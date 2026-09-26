"""Archive a maintenance cycle and start the next; never publish a release."""
import argparse
import csv
import datetime
import json
from pathlib import Path
import re
import shutil
import subprocess
from context import load, sha, atomic, json_bytes
from apply_ledger import FIELDS

def transition(root, version, apply=False):
    root, old, meta = load(root, writable=True)
    if not re.fullmatch(r'\d+\.\d+(?:\.\d+)?', version):
        raise ValueError('版本号格式应为 2.6 或 3.0 等')
    if tuple(map(int, version.split('.'))) <= tuple(map(int, meta['version'].split('.'))):
        raise ValueError('新版本必须大于当前版本')
    new = root/('夜莺'+version)
    if new.exists(): raise ValueError('目标目录已存在，拒绝覆盖')
    with (old/'记录/修改台账.tsv').open() as f:
        if any(r['状态'] == '待处理' for r in csv.DictReader(f, delimiter='\t')):
            raise ValueError('有待处理台账，不能封存')
    print(f'封存 {old.name} → 建立 {new.name}（不会发布、推送或部署）')
    if not apply:
        print('预演；确认新版本已发布后加 --apply')
        return
    # New cycle inherits source/config, not build products, backups or old ledger.
    new.mkdir()
    for name in ('主表', '资料', '配置'):
        shutil.copytree(old/name, new/name)
    (new/'记录').mkdir()
    (new/'记录/修改台账.tsv').write_text('\t'.join(FIELDS)+'\n')
    now = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
    atomic(new/'版本.json', json_bytes({'version':version, 'status':'active', 'previous':old.name,
                                      'release_tag':'v'+version, 'created_at':now}))
    (new/'README.md').write_text(f'# 夜莺 {version} 维护周期\n\n继承 {old.name} 的主表、资料和配置，修改台账从空表开始。通用入口见仓库根目录 MAINTENANCE.md。\n')
    # Store exact shared tool sources so an archive does not depend on future tools.
    bundle = old/'记录/封存工具源码.zip'
    import zipfile
    with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as z:
        for tool_dir in ('maintenance','rime_mac'):
            for p in sorted((root/'tools'/tool_dir).rglob('*')):
                if p.is_file() and '__pycache__' not in p.parts:
                    if p.suffix in ('.py', '.lua', '.yaml', '.md', '.c'):
                        z.write(p, p.relative_to(root))
    archived = {**meta, 'status':'archived', 'archived_at':now, 'next':new.name}
    atomic(old/'版本.json', json_bytes(archived))
    hashes = {str(p.relative_to(old)):sha(p) for p in sorted(old.rglob('*')) if p.is_file()
              and not ({'产物', '备份'} & set(p.relative_to(old).parts))
              and p.name != '封存校验.json'}
    atomic(old/'记录/封存校验.json', json_bytes(hashes))
    atomic(root/'maintenance.json', json_bytes({'active':new.name}))

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('version'); p.add_argument('--root'); p.add_argument('--apply', action='store_true')
    a = p.parse_args(); transition(a.root, a.version, a.apply)
