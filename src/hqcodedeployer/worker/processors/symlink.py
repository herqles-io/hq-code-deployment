from hqworker.processor import ActionProcessor


class Symlink(ActionProcessor):

    def __init__(self, worker):
        super(Symlink, self).__init__(worker, "symlink", ['source', 'target'])

    def work(self):
        if self.args['source'] is None:
            return -1, "Source not provided"

        if self.args['target'] is None:
            return -1, "Target not provided"

        exitCode, error = self.run_command(['/bin/ln', '-sfn', self.args['source'], self.args['target']])

        return exitCode, error

