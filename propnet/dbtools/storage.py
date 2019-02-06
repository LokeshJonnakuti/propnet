from monty.json import MSONable
from monty.serialization import MontyDecoder
from propnet.core.quantity import BaseQuantity, QuantityFactory
from propnet.core.provenance import ProvenanceElement
from propnet import ureg
from propnet.symbols import DEFAULT_SYMBOLS
import copy
import logging

logger = logging.getLogger(__name__)


class StorageQuantity(MSONable):
    """
    A class to hold quantity data intended for database storage.

    This class does not inherit from BaseQuantity in effort to remain autonomous as a storage
    container, and not implementing much of the functionality required by the BaseQuantity class.

    This class is the top-level object for storage. StorageQuantity objects contain a ProvenanceStore
    object for provenance which therein contains ProvenanceStoreQuantity objects as its inputs.

    Hierarchy for non-storage objects:
        BaseQuantity has a ProvenanceElement (self.provenance)
        ProvenanceElement has a list of BaseQuantity objects (self.provenance.inputs)
        Each input BaseQuantity object has a ProvenanceElement with BaseQuantity inputs, etc.

    Hierarchy for non-storage objects:
        StorageQuantity has a ProvenanceStore (self.provenance)
        ProvenanceStore has a list of ProvenanceStoreQuantity objects (self.provenance.inputs)
        Each input ProvenanceStoreQuantity object has a ProvenanceStore
            with ProvenanceStoreQuantity inputs, etc.

    The main purpose of these three classes is to prevent storing many copies of
    provenance quantity data (i.e. the values) in the database to save on document size.
    """

    def __init__(self, quantity_to_store=None):
        """
        Constructor for StorageQuantity objects. Converts a BaseQuantity-derived object
        into storage-ready object. See _initialize() for more information.

        Args:
            quantity_to_store: (BaseQuantity) BaseQuantity-derived object for storage

        """
        self._internal_id = None
        self._data_type = None
        self._symbol_type = None
        self._tags = None
        self._units = None
        self._value = None
        self._uncertainty = None
        self._provenance = None

        if isinstance(quantity_to_store, BaseQuantity):
            self._initialize(
                data_type=quantity_to_store.__class__.__name__,
                symbol_type=quantity_to_store.symbol,
                value=quantity_to_store.magnitude,
                units=quantity_to_store.units.format_babel() if quantity_to_store.units else None,
                internal_id=quantity_to_store._internal_id,
                tags=quantity_to_store.tags,
                provenance=ProvenanceStore.from_provenance_element(quantity_to_store.provenance),
                uncertainty=quantity_to_store.uncertainty.magnitude if quantity_to_store.uncertainty else None)
        elif quantity_to_store is not None:
            raise TypeError("Initialization requires a BaseQuantity-derived object for storage. "
                            "Instead received: {}".format(type(quantity_to_store)))

    def _initialize(self, data_type=None, symbol_type=None, value=None, units=None,
                    internal_id=None, tags=None, provenance=None, uncertainty=None):
        """
        Workhorse function for StorageQuantity constructor. This is a private method because this
        class is intended to be constructed by passing in a BaseQuantity-derived object to
        __init__() or from_quantity(). It is required to provide easy from_dict() functionality.

        Args:
            data_type: (str) indicates what type of BaseQuantity object it was created from.
                Must be "NumQuantity" or "ObjQuantity".
            symbol_type: (Symbol) symbol representing the type of data contained in the object
            value: (id) the data stored in the object
            units: (str) units of the value or None for non-numerical values
            internal_id: (str) unique identifier. (Note: this is used for lookup when the
                object is deserialized)
            tags: (list<str>) tags associated with the quantity, typically
                related to its origin, e. g. "DFT" or "ML" or "experiment"
            provenance: (ProvenanceStore) provenance associated with the object as storage object.
            uncertainty: (int, float, complex) uncertainty associated with the
                value stored in the same units
        """

        self._internal_id = internal_id
        self._data_type = data_type
        self._symbol_type = symbol_type
        self._tags = tags
        self._units = units
        self._value = value
        self._uncertainty = uncertainty
        self._provenance = provenance

    @property
    def uncertainty(self):
        """
        Returns uncertainty as pint Quantity

        Returns: (pint.Quantity) uncertainty as pint object or None if does not exist
        """

        return ureg.Quantity(self._uncertainty, self._units) if self._uncertainty else None

    @property
    def provenance(self):
        """
        Returns a copy of this object's provenance object

        Returns: (ProvenanceElement) provenance information

        """
        return copy.deepcopy(self._provenance)

    @property
    def symbol(self):
        """
        Returns a copy of the object's symbol representing the property stored

        Returns: (Symbol) Symbol property object of this object
        """
        return copy.deepcopy(self._symbol_type)

    @property
    def tags(self):
        """
        Returns a copy of the object's list of tags.

        Returns: (list<str>) tags for the object

        """
        return copy.deepcopy(self._tags)

    @property
    def value(self):
        """
        Returns a copy of the object's value.

        Returns: (id) object's value

        """
        # Return copy so class member remains immutable
        return copy.deepcopy(self._value)

    @property
    def magnitude(self):
        """
        Returns a copy of the object's value (same as self.value)

        Note: For numerical quantities, self.value already contains the unitless magnitude

        Returns: (id) object's value

        """
        return self.value

    @property
    def units(self):
        """
        Returns the units of the object as a pint.Unit.

        Returns: (pint.Unit) units, None if no units

        """
        return ureg.Unit(self._units) if self._units else None

    @classmethod
    def from_quantity(cls, quantity_in):
        """
        Creates a StorageQuantity object from a BaseQuantity-derived object
        or returns a deep copy of a StorageQuantity object.

        Args:
            quantity_in: (BaseQuantity, StorageQuantity) quantity to convert

        Returns: (StorageQuantity) converted or copied object

        """
        if isinstance(quantity_in, StorageQuantity):
            return copy.deepcopy(quantity_in)

        return cls(quantity_in)

    def to_quantity(self, lookup=None):
        """
        Converts the current StorageQuantity to the appropriate BaseQuantity-derived
        object.

        Verifies that the object's provenance has complete values, which would be
        missing if read in from a JSON-serialized dictionary. If values are found
        to be missing, a lookup function/dictionary is required to reconstitute the data.

        Lookup dictionaries should be keyed by internal ID, and have values which are
        dictionaries with the fields shown below. Lookup functions should take one argument,
        internal ID, and return a dictionary with the fields below.

        Lookup return value construction:
            value: (id) value of the quantity
            units: (str) units of quantity, None if no units
            uncertainty: (int, float, complex) uncertainty value, None if no uncertainty

        Args:
            lookup: (dict or function) lookup container for missing values. Not required
                if self.needs_lookup() is False

        Returns: (BaseQuantity) converted BaseQuantity-derived object

        """
        if self.needs_lookup() and not lookup:
            raise ValueError("StorageQuantity cannot be converted to BaseQuantity-derived"
                             " object because it is missing values in provenance inputs. "
                             "Please provide a lookup dictionary or function with the "
                             "following keys: {}".format(self.get_missing_keys()))

        if self.provenance is not None:
            provenance_in = self._provenance.to_provenance_element(lookup=lookup)
        else:
            provenance_in = None

        out = QuantityFactory.create_quantity(symbol_type=self._symbol_type,
                                              value=self._value,
                                              units=self._units,
                                              tags=self._tags,
                                              provenance=provenance_in,
                                              uncertainty=self._uncertainty)

        out._internal_id = self._internal_id
        return out

    def needs_lookup(self):
        """
        Checks to see if this object requires a value lookup dictionary to be converted
        to a BaseQuantity-derived object. Inputs in the provenance tree
        may be missing if the object was created from a JSON-serialized dictionary.

        Returns: True if there are inputs missing values in the provenance tree.
            False if all values are present or there is no provenance tree.
        """
        return not self.get_missing_keys()

    def get_missing_keys(self):
        """
        Finds the inputs in the provenance tree that are missing values and reports
        their internal IDs.

        Returns: (set) set of internal IDs whose values are missing. Empty set if
            all values are present or no provenance tree exists.
        """
        def rec_get_missing_keys(provenance, keys):
            if provenance.inputs:
                for item in provenance.inputs:
                    if not item.is_value_retrieved():
                        keys.add(item._internal_id)
                    rec_get_missing_keys(item.provenance, keys)

        missing_keys = set()
        if self._provenance:
            rec_get_missing_keys(self._provenance, missing_keys)
        return missing_keys

    def __hash__(self):
        return hash(self._internal_id)

    def __str__(self):
        return "<{}, {} {}, {}>".format(self.symbol.name, self.value, self.units, self.tags)

    def __repr__(self):
        return self.__str__()

    def __bool__(self):
        return bool(self.value)

    def as_dict(self):
        """
        Returns object instance as a dictionary. Object can be reconstituted from this
        dictionary using from_dict().

        Returns: (dict) dictionary representation of the object

        """
        symbol = self._symbol_type
        if symbol.name in DEFAULT_SYMBOLS.keys() and symbol == DEFAULT_SYMBOLS[symbol.name]:
            symbol = self._symbol_type.name

        return {"@module": self.__class__.__module__,
                "@class": self.__class__.__name__,
                "internal_id": self._internal_id,
                "data_type": self._data_type,
                "symbol_type": symbol,
                "value": self._value,
                "units": self._units,
                "provenance": self._provenance,
                "tags": self._tags,
                "uncertainty": self._uncertainty}

    @classmethod
    def from_dict(cls, d):
        """
        Creates a StorageQuantity object from a dictionary of instance variable values.

        Args:
            d: (dict) dictionary of object instance variable values

        Returns: (StorageQuantity) StorageQuantity represented by the dictionary values

        """
        d_in = {k: MontyDecoder().process_decoded(v) for k, v in d.items()
                if not k.startswith("@")}
        if isinstance(d_in['symbol_type'], str):
            d_in['symbol_type'] = DEFAULT_SYMBOLS[d_in['symbol_type']]

        out = cls()
        out._initialize(**d_in)
        return out

    @staticmethod
    def reconstruct_quantity(d, lookup):
        """
        Recreates BaseQuantity-derived object from JSON-serialized dictionary
        representation of the equivalent StorageQuantity.

        Args:
            d: (dict) dictionary representation of StorageQuantity object
            lookup: (dict or function) lookup container for missing values,
                if they exist (see to_quantity() for more information)

        Returns: (BaseQuantity) BaseQuantity-derived object representation
            of the dictionary values

        """
        return StorageQuantity.from_dict(d).to_quantity(lookup)

    def __eq__(self, other):
        """
        Determines equality between this object and a BaseQuantity-derived object,
        StorageQuantity object, or ProvenanceStoreQuantity object.

        Equality is defined as having the same internal ID and the same provenance.

        Args:
            other: (BaseQuantity, StorageQuantity, ProvenanceStoreQuantity)
                quantity with which to determine equality

        Returns: (bool) True if the objects represent the same information. False otherwise.

        """
        if isinstance(other, (StorageQuantity, BaseQuantity)):
            return self._internal_id == other._internal_id and \
                   self.provenance == other.provenance
        else:
            return NotImplemented


class ProvenanceStore(MSONable):
    """
    A class to hold provenance data for storage. It is held within a StorageQuantity
    or ProvenanceStoreQuantity object. The class provides methods to coerce ProvenanceElement
    objects for storage.

    This class does not inherit from ProvenanceElement in effort to remain autonomous as a storage
    container, and to strip any unwanted functionality from the ProvenanceElement class.

    The main purpose of these three classes is to prevent storing many copies of
    provenance quantity data (i.e. the values) in the database to save on document size.
    """
    def __init__(self, provenance_in=None):
        # super(ProvenanceStore, self).__init__()
        self._model = None
        self._source = None
        self._inputs = None

        if isinstance(provenance_in, ProvenanceElement):
            self._initialize(model=provenance_in.model,
                             source=provenance_in.source,
                             inputs=[ProvenanceStoreQuantity.from_quantity(v)
                                     for v in provenance_in.inputs]
                             if provenance_in.inputs else None)
        elif provenance_in is not None:
            raise TypeError("Initialization requires a ProvenanceElement object for storage. "
                            "Instead received: {}".format(type(provenance_in)))

    def _initialize(self, model=None, inputs=None, source=None):
        self._model = model
        self._source = source
        self._inputs = inputs

    @property
    def inputs(self):
        return copy.deepcopy(self._inputs)

    @property
    def model(self):
        return self._model

    @property
    def source(self):
        return copy.deepcopy(self._source)

    @classmethod
    def from_provenance_element(cls, provenance_in):
        if isinstance(provenance_in, ProvenanceStore):
            return copy.deepcopy(provenance_in)

        return cls(provenance_in)

    def to_provenance_element(self, lookup=None):
        if self.inputs:
            inputs = [v.to_quantity(lookup=lookup) for v in self.inputs]
        else:
            inputs = None
        return ProvenanceElement(model=self.model,
                                 inputs=inputs,
                                 source=self.source)

    def as_dict(self):
        return {'@module': self.__class__.__module__,
                '@class': self.__class__.__name__,
                'model': self._model,
                'source': self._source,
                'inputs': self._inputs}

    @classmethod
    def from_dict(cls, d):
        d_in = {k: MontyDecoder().process_decoded(v) for k, v in d.items()
                if not k.startswith('@')}
        out = cls()
        out._initialize(**d_in)
        return out

    def __eq__(self, other):
        if type(other) is type(self):
            return self.model == other.model and \
                   set(self.inputs or []) == set(other.inputs or [])
        elif isinstance(other, ProvenanceElement):
            return self.model == other.model and \
                   set(self.inputs or []) == set(self.from_provenance_element(other).inputs or [])
        else:
            return NotImplemented


class ProvenanceStoreQuantity(StorageQuantity):
    def __init__(self, quantity_to_store=None, from_dict=False):
        super(ProvenanceStoreQuantity, self).__init__(quantity_to_store)

        self._from_dict = from_dict
        self._value_retrieved = self.value is not None

    def as_dict(self):
        symbol = self._symbol_type
        if symbol.name in DEFAULT_SYMBOLS.keys() and symbol == DEFAULT_SYMBOLS[symbol.name]:
            symbol = self._symbol_type.name

        return {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "data_type": self._data_type,
            "symbol_type": symbol,
            "internal_id": self._internal_id,
            "tags": self._tags,
            "provenance": self._provenance
        }

    @classmethod
    def from_dict(cls, d):
        d_in = {k: MontyDecoder().process_decoded(v) for k, v in d.items()
                if not k.startswith('@')}
        out = cls(from_dict=True)
        out._initialize(**d_in)
        return out

    def is_from_dict(self):
        return self._from_dict

    def is_value_retrieved(self):
        return self._value_retrieved

    def lookup_value(self, lookup):
        lookup_fun = None
        if isinstance(lookup, dict):
            lookup_fun = lookup.get
        elif not callable(lookup) and lookup_fun is None:
            raise TypeError("Specified lookup is not callable or a dict.")
        else:
            lookup_fun = lookup

        d = lookup_fun(self._internal_id)

        if not d:
            logger.warning("Value not found for internal ID: {}".format(self._internal_id))
            return False

        if not isinstance(d, dict):
            raise TypeError("Expected dict, instead received: {}".format(type(d)))

        if not all(k in d.keys() for k in ('value', 'units', 'uncertainty')):
            raise ValueError("Callable does not return dict containing 'value', "
                             "'units', and 'uncertainty' keys")

        self._value = d['value']
        self._units = d['units']
        self._uncertainty = d['uncertainty']
        self._value_retrieved = True
        return True

    def to_quantity(self, lookup=None):
        copy_of_self = copy.deepcopy(self)
        if lookup:
            copy_of_self.lookup_value(lookup)

        if not copy_of_self.is_value_retrieved():
            if copy_of_self.is_from_dict():
                raise ValueError("No value has been looked up successfully for this quantity. "
                                 "Run lookup_value() first or make sure the specified lookup "
                                 "function or dict contains the internal ID of this quantity: {}"
                                 "".format(copy_of_self._internal_id))
            else:
                raise ValueError("Cannot create new BaseQuantity with no value. Property 'value' has no value, "
                                 "possibly because it was never looked up. Use lookup_value() or initialize an "
                                 "object with a value.")

        return super(ProvenanceStoreQuantity, copy_of_self).to_quantity(lookup=lookup)

    def __hash__(self):
        return super().__hash__()
