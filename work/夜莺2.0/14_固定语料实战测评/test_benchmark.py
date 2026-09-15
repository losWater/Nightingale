import unittest
from benchmark import *
class Rules(unittest.TestCase):
 def test_selection(self):
  self.assertEqual([commit(p) for p in range(1,8)],[" ",";","'","= ","=;","='","== "])
 def test_sentence_boundaries(self):
  r=analyze([('a ',1),('b ',1)],2)
  self.assertEqual(r['键对数'],2)
  self.assertAlmostEqual(r['已知总当量'],EQ['a ']+EQ['b '])
 def test_weighted_theory(self):
  r=analyze([('a ',3),('b ',2)],5)
  self.assertEqual(r['总击键'],10)
  self.assertAlmostEqual(r['字均当量'],(3*EQ['a ']+2*EQ['b '])/5)
 def test_missing_equivalence_not_zero(self):
  prior=EQ.pop('a ',None)
  try:self.assertIsNone(analyze([('a ',1)],1)['字均当量'])
  finally:
   if prior is not None:EQ['a ']=prior
 def test_collision_accounting(self):
  fixed=set()
  for f in (P/'results').glob('*/结果.json'):
   r=read(f)
   for mode,d in r['实战'].items():
    self.assertEqual(d['选重次数'],d['字字选重次数']+d['词插入新增字选重次数']+d['实际打词中词词选重次数']+d['单字新增词选重次数'])
    if mode=='纯单字':self.assertEqual(d['字词增量受影响率'],0)
    else:
     fixed.add((d['词词原有非首选尝试次数'],d['词词原有超三选拆词次数']))
     self.assertGreaterEqual(d['单字导致有效词位后移次数'],d['字占位导致拆词次数'])
  self.assertEqual(len(fixed),1)
 def test_all_outputs(self):
  verify();manifest=read(I/'固定清单.json')
  results=list((P/'results').glob('*/结果.json'));self.assertEqual(len(results),7)
  for f in results:
   r=read(f);self.assertEqual(r['固定输入']['sha256'],manifest['sha256'])
   for mode,d in r['实战'].items():
    self.assertTrue(d['可计分']);self.assertEqual(d['目标字次'],155026);self.assertEqual(d['输出字次'],155026)
    trace=read(f.parent/(mode+'_逐句按键.json'));self.assertEqual(len(trace),10000)
    self.assertEqual(sum(len(x['按键']) for x in trace),d['总击键'])
    self.assertEqual(sum(d['按键次数'].values()),d['总击键'])
    self.assertEqual(sum(d['编码键热力'].values()),d['编码键'])
    for x in trace:
     self.assertEqual(x['按键'],''.join(e['码']+commit(e['位']) for e in x['事件']))
     self.assertTrue(all(len(e['码'])==4 for e in x['事件'] if len(e['目标'])>1))
if __name__=='__main__':unittest.main()
