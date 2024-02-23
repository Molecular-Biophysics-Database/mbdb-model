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
