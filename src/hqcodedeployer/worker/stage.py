from schematics.types import StringType
from schematics.types.compound import DictType
from hqcodedeployer.worker import CDWorker

class Worker(CDWorker):

    def __init__(self):
        super(Worker, self).__init__("codedeployer-stage")

    def config_class(self):
        class ConfigValidator(super(Worker, self).config_class()):

            tags = DictType(StringType)

        return ConfigValidator

    def get_tags(self):

        data = {}

        if self.config.tags is not None:
            data = data.copy()
            data.update(self.config.tags)

        return data

    def on_register(self):
        self.logger.info("Registered Code Deployer Stage Worker")
