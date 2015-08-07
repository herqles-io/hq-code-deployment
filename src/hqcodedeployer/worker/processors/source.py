from hqworker.processor import ActionProcessor
import subprocess

class SourceWorker(ActionProcessor):

    def __init__(self, worker):
        super(SourceWorker, self).__init__(worker, "source", ["input_file", "cwd"])

    def work(self):

        env = self.read_env_file(self.args['cwd']+"/.HQ_ENV")

        proc = subprocess.Popen(["sh", "-c", "source "+self.args['input_file']+"; env"],
                                stdout=subprocess.PIPE, env=env, cwd=self.args['cwd'])

        with open(self.args['cwd']+"/.HQ_ENV", 'w') as f:
            f.write(proc.communicate()[0])

        return 0, ""

