from hqworker.processor import ActionProcessor


class MkDirWorker(ActionProcessor):

    def __init__(self, worker):
        super(MkDirWorker, self).__init__(worker, "mkdir", ["dir"])

    def work(self):
        return self.run_command(['mkdir', '-p', self.args["dir"]])
