# Model conversion

**WARNING**
The tools are in an early state of development, so please be careful when using
them as they will overwrite changes you have made downstream of the main models
without asking you.

## Main utility

`convert_and_validate.sh` is the main utility script that converts all the main models and validates the metadata examples.

Usage:

```bash
./convert_and_validate.sh
```

It simply calls all the specialised scripts in this folder that generates models or validates the example in the following order:

 1. Convert all main models to value-only models
 2. Converts the value-only models to unrolled models
 3. Validates the YAML metadata examples and converts them to JSON
 4. Generates oarepo (Invenio) models

## Convert to values only model

The `values_only.py` script strips away the descriptions to give rise to a model that can be used for validation of metadata records.

THis is done by recursively finding description:value pairs that are present within the
same scope of Yamale schmeas and replaces them with the value of the value

## values_only.py

This tool recursively finds description:value pairs that are present within the
same scope of Yamale schmeas and replaces them with the value of the value.

## Unroll the models

the `unroll.py` script recursively replace a reference to an include with the include itself
as wells as extracting and adding information about each item. Includes from
multiple files be used.

The script is useful for accessing the total number of fields.


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



## Convert to Invenio/Oarepo model compatible model

The `yamale2oarepo.py` scripts converts the main model into the models files that can used to add and compile
models to the the repo.

`yamale2oarepo_config.py` is merely a configuration file for yamale2oarepo.py that encodes various constants.

## Validate example record against the models

`validate_examples.py` uses the value_only models to validate the YAML form of the records and converts them
into JSON that can be used as fixtures in the Invenio/Oarepo app.
