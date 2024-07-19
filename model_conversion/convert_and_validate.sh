#!/bin/bash

MODEL_DIR="../models"

# Remove descriptions
./values_only.py $MODEL_DIR/main/*.yaml \
--output-folder $MODEL_DIR/values-only/

# Unroll schemas
./unroll.py \
--schema-files $MODEL_DIR/values-only/*.yaml \
--output-folder $MODEL_DIR/unrolled/ \
--includes $MODEL_DIR/values-only/general_parameters.yaml

# Check that test data can still be validated
MODELS=(BLI MST ITC SPR)
./validate_examples.py ${MODELS[@]}

# run conversion to oarepo (Invenio) model
./yamale2oarepo.py $MODEL_DIR/main/general_parameters.yaml \
        --out_dir $MODEL_DIR/oarepo \
        --only_defs True

for model in ${MODELS[@]}
do
    ./yamale2oarepo.py $MODEL_DIR/main/$model.yaml \
        --out_dir $MODEL_DIR/oarepo \
        --include $MODEL_DIR/main/general_parameters.yaml
done
