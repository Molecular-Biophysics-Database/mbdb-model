# Model conversion

## Main utility

`convert_and_validate.sh` is the main utility script that converts all the main models and validates the metadata examples.

Usage:

```bash
./convert_and_validate.sh
```

It simply calls all the specialised scripts in this folder that generates models or validates the example metadata.

## Convert to values only model

The `values_only.py` script strips away the descriptions to give rise to a model that can be used for validation of metadata records.

## Unroll the models

The `unroll.py` script creates the complete tree of the models with all fields included. This is useful
to access the total number of fields.

## Convert to Invenio/Oarepo model compatible model

The `yamale2oarepo.py` scripts converts the main model into the models files that can used to add and compile
models to the the repo.

`yamale2oarepo_config.py` is merely a configuration file for yamale2oarepo.py that encodes various constants.

## Validate example record against the models

`validate_examples.py` uses the value_only models to validate the YAML form of the records and converts them
into JSON that can be used as fixtures in the Invenio/Oarepo app.
