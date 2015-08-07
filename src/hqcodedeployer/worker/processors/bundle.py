from hqworker.processor import ActionProcessor


class Install(ActionProcessor):

    def __init__(self, worker):
        super(Install, self).__init__(worker, "bundle:install", ['cwd'])

    def work(self):

        return self.run_command(["bundle", "install", "--deployment", "--without", "development", "test"],
                                cwd=self.args['cwd'], env=self.read_env_file(self.args['cwd']+"/.HQ_ENV"))
