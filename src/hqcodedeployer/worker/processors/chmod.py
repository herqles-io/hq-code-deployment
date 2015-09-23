from hqworker.processor import ActionProcessor


class ChmodWorker(ActionProcessor):

    def __init__(self, worker):
        super(ChmodWorker, self).__init__(worker, "chmod", ["options", "mode", "file"])

    def work(self):
        return self.run_command(['chmod', self.args["options"], self.args["mode"], self.args["file"]])
