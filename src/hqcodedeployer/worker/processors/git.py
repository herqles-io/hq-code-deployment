from hqworker.processor import ActionProcessor
import subprocess


class Clone(ActionProcessor):

    def __init__(self, worker):
        super(Clone, self).__init__(worker, "git:clone", ['repo', 'branch', 'cwd'])

    def work(self):

        exitCode, error = self.run_command(['/usr/bin/git', 'clone', self.args['repo'], self.args['cwd']])
        
        if exitCode == 0 and self.args['branch'] is not None:
            exitCode, error = self.run_command(['/usr/bin/git', 'checkout', self.args['branch']], cwd=self.args['cwd'])

        if exitCode == 0:
            try:
                with open(self.args['cwd']+"/BRANCH", "w") as f:
                    f.write(self.args['branch'])
            except EnvironmentError:
                exitCode = -1
                error = "Error creating branch file"

        if exitCode == 0:
            try:
                with open(self.args['cwd']+"/REVISION", "w") as f:
                    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=self.args['cwd'])
                    f.write(sha)
            except EnvironmentError:
                exitCode = -1
                error = "Error creating revision file"
        
        return exitCode, error