from hqworker.processor import ActionProcessor


class ChownWorker(ActionProcessor):

    def __init__(self, worker):
        super(ChownWorker, self).__init__(worker, "chown", ["options", "owner", "group", "file"])

    def work(self):
        group = self.args["group"]
        owner = self.args["owner"]

        if group is not None:
            group = ":{0}".format(group)
        else:
            group = ""

        if owner is None:
            owner = ""

        ownership = "{0}{1}".format(owner, group)

        if self.args["options"] is not None:
            cmd_list = ['chown', self.args["options"], ownership, self.args["file"]]
        else:
            cmd_list = ['chown', ownership, self.args["file"]]

        return self.run_command(cmd_list)
