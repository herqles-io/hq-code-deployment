from hqworker.processor import ActionProcessor


class RakeWorker(ActionProcessor):

    def __init__(self, worker):
        super(RakeWorker, self).__init__(worker, "rake", ["command", "cwd"])

    def work(self):

        env = self.read_env_file(self.args['cwd']+"/.HQ_ENV")
        env['RAILS_ENV'] = self.worker.get_tags()['environment']

        return self.run_command(['bundle', 'exec', 'rake', self.args["command"],
                                 "RAILS_ENV="+self.worker.get_tags()['environment']], cwd=self.args["cwd"], env=env)
