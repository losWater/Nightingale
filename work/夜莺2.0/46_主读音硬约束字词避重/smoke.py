
from pathlib import Path
P=Path(__file__).resolve().parent
ns={'__file__':str(P/'controller.py')}
exec((P/'controller.py').read_text(encoding='utf8').split('try:\n')[0],ns)
globals().update(ns)
d=P/'硬约束原权重'; cfg=read(d/'initial.json')
cfg['optimization']['metaheuristic']['parameters']['steps']=1000
out=run('optimize',cfg,d/'elements.yaml',d/'短跑核验')
check_gate(out)
delta=float(re.search(r'TRIAL_CACHE_DELTA ([^\s]+)',(d/'短跑核验/stderr.log').read_text(encoding='utf8'))[1])
assert delta<1e-7
final=yaml.load((out/'config.yaml').read_text(encoding='utf8'),Loader=yaml.CSafeLoader)
final['generated_mapping_space']=cfg['generated_mapping_space']
v=run('encode',final,d/'elements.yaml',d/'短跑重算')
assert (out/'code.txt').read_bytes()==(v/'code.txt').read_bytes()
badres=read(W/'45_主读音准入与字词避重试跑/避重4倍/result.json')
bad=yaml.load((Path(badres['输出目录'])/'config.yaml').read_text(encoding='utf8'),Loader=yaml.CSafeLoader)
bad['generated_mapping_space']=cfg['generated_mapping_space']
bad['optimization']['metaheuristic']['parameters']['steps']=5
rejected=False
try:run('optimize',bad,d/'elements.yaml',d/'坏起点核验')
except AssertionError:
 assert 'initial layout fails primary reading hard constraint' in (d/'坏起点核验/stderr.log').read_text(encoding='utf8')
 rejected=True
assert rejected
write(P/'硬约束功能核验.json',{'短跑步数':1000,'可行结果':True,'缓存差异':delta,'重编码逐字节一致':True,'坏起点确实拒绝':True,'日志':(d/'短跑核验/stderr.log').read_text(encoding='utf8')})
print('SMOKE PASS',flush=True)
