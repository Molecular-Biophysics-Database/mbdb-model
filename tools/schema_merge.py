from pathlib import Path

import yamale
from yamale.readers import parse_yaml

from .custom_validators import extend_validators


def merged_schema(
    method_specific: Path, *additional_includes: Path, validators=extend_validators
) -> yamale.schema.Schema:
    schema = yamale.make_schema(method_specific, validators=validators)
    for path in additional_includes:
        add_includes(path, schema)
    return schema


def add_includes(path: Path, schema: yamale.schema.Schema) -> None:
    list_of_docs = parse_yaml(path)
    for doc in list_of_docs:
        schema.add_include(doc)
