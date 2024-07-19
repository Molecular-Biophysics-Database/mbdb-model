#!/usr/bin/env python3

import json
import sys
from pathlib import Path

import click
import yamale

current_dir = Path(__file__).parent.absolute()
root_dir = current_dir.parent.absolute()
sys.path.append(str(root_dir))

from tools.custom_validators import current_schema
from tools.schema_merge import merged_schema
from tools.paths import MODEL_DIR, EXAMPLES_DIR

PATH_TO_SCHEMAS = MODEL_DIR / "values-only"


@click.command()
@click.argument(
    "models",
    nargs=-1,
)
def main(models):
    general_param_file_name = PATH_TO_SCHEMAS.joinpath("general_parameters.yaml")
    for model in models:
        # Validate file
        file_name = f"{model}.yaml"
        schema = merged_schema(
            PATH_TO_SCHEMAS.joinpath(file_name), general_param_file_name
        )
        current_schema.schema = schema
        full_test_path = EXAMPLES_DIR.joinpath(file_name)
        test_data = yamale.make_data(full_test_path)
        yamale.validate(schema, test_data)

        # Convert to JSON record, note that an array is needed to load it as an Invenio fixture.
        metadata_with_header = [{"metadata": test_data[0][0]}]
        json_metadata = json.dumps(
            metadata_with_header, indent=2, ensure_ascii=False, default=str
        )
        json_metadata = json_metadata.replace("$ref", "id")
        with open(full_test_path.with_suffix(".json"), "w") as json_out:
            json_out.write(json_metadata)


if __name__ == "__main__":
    main()
