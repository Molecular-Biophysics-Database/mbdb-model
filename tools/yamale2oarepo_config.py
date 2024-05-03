# objects that are only used elsewhere and therefore should be ignored during validation

# Mapping related constants
QUERY_STRING_FIELD = "collected_default_search_fields"
PRIMITIVES_MAPPING = {"copy_to": QUERY_STRING_FIELD}

# note that only vocabularies titles and id are made searchable
# TODO: allow placement of custom fields to be searchable
VOCABULARY_MAPPING = {
    "title": {"mapping": {"properties": {"en": PRIMITIVES_MAPPING}}},
    "id": {"mapping": PRIMITIVES_MAPPING},
}

CHEMICAL_VOCABULARY_KEYS = [
    "id",
    "title",
    {"key": "chemical_formula", "model": {"type": "keyword"}},
    {
        "key": "additional_identifiers",
        "model": {"type": "array", "items": {"type": "keyword"}},
    },
    {
        "key": "molecular_weight",
        "model": {
            "type": "object",
            "properties": {
                "value": {"type": "float"},
                "unit": {"type": "keyword"},
            },
        },
    },
]

VOCABULARY_CUSTOM_FIELD_KEYS = {
    "affiliations": None,
    "organisms": None,
    "grants": None,
    "instruments": None,
    "chemicals": CHEMICAL_VOCABULARY_KEYS,
}
