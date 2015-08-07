from schematics.models import Model
from schematics.types import StringType
from schematics.types.compound import ListType, ModelType, DictType
from hqcodedeployer.validators.task import TaskValidator


class StageValidator(Model):

    name = StringType(required=True)
    type = StringType(required=True)
    repo = StringType(required=True)
    branch = StringType(default='master')
    tags = DictType(StringType())
    stage_variables = DictType(StringType())
    stage_tasks = ListType(ModelType(TaskValidator))
