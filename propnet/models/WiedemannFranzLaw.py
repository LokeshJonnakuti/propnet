from propnet.core.models import AbstractModel


class WiedemannFranzLaw(AbstractModel):

    @property
    def constraint_symbols(self):
        return ['is_metallic']

    def check_constraints(self, constraint_inputs):
        return constraint_inputs['is_metallic'] is True
