from pathlib import Path
from collections import Counter
import csv,html,json

HERE=Path(__file__).resolve().parent
def read(name):
    with (HERE/name).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f,delimiter='\t'))

def main():
    summary=json.loads((HERE/'审计摘要.json').read_text(encoding='utf-8'))
    evidence=read('逐词分配证据.tsv');frequency=read('分读音字频_审计版.tsv')
    counts=Counter(r['依据'] for r in evidence)
    cases=[r for r in evidence if r['词'] in ('曝光','曝露','曝晒','睡觉','音乐','银行','睡着')]
    pending=summary['pending_character_occurrences'];total=summary['core_character_occurrences']
    text=f'''# 夜莺2.0字音频率审计

已检查原始 {summary['raw_rows']:,} 条词频记录。原始数据、旧字频表、两份参考词库均未改写；2.0的根集普查和改动台账已改用本目录入口。

## 本轮结果

- 保留8105字、8454个读音身份。与旧表相比，{summary['changed_pairs']}个字音的已分配频次变化；变化包括纠错、补入证据和移入待分配，不能统称为错读数量。
- 核心字原始出现次数 {total:,}，已分配 {summary['assigned_character_occurrences']:,}，待分配 {pending:,}（{pending/total:.2%}）。每字与总量均守恒。
- 曝光的296次从pu纠正为bao；曝现为bao=296、pu=20、待分配=20。待分配来自单字曝18次、曝光表2次，不擅自指定读音。
- 已保存每一行的原始拼音、辅助拼音、Chai、简单鹤、鲸凉鹤、采用读音和理由。字段矛盾或不可核验的{summary['conflict_or_uncheckable_rows']:,}行另列，包含已解决项，不等于全部仍有错误。
- 核心根评估复核：秉新增0对；暴仍新增暴—曝(bao)首根冲突且末根也同组。扩展字逐音与全量取根仍未完成。

## 规则

1. 声调不参与本轮音节划分，hao3/hao4均算hao；r按er归一。原始两个字段都可能有错，不能机械择一。
2. 简单鹤、鲸凉鹤只解析二字词四码。按字符限定还原已知飞键：百be→bd、几jo→ji、一ei→yi、鹤eh→he。未知码、不唯一解码、三字以上缩写不猜测，另表留存。
3. 参考中的多个码可能是容错或异读，不把每个码都累计一遍。两参考共同读音唯一时采用；两参考有多个共同读音时需原始音节与Chai一致才能选择；证据对立则待分配。
4. 已有逐词人工裁决优先保留，包括曝露pu lu。两份参考可能共享错误，不能把一致等同于绝对正确；若两鹤与原始音节、Chai形成两组相反的一致证据，不自动覆盖。
5. 孤立多音字若去调仍有多个音节，没有语境就保持待分配。历史人工/Unihan比例分配另列并保留来源，不能冒充逐次实测。单字重复行归入同一池，仅应用一次既有分配。
6. 已分配为0不表示现实零频。读音覆盖判断保留所有8454身份；加权判断须同时考虑待分配量。整字排名采用原始整字总频，不把未分配量丢掉。

## 数据入口与更新

- `分读音字频_审计版.tsv`：2.0分音证据，含每字待分配量（多音行重复展示，不能跨音节相加）。
- `整字频次守恒.tsv`：每字一行，整字字频与待分配的唯一求和入口。
- `逐词分配证据.tsv`、`拼音矛盾核对.tsv`、`待分配词条.tsv`：追溯与后续人工核对。
- `参考飞键还原.tsv`、`参考码无法解读.tsv`：参考解析依据。
- `单字历史裁决记账.tsv`：人工/比例分配来源，不与词内计数重复累计。

更新顺序：运行rebuild.py、test_rebuild.py，再运行recheck_roots.py与根集普查build_report.py。根集普查和台账会先检查输入/输出指纹；源词库、规则或产物变化但未重建时拒绝继续使用旧结果。台账保留旧评估，新结果追加记录。

本轮修复的是可追溯生成和检查入口，不宣称所有词条读音已人工逐条定案。待分配项已隔离，可继续做保守的是否冲突检查；尚不能把这些数值作为无缺口的精确退火权重。历史1.0脚本仅保留复现用途，不作为2.0频率入口。

## 典型词条

| 词 | 原拼音 | 简单鹤 | 鲸凉鹤 | 采用 | 理由 |
|---|---|---|---|---|---|
'''
    text+='\n'.join('| '+' | '.join(r[k].replace('|','／') for k in ('词','原拼音','简单鹤','鲸凉鹤','采用','依据'))+' |' for r in cases)+'\n'
    (HERE/'审计说明.md').write_text(text,encoding='utf-8')
    columns=['词','词频','原拼音','辅助拼音','简单鹤','鲸凉鹤','采用','依据']
    rows=''.join('<tr>'+''.join('<td>'+html.escape(r[k])+'</td>' for k in columns)+'</tr>' for r in cases)
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>字音频率审计</title><style>body{font:17px/1.65 "Microsoft YaHei",sans-serif;max-width:1450px;margin:30px auto;padding:20px;background:#f4f7fa;color:#203649}table{border-collapse:collapse;background:white;width:100%}td,th{padding:10px;border:1px solid #cbd8e1;text-align:left}th{background:#dce9ee}input{font:inherit;padding:9px}p{max-width:1050px}.scroll{overflow:auto}</style><h1>夜莺2.0 · 字音频率审计</h1>'''
    page+=f'<p>已检查 {summary["raw_rows"]:,} 条原始词频记录。核心字频次守恒；仍有 {pending/total:.2%} 的核心字出现次数待分配，单独保留。</p>'
    page+='<p>曝光：<b>bao 296</b>；曝字合计：bao 296、pu 20、待分配20。两鹤词库去飞键后交叉核验，兼容码不重复累计频次。</p><p><a href="审计说明.md">规则与完整说明</a> · <a href="../02_改动台账/改动总表.html">改动台账</a></p><h2>典型词条</h2><div class="scroll"><table><tr>'+''.join('<th>'+k+'</th>' for k in columns)+'</tr>'+rows+'</table></div><h2>逐字查询</h2><p>输入一个字，查看它的各读音。每行的待分配量属于整个字，不能重复相加。已分配为0不表示现实零频。</p><input id="q" value="曝" maxlength="2"><div id="result" class="scroll"></div>'
    page+='<script>const data='+json.dumps(frequency,ensure_ascii=False).replace('<','\\u003c')+''';function show(){const rows=data.filter(r=>r['汉字']===document.getElementById('q').value.trim());const box=document.getElementById('result');box.replaceChildren();if(!rows.length){box.textContent='未找到核心字记录';return}const table=document.createElement('table');const header=document.createElement('tr');Object.keys(rows[0]).forEach(k=>{const th=document.createElement('th');th.textContent=k;header.append(th)});table.append(header);rows.forEach(r=>{const tr=document.createElement('tr');Object.values(r).forEach(v=>{const td=document.createElement('td');td.textContent=v;tr.append(td)});table.append(tr)});box.append(table)}document.getElementById('q').oninput=show;show()</script></html>'''
    (HERE/'审计结果.html').write_text(page,encoding='utf-8')

if __name__=='__main__':main()
