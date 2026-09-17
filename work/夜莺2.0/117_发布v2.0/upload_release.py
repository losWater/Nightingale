# -*- coding: utf-8 -*-
"""把 发布包/ 里的附件传到 GitHub Release v2.0（对外动作，单独一步，不在 export.py 里）。
GitHub 不接受中文附件文件名，所以上传时用英文文件名 + 中文显示名；本地文件保持中文名。旧的同名附件被覆盖；Release 上多余的旧附件（如 SHA256SUMS-*.txt）会列出来并删除。"""
import io, sys, os, json, shutil, subprocess, tempfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); R = 'D:/nightingale/releases/v2.0'; pk = R + '/02_输入法挂接/rime/发布包'; GH = 'C:/Program Files/GitHub CLI/gh.exe'
assets = json.load(open(R + '/发布清单.json', encoding='utf-8'))['release_assets']
tmp = tempfile.mkdtemp(prefix='ngrel_'); args = []
try:
    for name, v in assets.items():
        src = pk + '/' + v['本地文件名']; dst = tmp + '/' + name
        try: os.link(src, dst)
        except OSError: shutil.copy2(src, dst)
        args.append('%s#%s' % (dst, v['显示名']))
    sums = tmp + '/SHA256SUMS.txt'; open(sums, 'w', encoding='utf-8', newline='\n').write(''.join('%s  %s\n' % (v['sha256'], k) for k, v in assets.items())); args.append(sums + '#校验值（SHA256）')
    p = subprocess.run([GH, 'release', 'upload', 'v2.0', '--clobber'] + args, cwd='D:/nightingale'); assert p.returncode == 0
    subprocess.run([GH, 'release', 'edit', 'v2.0', '--notes-file', H + '/release_notes.md'], cwd='D:/nightingale', capture_output=True)
    cur = json.loads(subprocess.run([GH, 'release', 'view', 'v2.0', '--json', 'assets'], cwd='D:/nightingale', capture_output=True).stdout.decode('utf-8'))['assets']
    for a in cur:
        if a['name'] not in assets and a['name'] != 'SHA256SUMS.txt':
            subprocess.run([GH, 'release', 'delete-asset', 'v2.0', a['name'], '-y'], cwd='D:/nightingale', capture_output=True); print('删除旧附件', a['name'])
    for a in cur:
        if a['name'] in assets or a['name'] == 'SHA256SUMS.txt': print('%10d  %s  ｜ %s' % (a['size'], a['name'], a.get('label') or ''))
finally: shutil.rmtree(tmp, ignore_errors=True)
