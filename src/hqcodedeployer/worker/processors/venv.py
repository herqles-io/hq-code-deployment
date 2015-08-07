from hqworker.processor import ActionProcessor
from virtualenvapi.manage import VirtualEnvironment, PackageInstallationException


class Venv(ActionProcessor):

    def __init__(self, worker):
        super(Venv, self).__init__(worker, "venv", ['dir'])

    def work(self):

        env = VirtualEnvironment(path=self.args['dir'], python="python2.7")

        env.open_or_create()

        return 0, ""
