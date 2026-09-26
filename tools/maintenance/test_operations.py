"""Semantic add/delete/update regressions, using only disposable data."""
from collections import defaultdict
import contextlib
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from apply_ledger import apply_row, FIELDS, checkup, render
from semantics import evolve, full_codes, apply_overrides, metadata
from export import export

CODE=Path(__file__).resolve().parent
def row(op,**kwargs):return {**dict.fromkeys(FIELDS,''),'问题ID':'T','操作':op,'状态':'待处理','目标码表':'单字表',**kwargs}

class OperationTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='nightingale-operation-test-');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.active=self.root/'夜莺7.1'
        for d in ('主表','配置','资料','记录'):(self.active/d).mkdir(parents=True,exist_ok=True)
        (self.root/'maintenance.json').write_text(json.dumps({'active':'夜莺7.1'}))
        (self.active/'版本.json').write_text(json.dumps({'version':'7.1','status':'active'}))
        self.before={'单字表':[('甲','a'),('甲','aaxx'),('乙','bbyy')],
                     '字词表':[('甲','a'),('甲','aaxx'),('乙','bbyy')],'符号表':[]}
        self.save(self.before)
        (self.active/'主表/快符.txt').write_text('a,2=！\n')
        (self.active/'配置/单字版差异.json').write_text('[]')
        self.data={c:{'新拆':r,'根':[{'根':r,'键':key}]} for c,r,key in [('甲','甲根','x'),('乙','乙根','y')]}
        self.save_splits()
        assets=self.root/'assets/rime';assets.mkdir(parents=True)
        for name in ('mohu-release.json','rime_api.h'):(assets/name).write_text('{}')
        with zipfile.ZipFile(assets/'nightingale-2.5-light.zip','w') as z:
            z.writestr('yeying20_rime_short.dict.yaml','...\n甲\taa;xx\t100\n乙\tbb;yy\t90\n')
            z.writestr('lua/yeying20_lookup_data.lua','return {["pinyin"]={["jia"]="aa",["yi"]="bb"}}')

    def save(self,tabs):
        for n,rows in tabs.items():(self.active/'主表'/(n+'.txt')).write_bytes(render(rows))
    def save_splits(self):
        query='const D = '+json.dumps(self.data,ensure_ascii=False)+';'
        (self.active/'资料/拆分原本.html').write_text('const views = '+json.dumps({'query':query},ensure_ascii=False)+';')
    def change(self,r):
        after={k:list(v) for k,v in self.before.items()}
        for n in ('单字表','字词表'):apply_row(after[n],r)
        return after
    def run_export(self):
        with contextlib.redirect_stdout(io.StringIO()):return export(self.root)

    def test_invalid_fields_and_required_values(self):
        for r in [row('新增',新字词='甲',新编码=c) for c in ('A1','a\tb','a\nb',' a')]+[
            row('新增',新字词=t,新编码='aa') for t in ('坏\t词','坏\n词','甲\x00',' 甲','')]:
            with self.subTest(r=r),self.assertRaises(ValueError):apply_row([],r)
        self.assertTrue(checkup({'单字表':[], '字词表':[('坏\t词','aa')], '符号表':[]}))

    def test_full_add_requires_explicit_type(self):
        r=row('新增',新字词='甲',新编码='abxx')
        with self.assertRaisesRegex(ValueError,'必须注明'):evolve(self.active,[r],self.before,self.change(r))

    def test_normal_short_requires_prefix(self):
        r=row('新增',新字词='甲',新编码='zz',备注='类型=简码')
        with self.assertRaisesRegex(ValueError,'前缀'):evolve(self.active,[r],self.before,self.change(r))

    def test_valid_short_no_automatic_full_reorder(self):
        r=row('新增',新字词='甲',新编码='aa',备注='类型=简码')
        after=self.change(r);m,w=evolve(self.active,[r],self.before,after)
        self.assertIn(('甲','aaxx'),after['单字表']);self.assertTrue(w)

    def test_tolerance_does_not_create_readings(self):
        r=row('新增',新字词='甲',新编码='abzz',备注='类型=容错码')
        after=self.change(r);m,_=evolve(self.active,[r],self.before,after)
        (self.active/'配置/编码类型.json').write_text(json.dumps(m,ensure_ascii=False));self.save(after)
        mac=self.run_export();generated=mac/'generated'
        self.assertIn('甲\tabzz\t',(generated/'yeying25_mac_rime_fixed.dict.yaml').read_text())
        self.assertNotIn('甲\tab;zz\t',(generated/'yeying25_mac_rime.dict.yaml').read_text())
        self.assertNotIn('["ab"]=',(generated/'yeying25_mac_lookup_data.lua').read_text())

    def test_new_character_requires_split(self):
        r=row('新增',新字词='丙',新编码='bcxy',备注='类型=全码')
        with self.assertRaisesRegex(ValueError,'先登记拆分'):evolve(self.active,[r],self.before,self.change(r))

    def test_new_split_registration_then_full_add(self):
        (self.active/'记录/修改台账.tsv').write_text('\t'.join(FIELDS)+'\n')
        command=[sys.executable,str(CODE/'edit_split.py'),'丙=甲根＋乙根','--root',str(self.root),'--add','--reason','测试新字']
        p=subprocess.run(command+['--apply'],capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr)
        r=row('新增',新字词='丙',新编码='bcxy',备注='类型=全码');after=self.change(r)
        m,_=evolve(self.active,[r],self.before,after);self.save(after)
        (self.active/'配置/编码类型.json').write_text(json.dumps(m))
        mac=self.run_export();self.assertIn('丙\tbc;xy\t',(mac/'generated/yeying25_mac_rime.dict.yaml').read_text())

    def test_last_full_code_cannot_leave_short(self):
        r=row('删除',原字词='甲',原编码='aaxx')
        with self.assertRaisesRegex(ValueError,'没有正式全码'):evolve(self.active,[r],self.before,self.change(r))

    def test_deleting_entire_character_is_explicit_and_allowed(self):
        after={k:[p for p in v if p[0]!='甲'] for k,v in self.before.items()}
        m,w=evolve(self.active,[],self.before,after);self.assertTrue(w)

    def test_deleting_short_keeps_full(self):
        r=row('删除',原字词='甲',原编码='a')
        after=self.change(r);m,w=evolve(self.active,[r],self.before,after)
        self.assertEqual(full_codes(after['单字表'],m)['甲','aa'],['aaxx']);self.assertTrue(w)

    def test_overlay_refuses_resurrection(self):
        changes=[{'record':'T','operation':'insert','text':'子','code':'zi','position':1,'expected_candidates':[], 'requires':[['子','zip']]}]
        with self.assertRaisesRegex(ValueError,'依赖'):apply_overrides(defaultdict(list),changes)

    def test_overlay_refuses_changed_slot(self):
        changes=[{'record':'T','operation':'delete','text':'甲','code':'a','expected_candidates':['甲']}]
        with self.assertRaisesRegex(ValueError,'冲突'):apply_overrides(defaultdict(list,{'a':['乙','甲']}),changes)

    def test_word_readings_create_long_sentence_entry(self):
        self.before['字词表'].append(('甲乙甲乙','abab'));self.save(self.before)
        (self.active/'配置/词语读音.json').write_text(json.dumps({'甲乙甲乙':['aa','bb','aa','bb']}))
        mac=self.run_export()
        self.assertIn('甲乙甲乙\taa;xx bb;yy aa;xx bb;yy\t',(mac/'generated/yeying25_mac_rime.dict.yaml').read_text())

    def test_missing_word_readings_report_without_removal(self):
        self.before['字词表'].append(('甲乙甲乙','abab'));self.save(self.before)
        mac=self.run_export();report=json.loads((self.active/'产物/缺读音词条.json').read_text())
        self.assertEqual(report[0]['字词'],'甲乙甲乙')
        self.assertIn('甲乙甲乙\tabab\t',(mac/'generated/yeying25_mac_rime_fixed.dict.yaml').read_text())

    def test_short_word_only_in_short_dictionary_without_readings(self):
        self.before['字词表'].append(('甲乙甲','aba'));self.save(self.before);mac=self.run_export()
        self.assertNotIn('甲乙甲\taba\t',(mac/'generated/yeying25_mac_rime.dict.yaml').read_text())
        self.assertIn('甲乙甲\taba\t',(mac/'generated/yeying25_mac_rime_short.dict.yaml').read_text())

    def test_invalid_readings_fail_before_outputs(self):
        (self.active/'配置/词语读音.json').write_text(json.dumps({'甲乙':['zz','bb']}))
        with self.assertRaisesRegex(ValueError,'读音'):self.run_export()
        self.assertFalse((self.active/'产物').exists())

    def test_export_repeats_without_model_downloads(self):
        self.run_export();self.run_export()

    def run_pending(self,r):
        records=[]
        for n,table in enumerate(('单字表','字词表'),1):records.append({**r,'问题ID':f'T-{n}','目标码表':table})
        with (self.active/'记录/修改台账.tsv').open('w') as f:
            writer=csv.DictWriter(f,fieldnames=FIELDS,delimiter='\t',lineterminator='\n');writer.writeheader();writer.writerows(records)
        return subprocess.run([sys.executable,str(CODE/'apply_ledger.py'),'--root',str(self.root),'--apply'],capture_output=True,text=True)

    def test_tolerance_transaction_persists_type_and_ledger(self):
        p=self.run_pending(row('新增',新字词='甲',新编码='abzz',备注='类型=容错码'))
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(metadata(self.active)['entries'][0]['type'],'容错码')
        with (self.active/'记录/修改台账.tsv').open() as f:records=list(csv.DictReader(f,delimiter='\t'))
        self.assertTrue(all(r['状态']=='已修复' and '编码类型SHA256=' in r['处理结果'] for r in records))
        self.assertTrue(list((self.active/'备份').glob('*/修改台账.tsv')))

    def test_invalid_transaction_preserves_master_bytes(self):
        original=(self.active/'主表/单字表.txt').read_bytes()
        p=self.run_pending(row('新增',新字词='甲',新编码='A1'))
        self.assertNotEqual(p.returncode,0)
        self.assertEqual((self.active/'主表/单字表.txt').read_bytes(),original)
        self.assertFalse((self.active/'备份').exists())

    def test_missing_split_transaction_is_rejected_before_commit(self):
        original=(self.active/'主表/单字表.txt').read_bytes()
        p=self.run_pending(row('新增',新字词='丙',新编码='bcxy',备注='类型=全码'))
        self.assertNotEqual(p.returncode,0);self.assertIn('先登记拆分',p.stderr)
        self.assertEqual((self.active/'主表/单字表.txt').read_bytes(),original)

    def test_overlay_conflict_rejected_during_ledger_preflight(self):
        changes=[{'record':'T','operation':'insert','text':'甲','code':'aa','position':1,'expected_candidates':[], 'requires':[['甲','a']]}]
        (self.active/'配置/单字版差异.json').write_text(json.dumps(changes))
        original=(self.active/'主表/单字表.txt').read_bytes()
        p=self.run_pending(row('删除',原字词='甲',原编码='a'))
        self.assertNotEqual(p.returncode,0);self.assertIn('依赖',p.stderr)
        self.assertEqual((self.active/'主表/单字表.txt').read_bytes(),original)

if __name__=='__main__':unittest.main()
