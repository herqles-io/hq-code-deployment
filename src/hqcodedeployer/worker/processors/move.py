from hqworker.processor import ActionProcessor


class MoveWorker(ActionProcessor):

    def __init__(self, worker):
        super(MoveWorker, self).__init__(worker, "move", ["from", "to"])

    def work(self):
        return self.run_command(['mv', self.args["from"], self.args["to"]])


