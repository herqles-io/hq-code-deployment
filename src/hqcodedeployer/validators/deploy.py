from schematics.models import Model
from schematics.types import StringType, IntType
from schematics.types.compound import ListType, DictType, ModelType
from hqcodedeployer.validators.task import TaskValidator
from schematics.exceptions import ValidationError


class DeployValidator(Model):

    datacenter = StringType()
    env = StringType(required=True)
    stage_id = IntType(min_value=1, required=True)
    min_nodes = IntType(min_value=1)
    targets = ListType(StringType(), min_size=1)
    tags = DictType(StringType())
    deploy_variables = DictType(StringType())
    deploy_tasks = ListType(ModelType(TaskValidator))

    def validate_targets(self, data, value):
        if data['min_nodes'] is None and value is None:
            raise ValidationError('min_nodes or targets must be given')

        return value
