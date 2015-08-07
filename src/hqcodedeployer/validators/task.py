from schematics.models import Model
from schematics.types import StringType, IntType
from schematics.types.compound import ListType, DictType, ModelType


class ActionValidator(Model):

    processor = StringType(required=True)
    arguments = DictType(StringType)


class TaskValidator(Model):

    name = StringType(required=True)
    priority = IntType(required=True)
    actions = ListType(ModelType(ActionValidator), min_size=1, required=True)

    def validate_actions(self, data, value):

        for action in value:
            action.validate()

        return value
