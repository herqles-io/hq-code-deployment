from hqworker.processor import ActionProcessor


class UnTarWorker(ActionProcessor):

    def __init__(self, worker):
        super(UnTarWorker, self).__init__(worker, "untar", ["file", "dir"])

    def work(self):
        return self.run_command(['/bin/tar', '-xzvf', self.args["file"]], cwd=self.args["dir"])


class TarWorker(ActionProcessor):

    def __init__(self, worker):
        super(TarWorker, self).__init__(worker, "tar", ["file", "dir"])

    def work(self):
        return self.run_command(['/bin/tar', '-zcvf', self.args["file"], "."], cwd=self.args["dir"])

