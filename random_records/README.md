# Model conversion

## Main utility

`random_generator.py` is the main utility script that generates (valid) random records based on a given model

```
Usage: random_generator.py [OPTIONS] INPUT_FILE

  Generate N_DOCS random records based on INPUT_FILE (defaults to MST model)
  which must be a values_only model.

Options:
  --n_docs INTEGER       [default: 25]
  --output_folder PATH   [default: /home/emil/bin/mbdb-orga/mbdb-
                         model/random_records/random_generated_data]
  --output_file PATH     [default: random_docs]
  --include_schema PATH  [default: /home/emil/bin/mbdb-orga/mbdb-
                         model/models/values-only/general_parameters.yaml]
  --help                 Show this message and exit.
```
