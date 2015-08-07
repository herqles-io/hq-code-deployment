from hqworker.processor import ActionProcessor


class CopyWorker(ActionProcessor):

    def __init__(self, worker):
        super(CopyWorker, self).__init__(worker, "copy", ["from", "to"])

    def work(self):
        return 0, ""

