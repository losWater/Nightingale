import copy
import unittest
from unittest.mock import patch
import rebuild as r

class FrequencyAuditTests(unittest.TestCase):
    def setUp(self):
        self.allowed={'曝':{'bao','pu'},'光':{'guang'},'睡':{'shui'},'觉':{'jiao','jue'}}
    def test_exposure_source_error(self):
        value,why,issues=r.decide('曝光','pu4 guang1','baoguang',{('bao4','guang1')},self.allowed)
        self.assertEqual(value,('bao','guang'));self.assertIn('原始两拼音字段矛盾',issues)
    def test_auxiliary_error_not_blindly_used(self):
        value,_,_=r.decide('睡觉','shui4 jiao4','shuijue',{('shui4','jiao4')},self.allowed)
        self.assertEqual(value,('shui','jiao'))
    def test_unresolved_conflict(self):
        self.assertIsNone(r.decide('曝光','pu4 guang1','baoguang',set(),self.allowed)[0])
    def test_reference_conflict_is_quarantined(self):
        self.assertIsNone(r.decide('曝光','pu4 guang1','baoguang',set(),self.allowed,jd={('bao','guang')},jl={('pu','guang')})[0])
    def test_two_agreeing_references_do_not_override_opposing_evidence(self):
        self.assertIsNone(r.decide('曝光','pu4 guang1','puguang',{('pu4','guang1')},self.allowed,jd={('bao','guang')},jl={('bao','guang')})[0])
    def test_stale_input_rejected(self):
        fake=r.fingerprint();fake[next(iter(fake))]='changed'
        with patch.object(r,'fingerprint',return_value=fake):
            with self.assertRaises(RuntimeError):r.check_current()
    def test_reference_tolerance_not_double_counted(self):
        both={('shui','jiao'),('shui','jue')}
        value,_,_=r.decide('睡觉','shui4 jiao4','shuijue',{('shui4','jiao4')},self.allowed,jd=both,jl=both)
        self.assertEqual(value,('shui','jiao'))
    def test_unique_reference_intersection(self):
        value,_,_=r.decide('睡觉','shui4 jiao4','shuijue',set(),self.allowed,jd={('shui','jiao')},jl={('shui','jiao'),('shui','jue')})
        self.assertEqual(value,('shui','jiao'))
    def test_out_of_inventory_override_fails(self):
        with self.assertRaises(ValueError):r.decide('曝光','pu4 guang1','baoguang',set(),self.allowed,{'syllables':['bo','guang']})
    def test_code_and_fly_normalization(self):
        self.assertEqual(r.double_code('bao'),'bc');self.assertEqual(r.double_code('jiao'),'jn')
        self.assertEqual(r.double_code('jue'),'jt');self.assertEqual(r.double_code('nve'),'nt')
        self.assertEqual(r.FLY.get(('百','be')),'bd');self.assertNotIn(('白','be'),r.FLY)
    def test_tone_variants_are_one_syllable(self):
        self.assertEqual(r.options('hao3/hao4'),[{'hao'}])
        self.assertEqual(r.decide('好','hao3/hao4','hao',{('hao3',),('hao4',)},{'好':{'hao'}})[0],('hao',))
    def test_build_integrity_and_exposure(self):
        self.assertTrue(r.check_current()['per_character_conservation'])
        rows=r.table(r.HERE/'分读音字频_审计版.tsv')
        bao=next(x for x in rows if x['汉字']=='曝' and x['拼音']=='bao')
        self.assertGreaterEqual(int(bao['已分配频率']),296)
        exposure=next(x for x in r.table(r.HERE/'逐词分配证据.tsv') if x['词']=='曝露')
        self.assertEqual(exposure['采用'],'pu lu')
        self.assertEqual(len(rows),len({(x['汉字'],x['拼音']) for x in rows}))
        self.assertEqual(len({x['汉字'] for x in rows}),8105)
        for x in r.table(r.HERE/'整字频次守恒.tsv'):
            self.assertEqual(int(x['原始总频']),int(x['已分配频率'])+int(x['待分配频率']))

if __name__=='__main__':unittest.main()
