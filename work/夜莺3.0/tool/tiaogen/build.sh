#!/bin/sh
# 调根台：重新生成数据并拼出单页 index.html（发布到 claude.ai Artifact 时连同 data.json 一起发布）
cd "$(dirname "$0")"
python3 ../../construct/export_viz.py data.json
python3 - <<'PY'
t=open('table.js').read().replace("if (typeof module !== 'undefined') module.exports = { buildTable };","")
open('index.html','w').write(open('head.html').read()+open('body.html').read()+'<script>\n'+open('model.js').read()+'\n'+t+'\n'+open('app.js').read()+'\n</script>\n')
PY
echo 已生成 index.html
