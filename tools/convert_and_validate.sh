#!/bin/bash

# Remove descriptions
./values_only.py ../models/main/*.yaml \
--output-folder ../models/values-only/

# Unroll schemas
./unroll.py \
--schema-files ../models/values-only/*.yaml \
--output-folder ../models/unrolled/ \
--includes ../models/values-only/general_parameters.yaml

# Check that test data can still be validated
./validate_examples.py

# run conversion to oarepo (Invenio) model
cd $(dirname $0)

python yamale2oarepo.py ../models/main/general_parameters.yaml \
        --out_dir ../models/oarepo \
        --only_defs True

python yamale2oarepo.py ../models/main/BLI.yaml \
        --out_dir ../models/oarepo \
        --include ../models/main/general_parameters.yaml

python yamale2oarepo.py ../models/main/MST.yaml \
        --out_dir ../models/oarepo \
        --include ../models/main/general_parameters.yaml

python yamale2oarepo.py ../models/main/SPR.yaml \
        --out_dir ../models/oarepo \
        --include ../models/main/general_parameters.yaml
