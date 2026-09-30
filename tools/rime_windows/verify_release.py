"""Windows-only integration tests against the unmodified official Weasel engine."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import urllib.request
import zipfile


def machine(path):
    data = path.read_bytes()
    if data[:2] != b'MZ':
        return 0
    return struct.unpack_from('<H', data, struct.unpack_from('<I', data, 0x3c)[0] + 4)[0]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path)
    p.add_argument('--probe', type=Path, required=True)
    p.add_argument('--work', type=Path, required=True)
    args = p.parse_args()
    assert os.name == 'nt', 'Native Windows verification is required'
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    installer = work / 'weasel-0.17.4.0-installer.exe'
    url = 'https://github.com/rime/weasel/releases/download/0.17.4/' + installer.name
    urllib.request.urlretrieve(url, installer)
    extracted = work / 'weasel'
    # NSIS contains x64 and x86 files with the same installed names. Keep
    # duplicate payloads rather than overwriting the x64 engine with x86.
    subprocess.run(['7z', 'x', str(installer), '-o' + str(extracted), '-aou', '-y'], check=True)
    dlls = [p for p in extracted.rglob('rime*.dll') if machine(p) == 0x8664]
    print('Official x64 engines:', dlls, flush=True)
    assert len(dlls) == 1, dlls
    dll = dlls[0]
    defaults = list(extracted.rglob('default.yaml'))
    assert len(defaults) == 1, defaults
    env = {**os.environ, 'RIME_TEST_DLL': str(dll), 'RIME_TEST_SHARED': str(defaults[0].parent),
           'SHOW_SOURCE': '1', 'PATH': str(dll.parent) + os.pathsep + os.environ['PATH']}
    results = []
    for entry in json.loads((args.directory / 'assets.json').read_text(encoding='utf-8')):
        archive = args.directory / entry['name']
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == entry['sha256']
        stage = work / entry['name'].removesuffix('.zip')
        stage.mkdir(exist_ok=False)
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist())
            z.extractall(stage)
        manifest = json.loads((stage / 'manifest.json').read_text(encoding='utf-8'))
        for n, digest in manifest['files'].items():
            assert hashlib.sha256((stage / n).read_bytes()).hexdigest() == digest
        schema = manifest['schema']
        shutil.copy2(stage / 'default.custom.yaml.example', stage / 'default.custom.yaml')
        checks = [('ycv{space}', '尧'), ('ycvp{space}', '尧'), ('ycpp{space}', '尧'),
                  ('qnvo{space}', '翘'), ('qnp{space}', '翘'), ('qnv{space}', '悄'),
                  ('yr{space}', '远'), ('yrp{space}', '元'), ('zi{space}', '自'), ('zip{space}', '子')]
        inputs = [k for k, _ in checks]
        if schema == 'yeying25_v5':
            inputs += ['woxihryeyk', 'woxihryeyk{space}']
        if schema == 'yeying25_single':
            inputs += ['f.', 'dv.', 'ct{space}', 'fzp{space}']
        run = subprocess.run([str(args.probe.resolve()), str(stage), schema, '--deploy', *inputs],
                             env=env, capture_output=True, timeout=300)
        stdout = run.stdout.decode('utf-8', errors='replace')
        stderr = run.stderr.decode('utf-8', errors='replace')
        (work / (schema + '.stdout.txt')).write_text(stdout, encoding='utf-8')
        (work / (schema + '.stderr.txt')).write_text(stderr, encoding='utf-8')
        print(stdout, flush=True)
        print(stderr[-12000:], flush=True)
        assert run.returncode == 0, run.returncode
        for keys, char in checks:
            assert f'COMMIT\t{keys}\t{char}' in stdout, (keys, char)
        if schema == 'yeying25_v5':
            # Must see a native-model-tagged candidate: plain Rime fallback is not a pass.
            assert '我喜欢夜莺' in stdout
            assert any(l.startswith('SOURCE\twoxihryeyk\t') and l.endswith('\tV5') for l in stdout.splitlines())
            assert 'COMMIT\twoxihryeyk{space}\t我喜欢夜莺' in stdout
        if schema == 'yeying25_single':
            assert 'COMMIT\tf.\t发。' in stdout
            assert 'COMMIT\tdv.\t对。' in stdout
            assert 'COMMIT\tfzp{space}\t否' in stdout
        errors = [p for p in stage.rglob('*') if p.is_file() and '.ERROR.' in p.name and p.stat().st_size]
        assert not errors, [(str(p), p.read_text(encoding='utf-8', errors='replace')[-12000:]) for p in errors]
        results.append(dict(asset=entry, schema=schema, passed=True, keys=inputs))
    report = dict(platform='Windows x64', weasel='0.17.4', engine_sha256=hashlib.sha256(dll.read_bytes()).hexdigest(),
                  installer_url=url, installer_sha256=hashlib.sha256(installer.read_bytes()).hexdigest(),
                  scope='Official engine isolated deployment and key sequences; not manual GUI application coverage',
                  results=results)
    (args.directory / 'windows-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('ALL THREE WINDOWS PACKAGES PASSED', flush=True)


if __name__ == '__main__':
    main()
