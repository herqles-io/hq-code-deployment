from schematics.models import Model
from schematics.types import StringType
from schematics.types.compound import ListType, ModelType, DictType
from hqcodedeployer.validators.task import TaskValidator


class AppTypeValidator(Model):

    variables = DictType(StringType)
    tasks = ListType(ModelType(TaskValidator))

