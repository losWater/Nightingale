import unittest,json
from pathlib import Path
from report import pair_sets,added_sets,local_recovery
HERE=Path(__file__).resolve().parent
class Metrics(unittest.TestCase):
    def test_cross_position_is_not_collision(self):
        self.assertEqual(pair_sets({'甲':['x','y'],'乙':['y','x']},{'甲':{'a'},'乙':{'a'}},lambda x:x),(set(),set()))
    def test_group_and_reading_identity(self):
        h,t=pair_sets({'甲':['x','z'],'乙':['y','w']},{'甲':{'a','b'},'乙':{'a','b'}},lambda x:'g' if x in ('x','y') else x)
        self.assertEqual(h,{('a','乙','甲'),('b','乙','甲')});self.assertFalse(t)
    def test_preexisting_other_side_and_dedup(self):
        p=('a','甲','乙');h,t,u,b=added_sets(({p},set()),({p},{p}))
        self.assertFalse(h);self.assertEqual(t,{p});self.assertEqual(u,{p});self.assertEqual(b,{p})
        self.assertEqual(added_sets((set(),set()),({p},{p}))[2],{p})
    def test_local_structure_keeps_other_decisions(self):
        self.assertEqual(local_recovery(['女','冓头','冂','土'],['女','一','龷','冂','丨','二'],'冓头'),['女','一','龷','冂','土'])
    def test_ambiguous_recovery_rejected(self):
        with self.assertRaises(ValueError):local_recovery(['根','甲'],['乙'],'根')
class Artifacts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.d=json.loads((HERE/'评估结果.json').read_text(encoding='utf-8'))
    def test_every_target_has_result(self):
        self.assertEqual(len(self.d['roots']),403);self.assertTrue(all('加权影响'in r for r in self.d['roots']))
    def test_aliases_are_removed_together(self):
        inp=json.loads((HERE/'input.json').read_text(encoding='utf-8'))
        for name in ['⺈','小']:
            t=next(t for t in inp['targets'] if t['id']==name);self.assertEqual(len(t['ids']),2)
    def test_scores_and_means(self):
        for r in self.d['roots']:
            self.assertEqual(r['加权影响'],sum(p['权重'] for p in r['新增对']))
            self.assertEqual(r['新增对数'],len(r['新增对']))
            self.assertTrue(all(p['权重']==min(p['字1分读音频次'],p['字2分读音频次']) for p in r['新增对']))
        for g in self.d['groups']:
            rs=[r for r in self.d['roots'] if r['组']==g['组']]
            self.assertEqual(g['成员数'],len(rs))
            self.assertAlmostEqual(g['平均加权影响'],sum(r['加权影响'] for r in rs)/len(rs))
    def test_frame_order_and_external_suffix(self):
        for root,char,expected in [('行','愆','彳＋氵＋一＋丁＋心'),('辡','辩','辛旁＋讠＋辛'),('玨','斑','王＋文＋王')]:
            r=next(r for r in self.d['roots'] if r['原名']==root)
            self.assertEqual(next(c for c in r['变化'] if c['字']==char)['改后'],expected)
    def test_sorted_and_exclusions(self):
        self.assertEqual([(r['加权影响'],r['新增对数']) for r in self.d['roots']],sorted((r['加权影响'],r['新增对数']) for r in self.d['roots']))
        self.assertTrue({'魚','車','鳥','門','長','馬','龜','黽','戶','1','2','3','4','5','秉','暴'}=={r['id'] for r in self.d['excluded']})
if __name__=='__main__':unittest.main()
