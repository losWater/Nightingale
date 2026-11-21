#!/bin/sh
# 调根台：重新生成数据并拼出单页
# - index.html：网页版（发布到 claude.ai Artifact 时连同 data.json 一起发布）
# - 夜莺调根台.html：本地版（数据和 seed.json 里的布局都嵌在页面里，双击即可离线使用）
# sh build.sh yozakura：夜桜版（自然码输入 zr31，换键对 NB46 计），输出到 yozakura/（index.html + data.json、夜桜调根台.html）
#   先跑一次 NB_INP=zr31 NB_BASE=release/NB46_form.json python construct/prefs.py 出算法喜好（construct/prefs_syllable_zr31.json）
cd "$(dirname "$0")"
PY=python3; [ -x ../../.venv/bin/python ] && PY=../../.venv/bin/python
if [ "$1" = yozakura ]; then
  mkdir -p yozakura
  NB_INP=zr31 NB_BASE=release/NB46_form.json $PY ../../construct/export_viz.py yozakura/data.json
  OUT=yozakura NAME=夜桜 $PY - <<'PY'
import json, os
out, name = os.environ['OUT'], os.environ['NAME']
d = json.load(open(f'{out}/data.json', encoding='utf-8'))
brand = {'名称': name, '基准': 'NB46', '起点': 'ZR27', '对照': 'NB46', '存储': 'tiaogen_yozakura'}
sub = lambda s: (s.replace('夜莺调根台', f'{name}调根台').replace('8455 个读音', f"{len(d['readings'])} 个读音")
                  .replace('相对 2.5 换了键', '相对 NB46（夜莺 3.1）换了键'))
head, body = sub(open('head.html').read()), sub(open('body.html').read())
t = open('table.js').read().replace("if (typeof module !== 'undefined') module.exports = { buildTable };", "")
br = '<script>window.TIAOGEN_BRAND=' + json.dumps(brand, ensure_ascii=False) + ';</script>\n'
code = br + '<script>\n' + open('model.js').read() + '\n' + t + '\n' + open('app.js').read() + '\n</script>\n'
open(f'{out}/index.html', 'w').write(head + body + code)
emb = lambda nm, s: f'<script>window.{nm}=' + s.strip().replace('</', '<\\/') + ';</script>\n'
doc = '<!doctype html>\n<html lang="zh-CN">\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
open(f'{out}/{name}调根台.html', 'w').write(doc + head + body + emb('TIAOGEN_DATA', open(f'{out}/data.json', encoding='utf-8').read()) + code)
PY
  echo 已生成 yozakura/index.html、yozakura/夜桜调根台.html
  exit 0
fi
$PY ../../construct/export_viz.py data.json
$PY - <<'PY'
t=open('table.js').read().replace("if (typeof module !== 'undefined') module.exports = { buildTable };","")
code='<script>\n'+open('model.js').read()+'\n'+t+'\n'+open('app.js').read()+'\n</script>\n'
open('index.html','w').write(open('head.html').read()+open('body.html').read()+code)
emb=lambda name, f: f'<script>window.{name}=' + open(f, encoding='utf-8').read().strip().replace('</', '<\\/') + ';</script>\n'
doc='<!doctype html>\n<html lang="zh-CN">\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
open('夜莺调根台.html','w').write(doc+open('head.html').read()+open('body.html').read()
    + emb('TIAOGEN_DATA', 'data.json') + emb('TIAOGEN_SEED', 'seed.json') + code)
PY
echo 已生成 index.html、夜莺调根台.html
