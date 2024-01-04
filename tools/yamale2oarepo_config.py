# objects that are only used elsewhere and therefore should be ignored by validation

EXTENSION_ELEMENTS = [
    "ui_file_context",
]

MODEL_SETTINGS = {"i18n-languages": ["en"], "extension-elements": EXTENSION_ELEMENTS}

PROFILES = [
    "record",
    "draft",
    "files",
    "draft_files",
]

PLUGINS = {
    "builder": {"disable": ["script_sample_data"]},
    "packages": [
        "oarepo-model-builder-files==4.*",
        "oarepo-model-builder-cf==4.*",
        "oarepo-model-builder-vocabularies==4.*",
        "oarepo-model-builder-relations==4.*",
        "oarepo-model-builder-polymorphic==1.*",
        "oarepo-model-builder-drafts",
        "oarepo-model-builder-drafts-files",
    ],
}

FILE_RESOURCE = {
    "base-classes": [
        "oarepo_ui.resources.file_resource.S3RedirectFileResource"
    ]
}

# Mapping related constants
QUERY_STRING_FIELD = "collected_default_search_fields"
QUERY_STRING_FIELD_SETTINGS = {
    "type": "fulltext",
    "marshmallow": {"read": False, "write": False},
}

RECORD_MAPPING = {
    "template": {
        "settings": {
            "index.mapping.total_fields.limit": 3000,
            "index.mapping.nested_fields.limit": 200,
            "index.query.default_field": QUERY_STRING_FIELD,
        }
    }
}

PRIMITIVES_MAPPING = {"copy_to": QUERY_STRING_FIELD}

# note that only vocabularies titles and id are made searchable
# TODO: allow placement of custom fields to be searchable
VOCABULARY_MAPPING = {
    "title": {"mapping": {"properties": {"en": PRIMITIVES_MAPPING}}},
    "id": {"mapping": PRIMITIVES_MAPPING},
}
