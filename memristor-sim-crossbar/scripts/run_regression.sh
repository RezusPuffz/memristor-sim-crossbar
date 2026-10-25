#!/bin/bash
# Run every test pattern through Spectre and check it against the golden model.
# Runs on the post-layout (Quantus-extracted) colout3.
# Needs: spectre on PATH and the gpdk045 models (path in gen_array.py).
# Usage: scripts/run_regression.sh   (from the repo root)
set -e
cd "$(dirname "$0")/.."
mkdir -p build

WEIGHTS="2,-2;-1,3"           # the tb_array2x2_v4 array
PATTERNS=("0,0.1" "0.1,0.1" "0.2,0.1")

fail=0
for vin in "${PATTERNS[@]}"; do
    tag=${vin//[,.]/_}
    python3 scripts/gen_array.py --weights "$WEIGHTS" --vin "$vin" \
        --colout3 "$PWD/netlists/colout3_extracted.scs" \
        --vteam "$PWD/veriloga/vteam.va" > "build/tb_$tag.scs"
    spectre -format psfascii -raw "build/raw_$tag" "build/tb_$tag.scs" > "build/log_$tag.txt"
    python3 scripts/golden_model.py --weights "$WEIGHTS" --vin "$vin" \
        --check "build/raw_$tag/dcop.dc" || fail=1
done

[ $fail -eq 0 ] && echo "REGRESSION PASS" || { echo "REGRESSION FAIL"; exit 1; }
