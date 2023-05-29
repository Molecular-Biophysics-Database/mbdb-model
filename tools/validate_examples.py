#!/usr/bin/env python3

import yamale
from yamale.readers import parse_yaml
from custom_validators import extend_validators, current_schema
from pathlib import Path
import json

PATH_TO_SCHEMAS = Path('../models/values-only/')
PATH_TO_TEST_DATA = Path('../metadata-examples/')


def merged_schema(method_specific: Path, *additional_includes: Path, validators=extend_validators) -> yamale.schema.Schema:
    schema = yamale.make_schema(method_specific, validators=validators)
    for path in additional_includes:
        add_includes(path, schema)
    return schema


def add_includes(path: Path, schema: yamale.schema.Schema) -> None:
    list_of_docs = parse_yaml(path)
    for doc in list_of_docs:
        schema.add_include(doc)


def main():
    general_param_file_name = PATH_TO_SCHEMAS.joinpath('general_parameters.yaml')

    file_names = ('MST.yaml',
                  'BLI.yaml',
                  'SPR.yaml'
                    )

    for file_name in file_names:
        schema = merged_schema(PATH_TO_SCHEMAS.joinpath(file_name), general_param_file_name)
        current_schema.schema = schema
        full_test_path = PATH_TO_TEST_DATA.joinpath(file_name)
        test_data = yamale.make_data(full_test_path)
        yamale.validate(schema, test_data)
        metadata_with_header = {'metadata': test_data[0][0]}
        json_metadata = json.dumps(metadata_with_header, indent=2, ensure_ascii=False, default=str)
        json_metadata = json_metadata.replace("$ref", "id")
        with open(full_test_path.with_suffix('.json'), 'w') as json_out:
            json_out.write(json_metadata)


if __name__ == '__main__':
    main()
