#!/bin/bash

MODELS=(BLI MST ITC SPR)

# Remove descriptions
./values_only.py ../models/main/*.yaml \
--output-folder ../models/values-only/

# Unroll schemas
./unroll.py \
--schema-files ../models/values-only/*.yaml \
--output-folder ../models/unrolled/ \
--includes ../models/values-only/general_parameters.yaml

# Check that test data can still be validated
./validate_examples.py ${MODELS[@]}

# run conversion to oarepo (Invenio) model
cd $(dirname $0)

python yamale2oarepo.py ../models/main/general_parameters.yaml \
        --out_dir ../models/oarepo \
        --only_defs True

for model in ${MODELS[@]}
do
    python yamale2oarepo.py ../models/main/$model.yaml \
        --out_dir ../models/oarepo \
        --include ../models/main/general_parameters.yaml
done
