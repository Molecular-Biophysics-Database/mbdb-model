#!/bin/bash

set -e

cd $(dirname $0)

black . --target-version py310
autoflake --in-place --remove-all-unused-imports --recursive .
isort .  --profile black
