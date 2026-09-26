"""Boundary tests use disposable fixtures, never real masters or user data."""
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from apply_ledger import FIELDS, apply_row
from context import load
from rollover import transition

CODE = Path(__file__).resolve().parent

class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='nightingale-maintenance-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.active=self.root/'夜莺7.1'
        for name in ('主表','记录','资料','配置'):(self.active/name).mkdir(parents=True,exist_ok=True)
        (self.root/'maintenance.json').write_text(json.dumps({'active':'夜莺7.1'}))
        (self.active/'版本.json').write_text(json.dumps({'version':'7.1','status':'active'}))
        for name in ('单字表','字词表'):(self.active/'主表'/(name+'.txt')).write_text('甲\taa\n乙\tab\n')
        (self.active/'主表/符号表.txt').write_text('！\toa\n')
        (self.active/'配置/单字版差异.json').write_text('[]\n')
        self.ledger([])

    def ledger(self,rows):
        with (self.active/'记录/修改台账.tsv').open('w') as f:
            w=csv.DictWriter(f,fieldnames=FIELDS,delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(rows)

    def row(self,table='单字表',id='T-1'):
        return {**dict.fromkeys(FIELDS,''),'问题ID':id,'状态':'待处理','目标码表':table,
                '操作':'改码','原编码':'aa','原字词':'甲','新编码':'ac'}

    def snapshot(self):
        return {str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def run_ledger(self,*args):
        return subprocess.run([sys.executable,str(CODE/'apply_ledger.py'),'--root',str(self.root),*args],capture_output=True,text=True)

    def test_preview_is_read_only(self):
        self.ledger([self.row(),self.row('字词表','T-2')]);before=self.snapshot()
        self.assertEqual(self.run_ledger().returncode,0);self.assertEqual(before,self.snapshot())

    def test_apply_then_repeat_is_noop(self):
        self.ledger([self.row(),self.row('字词表','T-2')]);result=self.run_ledger('--apply')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('甲\tac',(self.active/'主表/单字表.txt').read_text())
        with (self.active/'记录/修改台账.tsv').open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
        self.assertTrue(all(r['状态']=='已修复' and len(r['修改后SHA256'])==64 for r in rows))
        self.assertTrue(list((self.active/'备份').glob('*/修改台账.tsv')))
        before=self.snapshot();self.assertEqual(self.run_ledger('--apply').returncode,0);self.assertEqual(before,self.snapshot())

    def test_mismatched_tables_refuse_write(self):
        self.ledger([self.row()]);before=self.snapshot()
        self.assertNotEqual(self.run_ledger('--apply').returncode,0);self.assertEqual(before,self.snapshot())

    def test_invalid_baseline_fails_even_without_pending(self):
        (self.active/'主表/单字表.txt').write_text('甲\taa\n')
        self.assertNotEqual(self.run_ledger().returncode,0)

    def test_duplicate_id_refused(self):
        self.ledger([self.row(),self.row('字词表')]);before=self.snapshot()
        self.assertNotEqual(self.run_ledger('--apply').returncode,0);self.assertEqual(before,self.snapshot())

    def test_bad_empty_header_refused(self):
        (self.active/'记录/修改台账.tsv').write_text('错误字段\n')
        self.assertNotEqual(self.run_ledger('--apply').returncode,0)

    def test_completed_platform_rows_are_not_executed(self):
        r=self.row('Mac单字版');r['状态']='本地已应用';self.ledger([r]);before=self.snapshot()
        self.assertEqual(self.run_ledger('--apply').returncode,0);self.assertEqual(before,self.snapshot())

    def test_rollover_preview_and_archive_guard(self):
        before=self.snapshot();transition(self.root,'7.2');self.assertEqual(before,self.snapshot())
        transition(self.root,'7.2',True)
        self.assertEqual(load(self.root)[1].name,'夜莺7.2')
        with self.assertRaises(ValueError):load(self.root,'夜莺7.1',writable=True)
        old=self.snapshot()
        self.assertNotEqual(self.run_ledger('--version','夜莺7.1','--apply').returncode,0)
        self.assertEqual(old,self.snapshot())
        new=self.root/'夜莺7.2'
        self.assertEqual((new/'记录/修改台账.tsv').read_text(),'\t'.join(FIELDS)+'\n')
        manifest=json.loads((self.active/'记录/封存校验.json').read_text())
        for name,digest in manifest.items():self.assertEqual(hashlib.sha256((self.active/name).read_bytes()).hexdigest(),digest)

    def test_rollover_rejects_pending_existing_or_older(self):
        self.ledger([self.row()])
        with self.assertRaises(ValueError):transition(self.root,'7.2',True)
        self.ledger([])
        with self.assertRaises(ValueError):transition(self.root,'7.0',True)
        (self.root/'夜莺7.2').mkdir()
        with self.assertRaises(ValueError):transition(self.root,'7.2',True)

    def test_no_path_escape(self):
        with self.assertRaises(ValueError):load(self.root,'../夜莺7.1')

    def test_atomic_operations(self):
        rows=[('甲','aa'),('乙','aa')];r=self.row();r.update({'操作':'调序','目标候选位':'2'})
        apply_row(rows,r);self.assertEqual(rows,[('乙','aa'),('甲','aa')])
        r.update({'操作':'改词','新字词':'丙'});apply_row(rows,r);self.assertEqual(rows[-1],('丙','aa'))
        r.update({'操作':'新增','新字词':'丁','新编码':'ab','目标候选位':'1'});apply_row(rows,r)
        r.update({'操作':'删除','原字词':'丁','原编码':'ab'});apply_row(rows,r)
        r.update({'操作':'查询','原编码':'aa'});self.assertIn('乙、丙',apply_row(rows,r))

    def test_split_preview_apply_and_record(self):
        roots=[{'根':'首','键':'b'},{'根':'末','键':'c'}]
        data={'甲':{'新拆':'首 ＋ 末','根':roots},'乙':{'新拆':'中','根':[{'根':'中','键':'d'}]}}
        query='const D = '+json.dumps(data,ensure_ascii=False)+';'
        source=self.active/'资料/拆分原本.html'
        source.write_text('const views = '+json.dumps({'query':query},ensure_ascii=False)+';')
        command=[sys.executable,str(CODE/'edit_split.py'),'甲=首＋中＋末','--root',str(self.root)]
        before=self.snapshot();r=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(before,self.snapshot())
        r=subprocess.run(command+['--apply'],capture_output=True,text=True)
        self.assertNotEqual(r.returncode,0);self.assertEqual(before,self.snapshot())
        r=subprocess.run(command+['--apply','--reason','测试拆分修订'],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        with (self.active/'记录/修改台账.tsv').open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['操作'],'改拆分')
        self.assertEqual(rows[0]['修改后SHA256'],hashlib.sha256(source.read_bytes()).hexdigest())

if __name__=='__main__':unittest.main()
