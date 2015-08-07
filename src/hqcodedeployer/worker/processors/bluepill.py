from hqworker.processor import ActionProcessor
import os


class Bluepill(ActionProcessor):

    def __init__(self, worker):
        super(Bluepill, self).__init__(worker, "bluepill", ["location", "name"])

    def work(self):
        env = os.environ.copy()
        if 'RAILS_ENV' not in env:
            env['RAILS_ENV'] = self.worker.get_tags()['environment']

        exitCode, error = self.run_command(['sudo', '/usr/local/bin/bootup_bluepill', 'load', self.args['location']], env=env)

        if exitCode == 0:
            exitCode, error = self.run_command(['sudo', '/usr/local/bin/bootup_bluepill', self.args['name'], 'restart'], env=env)

        return exitCode, error
