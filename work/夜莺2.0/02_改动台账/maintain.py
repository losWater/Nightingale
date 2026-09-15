"""生成改动台账；检查源数据和已确认方案变化是否使旧评估过期。"""
import hashlib
import html
import json
import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCES = [
    'work/夜莺2.0/评估规则.md',
    'work/重开工程/01_根集/根集_待完整性复核.yaml',
    'work/重开工程/02_规范拆分/最终规范拆分表_待核验.tsv',
    'work/夜莺2.0/03_字音频率审计/分读音字频_审计版.tsv',
    'work/夜莺2.0/03_字音频率审计/审计摘要.json',
    'work/夜莺0.85/10_扩展字Chai实验/20260830_034806+1000/扩展字规范拆分_候选.tsv',
]

def source_hashes():
    runpy.run_path(str(ROOT/'work/夜莺2.0/03_字音频率审计/rebuild.py'))['check_current']()
    return {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}

def confirmed_state(entries):
    return {e['id']: e['proposal'] for e in entries if e['decision'] == '已确认'}

def stale_reasons(entry, entries, hashes):
    if not entry.get('evaluations'):
        return ['尚未评估']
    assessment = entry['evaluations'][-1]
    reasons = []
    for p, digest in hashes.items():
        if assessment['source_hashes'].get(p) != digest:
            reasons.append('依据变化：'+p)
    # 完整方案签名是保守兜底：另一字族的变化也可能引入同音冲突。
    # 本条自身不计入上下文，以便在其评估获准后正常保存结果。
    current = {k:v for k,v in confirmed_state(entries).items() if k != entry['id']}
    if current != assessment['confirmed_context']:
        reasons.append('其他已确认改动新增、修改或撤回：须按累计方案重算')
    if entry['proposal'] != assessment['proposal']:
        reasons.append('本条方案内容已变化')
    return reasons

def render(data):
    hashes = source_hashes()
    entries = data['entries']
    rows=[]
    for e in entries:
        reasons=stale_reasons(e, entries, hashes)
        state='待评估' if not e.get('evaluations') else '待重算' if reasons else '已有评估（范围受限）'
        evaluation=e.get('evaluations',[])
        result=evaluation[-1]['summary'] if evaluation else '—'
        if state=='待重算': result='旧结果，仅供追溯：'+result
        rows.append([e['id'],e['title'],e['decision'],e['implementation'],state,
                     e['proposal']['description'],'、'.join(e['dependencies']['roots']),
                     '、'.join(e['dependencies']['characters']) or '待提取',result,
                     '；'.join(reasons) or e['evaluations'][-1]['limitations']])
    headings=['编号','改动','决定','实装','评估状态','方案','相关根/组','已知涉及字','评估记录','待办或限制']
    intro='''# 夜莺2.0改动台账

这是2.0的统一改动入口，保留候选、已确认、撤回和替代记录。决定、实装、评估有效性分别记录。

每次新增、调整、撤回方案或重算前，运行 maintain.py 更新本表。它不会常驻监听，也不会修改正式方案。

评估绑定根集、拆分、读音频率、扩展字数据的文件指纹，以及当时其他已确认改动的内容。任何依据变化，或其他已确认改动变化，旧评估即标为“待重算”。当前采用保守策略：即使不直接共享根，也先标记，以免漏掉同音字族之间的间接影响。依赖根列表用于定位，不能代替全字表比较。

重算必须使用累计已确认方案；同时记录“当前累计方案有本条”和“当前累计方案无本条”的差异。不能只和1.0旧表比较。遇到拆分与加根先后依赖时先解决依赖；这里只管理记录与过期检查，尚未实现自动重拆或冲突重算。

旧评估追加保留，不覆盖；待重算不等于撤销决定。正式根集、码表和发布包不由本工具改动。

逐根删除筛选见[批量影响排行](../04_逐根删除评估/逐根删除影响排行.html)及[计算口径](../04_逐根删除评估/评估说明.md)。批量结果只是候选评估，不自动新增已确认删根决定；含人工结构的条件试算仍需逐字复核。

'''
    md=intro+'| '+' | '.join(headings)+' |\n|'+'|'.join(['---']*len(headings))+'|\n'
    md+='\n'.join('| '+' | '.join(str(v).replace('|','／').replace('\n',' ') for v in row)+' |' for row in rows)+'\n'
    (HERE/'改动总表.md').write_text(md,encoding='utf-8')
    body=''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in row)+'</tr>' for row in rows)
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>夜莺2.0改动台账</title><style>body{font:16px/1.7 "Microsoft YaHei",sans-serif;background:#f5f7fa;color:#233548;margin:30px}table{border-collapse:collapse;background:white}td,th{padding:10px;border:1px solid #cdd9e0;vertical-align:top;min-width:90px}th{background:#dce9ee;position:sticky;top:0}input{font:inherit;padding:8px}p{max-width:1000px}</style><h1>夜莺2.0改动台账</h1><p>候选11项，已确认拆根1项。决定、实装、评估状态分别记录。依据或其他已确认方案变化后，运行维护工具会把旧评估标为待重算；不会自动重拆，也不会撤销决定。</p><p><a href="改动总表.md">完整维护说明</a> · <a href="../01_根集普查/秉删根评估.md">秉的评估依据</a></p><input id="q" placeholder="搜索根、字或状态"><table><thead><tr>'''
    page=page.replace('<input id="q"','<p><a href="../04_逐根删除评估/逐根删除影响排行.html">逐根删除批量影响排行</a>（筛选试算，不代表删根定案）</p><input id="q"')
    page+=''.join('<th>'+h+'</th>' for h in headings)+'</tr></thead><tbody>'+body+'</tbody></table>'
    page+='''<script>document.getElementById('q').oninput=function(){document.querySelectorAll('tbody tr').forEach(r=>r.hidden=!r.textContent.includes(this.value.trim()))}</script></html>'''
    page=page.replace('候选11项，已确认拆根1项',f"候选{sum(e['decision']=='候选' for e in entries)}项，已确认{sum(e['decision']=='已确认' for e in entries)}项")
    (HERE/'改动总表.html').write_text(page,encoding='utf-8')
    return {row[0]:row[4] for row in rows}

if __name__ == '__main__':
    data=json.loads((HERE/'改动台账.json').read_text(encoding='utf-8'))
    print(json.dumps(render(data),ensure_ascii=False,indent=2))
