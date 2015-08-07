from hqworker.processor import ActionProcessor
import subprocess

class Copy(ActionProcessor):

    def __init__(self, worker):
        super(Copy, self).__init__(worker, "gem:copy", ["cwd", "gem", "from", "to"])

    def work(self):
        gem_path = subprocess.check_output(['bundle', 'show', self.args['gem']], cwd=self.args['cwd'])

        self.args['from'] = self.args['from'].replace('{gem_path}', gem_path)

        return self.run_command(['cp', '-r', self.args["from"], self.args["to"]])
