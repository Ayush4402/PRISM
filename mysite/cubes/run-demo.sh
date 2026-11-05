#!/usr/bin/env bash
set -eo pipefail

cd "$(dirname "$0")"
source "$PWD/.miniconda3/etc/profile.d/conda.sh"
conda activate cubes
exec python sequential.py tests-examples/demo/intro.yaml
