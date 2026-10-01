#!/bin/zsh
# 用法：build/run_batch.sh <批次名> <步数> <种子> '<权重JSON>' ...  （每组：名 种子 权重）
set -e
ROOT=~/Yozakura; BATCH=$1; STEPS=$2; shift 2
while (( $# >= 3 )); do
  NAME=$1; SEED=$2; W=$3; shift 3
  D=$ROOT/runs/$BATCH/$NAME; mkdir -p $D
  $ROOT/.venv/bin/python $ROOT/build/make_inputs.py "$BATCH-$NAME" "$W" > $D/build.log
  IN=$ROOT/build/out/$BATCH-$NAME
  cp $IN/{elements.yaml,yozakura.json,targets.json,matrix.json,distribution.txt,equivalence.txt,weights.json,meta.json} $D/
  python3 -c "import json,sys;c=json.load(open('$IN/run.json'));c['optimization']['metaheuristic']['parameters']['steps']=$STEPS;json.dump(c,open('$D/run.json','w'),ensure_ascii=False)"
  sed -i '' "s#$IN/matrix.json#$D/matrix.json#" $D/yozakura.json
  (cd $D && NIGHTINGALE_YOZAKURA=$D/yozakura.json NIGHTINGALE_TARGET_DIR=$D NIGHTINGALE_TARGET_WEIGHT=${T200:-200} NIGHTINGALE_TRIAL_SEED=$SEED \
     $ROOT/engine/target/release/chai optimize run.json -e elements.yaml -k distribution.txt -p equivalence.txt -t 1 > stdout.log 2> stderr.log; echo "rc=$?" > done.txt) &
done
wait
