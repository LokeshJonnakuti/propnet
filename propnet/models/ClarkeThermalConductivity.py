from propnet.core.models import AbstractModel
from pymatgen.analysis.elasticity.elastic import ElasticTensor


class ClarkeThermalConductivity(AbstractModel):

   def plug_in(self, symbol_values):

       tensor = ElasticTensor.from_voigt(symbol_values["C_ij"])
       structure = symbol_values["_structure"]

       return {
           't': tensor.clarke_thermalcond(structure)
       }