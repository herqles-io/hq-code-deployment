from hqworker.processor import ActionProcessor
from virtualenvapi.manage import VirtualEnvironment, PackageInstallationException


class Install(ActionProcessor):

    def __init__(self, worker):
        super(Install, self).__init__(worker, "pip:install", ['venv', 'wheel-dir', 'requirements'])

    def work(self):

        env = VirtualEnvironment(path=self.args['venv'], python="python2.7")

        if self.args['wheel-dir'] is not None:
            exitCode, error = self.install_from_file(self.args['requirements'], env, wheel=self.args['wheel-dir'])
        else:
            exitCode, error = self.install_from_file(self.args['requirements'], env)

        return exitCode, error

    def install_from_file(self, requirements, env, wheel=None):
        with open(requirements) as f:

            options = []

            if wheel is not None:
                options.append('--no-index')
                options.append('--find-links='+wheel)
                options.append('--use-wheel')

            for line in f.readlines():
                line = line.replace("/n", "").replace("/t", "")
                line = line.strip().replace(" ", "")
                if line.startswith("#"):
                    continue
                if not line:
                    continue
                try:
                    self.logger.info("Installing python package "+line)
                    env.install(line, options=options)
                    self.logger.info("Installed python package "+line)
                except PackageInstallationException as e:
                    return -1, "Error installing package "+line+" Message: "+e.message[1]

        return 0, ""


class Wheel(ActionProcessor):

    def __init__(self, worker):
        super(Wheel, self).__init__(worker, "pip:wheel", ['venv', 'wheel-dir', 'requirements'])

    def work(self):
        env = VirtualEnvironment(path=self.args['venv'], python="python2.7")

        env.install('wheel')

        exit_code, error = self.wheel_from_file(self.args['requirements'], env, self.args['wheel-dir'])

        return exit_code, error

    def wheel_from_file(self, requirements, env, wheel):
        with open(requirements) as f:

            options = ['--wheel-dir='+wheel]

            for line in f.readlines():
                line = line.replace("/n", "").replace("/t", "")
                line = line.strip().replace(" ", "")
                if line.startswith("#"):
                    continue
                if not line:
                    continue
                try:
                    self.logger.info("Wheeling python package "+line)
                    env.wheel(line, options=options)
                    self.logger.info("Wheeled python package "+line)
                except PackageInstallationException as e:
                    return -1, "Error wheeling package "+line+" Message: "+e.message[1]

        return 0, ""
