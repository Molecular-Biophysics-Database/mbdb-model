# tools

**WARNING**
The tools are in an early state of development, so please be careful when using
them as they will overwrite changes you have made downstream of the main models
without asking you.


## convert_and_validates.sh

Convenience tool that uses most of the following tools to:
 1. Convert all main models to value-only models
 2. Converts the value-only models to unrolled models
 3. Validates the YAML metadata examples and converts them to JSON
 4. Generates oarepo (Invenio) models


## custom_validators.py

The standard validators of Yamale isn't enough for the task at hand and this is
where the custom Yamale validators are implemented.

## values_only.py

This tool recursively finds description:value pairs that are present within the
same scope of Yamale schmeas and replaces them with the value of the value.


```bash
usage: values_only.py [-h] [--output_folder OUTPUT_FOLDER]
                            schema_files [schema_files ...]

Removing the description elements in yamale schemas from mbdb

positional arguments:
  schema_files          Input Yamale schema files with descriptions

options:
  -h, --help            show this help message and exit
  --output_folder OUTPUT_FOLDER
                        Output folder where the schemas without structures
                        will be stored
```

## unroll.py

This tool recursively replace a reference to an include with the include itself
as wells as extracting and adding information about each item. Includes from
multiple files be used


```bash
usage: unroll.py [-h] [--output_folder OUTPUT_FOLDER]
                        [--includes INCLUDES [INCLUDES ...]]
                        schema_files [schema_files ...]

Unrolling the mbdb values-only yamale schemas

positional arguments:
  schema_files          Input Yamale schema files without descriptions

options:
  -h, --help            show this help message and exit
  --output_folder OUTPUT_FOLDER
                        Output folder where the unrolled structures will be stored
  --includes INCLUDES [INCLUDES ...]
                        Additional Yamale schema input files without descriptions to be used as
                        includes

```

## validate_examples.py

This is used to check that the example metadata be validate by the Yamale
schema. Note that the models used for validation is the values-only models.


## yamale2model.py

This is the tool that converts from the main (Yamale) models to oarepo models
that are compatible with being stored in Invenio.

## unit_conversion_table.md

Table of unit conversion that will be needed to make searching possible as well
as efficient.

## random_generator.py

Early attempt at creating random data based on the a Yamale schema
