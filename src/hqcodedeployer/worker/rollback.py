from hqcodedeployer.worker import CDWorker
from schematics.types import StringType
from schematics.types.compound import DictType, ListType


class Worker(CDWorker):

    def __init__(self):
        super(Worker, self).__init__("codedeployer-rollback")

    def config_class(self):
        class ConfigValidator(super(Worker, self).config_class()):

            apps = ListType(StringType, default=[])
            environment = StringType(required=True)
            tags = DictType(StringType)

        return ConfigValidator

    def get_tags(self):
        data = {'environment': self.config.environment, 'apps': self.config.apps}

        if self.config.tags is not None:
            data = data.copy()
            data.update(self.config.tags)

        return data

    def on_register(self):
        self.logger.info("Registered Code Deployer Rollback Worker")
