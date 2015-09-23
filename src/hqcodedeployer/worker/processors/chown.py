from hqworker.processor import ActionProcessor


class ChownWorker(ActionProcessor):

    def __init__(self, worker):
        super(ChmodWorker, self).__init__(worker, "chown", ["options", "owner", "group", "file"])
        group = self.args["group"]
        owner = self.args["owner"]

        if group not None:
            group = ":{0}".format(group)

        ownership = "{0}:{1}".format(owner, group)

    def work(self):
        return self.run_command(['chown', self.args["options"], self.ownership, self.args["file"]])
