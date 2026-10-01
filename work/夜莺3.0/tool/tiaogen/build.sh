#!/bin/sh
# 调根台：重新生成数据并拼出单页
# - index.html：网页版（发布到 claude.ai Artifact 时连同 data.json 一起发布）
# - 夜莺调根台.html：本地版（数据和 seed.json 里的布局都嵌在页面里，双击即可离线使用）
cd "$(dirname "$0")"
python3 ../../construct/export_viz.py data.json
python3 - <<'PY'
t=open('table.js').read().replace("if (typeof module !== 'undefined') module.exports = { buildTable };","")
code='<script>\n'+open('model.js').read()+'\n'+t+'\n'+open('app.js').read()+'\n</script>\n'
open('index.html','w').write(open('head.html').read()+open('body.html').read()+code)
emb=lambda name, f: f'<script>window.{name}=' + open(f, encoding='utf-8').read().strip().replace('</', '<\\/') + ';</script>\n'
doc='<!doctype html>\n<html lang="zh-CN">\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
open('夜莺调根台.html','w').write(doc+open('head.html').read()+open('body.html').read()
    + emb('TIAOGEN_DATA', 'data.json') + emb('TIAOGEN_SEED', 'seed.json') + code)
PY
echo 已生成 index.html、夜莺调根台.html
