from schematics.models import Model
from schematics.types import StringType
from schematics.types.compound import ListType, ModelType, DictType
from hqcodedeployer.validators.task import TaskValidator


class RollbackValidator(Model):

    env = StringType(required=True)
    datacenter = StringType()
    name = StringType(required=True)
    type = StringType(required=True)
    tags = DictType(StringType())
    rollback_variables = DictType(StringType())
    rollback_tasks = ListType(ModelType(TaskValidator))
