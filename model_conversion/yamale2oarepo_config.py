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
    {"id": {"type": "keyword"}},
    {"title": {"type": "i18ndict"}},
    {"chemical_formula": {"type": "keyword"}},
    {
        "additional_identifiers": {"type": "array", "items": {"type": "keyword"}},
    },
    {"molecular_weight": {
        "type": "object",
        "properties": {
            "value": {"type": "float"},
            "unit": {"type": "keyword"},
        }},
    },
]

VOCABULARY_CUSTOM_FIELD_KEYS = {
    "affiliations": [{'id': {'type': 'keyword'}}, {'title': {'type': 'i18ndict'}}, {'props.city': {'type': 'keyword'}}, {'props.state': {'type': 'keyword'}}, {'props.country': {'type': 'keyword'}}],
    "organisms": [{'id': {'type': 'keyword'}}, {'title': {'type': 'i18ndict'}}, {'props.rank': {'type': 'keyword'}}],
    "grants": [{"id": {"type": "keyword"}}, {"title": {"type": "i18ndict"}}, {"props.funder_name": {"type": "keyword"}}, {"props.grant_id": {"type": "keyword"}}],
    "instruments": [{'id': {'type': 'keyword'}}, {'title': {'type': 'i18ndict'}}, {'props.manufacturer': {'type': 'keyword'}}],
    "environment_types": [{'id': {"type": "keyword"}}, {'title': {"type": "i18ndict"}}],
    "body_fluids": [{'id': {"type": "keyword"}}, {'title': {"type": "i18ndict"}}],
    "products": [{'id': {"type": "keyword"}}, {'title': {"type": "i18ndict"}}],
    "cell_fractions": [{'id': {"type": "keyword"}}, {'title': {"type": "i18ndict"}}],
    "chemicals": CHEMICAL_VOCABULARY_KEYS,
}
