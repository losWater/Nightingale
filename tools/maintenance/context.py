"""One active version; no version literal or platform-specific absolute paths."""
from pathlib import Path
import hashlib
import json
import os

REPO = Path(__file__).resolve().parents[2]

def load(root=None, version=None, writable=False):
    root = Path(root or os.environ.get('NIGHTINGALE_REPO', REPO)).resolve()
    active = json.loads((root/'maintenance.json').read_text())['active']
    name = version or active
    if not isinstance(name, str) or Path(name).name != name or name in ('.', '..'):
        raise ValueError('非法版本目录')
    directory = root/name
    if directory.is_symlink():
        raise ValueError('版本目录不能是符号链接')
    meta = json.loads((directory/'版本.json').read_text())
    if name != '夜莺' + meta['version']:
        raise ValueError('目录与版本配置不一致')
    if writable and (name != active or meta['status'] != 'active'):
        raise ValueError('版本已封存或不是当前版本，禁止写入')
    return root, directory, meta

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def atomic(path, data):
    path = Path(path)
    temp = path.with_name(path.name + '.tmp')
    temp.write_bytes(data)
    temp.replace(path)

def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode()

def table_paths(directory):
    return {n: directory/'主表'/(n+'.txt') for n in ('单字表', '字词表', '符号表')}
