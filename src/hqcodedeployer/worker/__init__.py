from hqworker.worker import AbstractWorker
from hqcodedeployer.worker.processors import processors
from abc import ABCMeta, abstractmethod


class CDWorker(AbstractWorker):

    __metaclass__ = ABCMeta

    @abstractmethod
    def get_tags(self):
        return {}

    def do_work(self, action):
        if action.processor in processors:
            exit_code, message = processors[action.processor](self).do_work(action.arguments)
            return exit_code, message
        else:
            return -1, "Unknown processor "+action.processor

    @abstractmethod
    def on_register(self):
        pass
