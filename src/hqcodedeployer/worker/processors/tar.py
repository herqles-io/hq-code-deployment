from hqworker.processor import ActionProcessor


class UnTarWorker(ActionProcessor):

    def __init__(self, worker):
        super(UnTarWorker, self).__init__(worker, "untar", ["file", "dir"])

    def work(self):
        return self.run_command(['/bin/tar', '-xzvf', self.args["file"]], cwd=self.args["dir"])


class TarWorker(ActionProcessor):

    def __init__(self, worker):
        super(TarWorker, self).__init__(worker, "tar", ["extra_args", "file", "dir"])

    def work(self):
        if 'extra_args' in self.args:
            extra_args = self.args['extra_args'].split()
            cmd_list = ['/bin/tar'] + extra_args + ['-zcf', self.args["file"], '.']
        else:
            cmd_ist = ['/bin/tar', '-zcf', self.args["file"], '.']

        return self.run_command(cmd_list, cwd=self.args["dir"])

