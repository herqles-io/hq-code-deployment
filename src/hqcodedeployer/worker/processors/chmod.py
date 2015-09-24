from hqworker.processor import ActionProcessor


class ChmodWorker(ActionProcessor):

    def __init__(self, worker):
        super(ChmodWorker, self).__init__(worker, "chmod", ["options", "mode", "file"])

    def work(self):
        if self.args["options"] is not None:
            cmd_list = ['chmod', self.args["options"], self.args["mode"], self.args["file"]]
        else:
            cmd_list = ['chmod', self.args["mode"], self.args["file"]]

        return self.run_command(cmd_list)
