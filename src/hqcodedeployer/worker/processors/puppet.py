from hqworker.processor import ActionProcessor


class PuppetWorker(ActionProcessor):

    def __init__(self, worker):
        super(PuppetWorker, self).__init__(worker, "puppet", ['binary_path'])

    def work(self):

        if self.args['binary_path'] is None:
            self.args['binary_path'] = 'puppet'

        self.run_command(['sudo', self.args['binary_path'], 'agent', '-t'])
        # if puppet throws errors treat is like the command was a success so the deployment doesn't fail
        return 0, ""
