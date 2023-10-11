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
        ../models/oarepo/general_parameters.yaml

python yamale2oarepo.py ../models/main/BLI.yaml ../models/oarepo/BLI.yaml \
        --include ../models/main/general_parameters.yaml

python yamale2oarepo.py ../models/main/MST.yaml ../models/oarepo/MST.yaml \
        --include ../models/main/general_parameters.yaml

python yamale2oarepo.py ../models/main/SPR.yaml ../models/oarepo/SPR.yaml \
        --include ../models/main/general_parameters.yaml
