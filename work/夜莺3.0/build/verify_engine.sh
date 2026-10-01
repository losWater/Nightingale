#!/bin/zsh
# 用法：build/verify_engine.sh <旧引擎> <新引擎> <运行目录>...   比较同一最终布局下 YOZAKURA 分项与总分
OLD=$1; NEW=$2; shift 2
for D in "$@"; do
  O=$(find $D -maxdepth 1 -name 'output-*' | sort | head -1)
  T=$(mktemp -d)
  cp $D/{elements.yaml,yozakura.json,targets.json,matrix.json,distribution.txt,equivalence.txt} $T/
  sed -i '' "s#\"matrix\": \"[^\"]*\"#\"matrix\": \"$T/matrix.json\"#" $T/yozakura.json
  ~/Yozakura/.venv/bin/python -c "import yaml,json;c=yaml.safe_load(open('$O/config.yaml'));c['generated_mapping_space']=json.load(open('$D/run.json'))['generated_mapping_space'];json.dump(c,open('$T/run.json','w'),ensure_ascii=False)"
  for B in $OLD $NEW; do
    (cd $T && NIGHTINGALE_YOZAKURA=$T/yozakura.json NIGHTINGALE_TARGET_DIR=$T NIGHTINGALE_TARGET_WEIGHT=200 NIGHTINGALE_TRIAL_SEED=1 \
      $B encode run.json -e elements.yaml -k distribution.txt -p equivalence.txt 2>&1 >/dev/null | grep YOZAKURA | tail -1)
    S=$(find $T -maxdepth 1 -name 'output-*' | sort | tail -1); python3 -c "import json;print('  score',json.load(open('$S/metric.json'))['score'])"; rm -rf $S
  done
  rm -rf $T
done
