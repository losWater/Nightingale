"""Append verified assets and a marked note to an existing Release; never deletes assets."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import ssl
import urllib.request
import urllib.parse


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', required=True)
    p.add_argument('--tag', required=True)
    p.add_argument('--directory', type=Path, required=True)
    p.add_argument('--notes', type=Path, required=True)
    p.add_argument('--apply', action='store_true')
    args = p.parse_args()
    if args.repo != 'losWater/Nightingale':
        raise ValueError('Only the authorized Nightingale repository is supported')
    cred = subprocess.run(['git', 'credential', 'fill'], input='protocol=https\nhost=github.com\n\n',
                          text=True, capture_output=True, check=True)
    credential = dict(line.split('=',1) for line in cred.stdout.splitlines() if '=' in line)
    token = credential.get('password')
    if not token:
        raise RuntimeError('GitHub credential unavailable')
    headers = {'Authorization': 'Bearer '+token, 'Accept': 'application/vnd.github+json',
               'User-Agent': 'Nightingale-release-maintenance', 'X-GitHub-Api-Version': '2022-11-28'}
    context = ssl.create_default_context()
    # python.org macOS installs may not have their own CA bundle initialized.
    # Add the system CA bundle; never disable certificate verification.
    if Path('/etc/ssl/cert.pem').is_file():
        context.load_verify_locations('/etc/ssl/cert.pem')

    def request(url, method='GET', data=None, extra=None):
        if urllib.parse.urlparse(url).hostname not in ('api.github.com','uploads.github.com'):
            raise ValueError('Refuse credential transmission to unexpected host')
        req = urllib.request.Request(url, method=method, data=data, headers={**headers, **(extra or {})})
        with urllib.request.urlopen(req, timeout=600, context=context) as response:
            return json.load(response)

    url = f'https://api.github.com/repos/{args.repo}/releases/tags/{urllib.parse.quote(args.tag)}'
    release = request(url)
    if release.get('immutable'):
        raise ValueError('Release is immutable')
    assets = json.loads((args.directory/'assets.json').read_text())
    sums = list(args.directory.glob('SHA256SUMS-mac-*.txt'))
    if len(sums) != 1:
        raise ValueError('Expected one checksum file')
    assets.append({'name': sums[0].name, 'label': '本次 Mac Rime 三版本 SHA256 校验值',
                   'sha256': hashlib.sha256(sums[0].read_bytes()).hexdigest(), 'size': sums[0].stat().st_size})
    existing = {a['name']: a for a in release['assets']}
    for asset in assets:
        path = args.directory/asset['name']
        if path.parent != args.directory or hashlib.sha256(path.read_bytes()).hexdigest() != asset['sha256']:
            raise ValueError('Invalid local asset '+asset['name'])
        if asset['name'] in existing:
            if existing[asset['name']].get('digest') != 'sha256:'+asset['sha256']:
                raise ValueError('Conflicting existing asset; refusing overwrite '+asset['name'])
    notes = args.notes.read_text()
    marker = notes.splitlines()[0]
    if not marker.startswith('<!-- NIGHTINGALE-'):
        raise ValueError('Expected unique marked notes')
    print(json.dumps({'release': release['html_url'], 'assets': assets, 'apply': args.apply}, ensure_ascii=False), flush=True)
    if not args.apply:
        return
    backup = args.directory/'release-before.json'
    if not backup.exists():
        backup.write_text(json.dumps(release, ensure_ascii=False, indent=2)+'\n')
    for asset in assets:
        if asset['name'] in existing:
            continue
        target = release['upload_url'].split('{',1)[0]+'?'+urllib.parse.urlencode({'name':asset['name'],'label':asset['label']})
        with (args.directory/asset['name']).open('rb') as data:
            result = request(target, 'POST', data, {'Content-Type': 'application/octet-stream',
                                                   'Content-Length': str(asset['size'])})
        if result.get('digest') != 'sha256:'+asset['sha256'] or result['state'] != 'uploaded':
            raise ValueError('Remote upload checksum/state mismatch')
        print('Uploaded and verified: '+result['name'], flush=True)
    current = request(url)
    if current['body'] != release['body']:
        raise ValueError('Release notes changed concurrently; assets uploaded, notes not modified')
    if marker not in current['body']:
        request(current['url'], 'PATCH', json.dumps({'body': notes+'\n---\n\n'+current['body']}).encode(),
                {'Content-Type':'application/json'})
    after = request(url)
    assert marker in after['body']
    (args.directory/'release-after.json').write_text(json.dumps(after, ensure_ascii=False, indent=2)+'\n')
    print('Published: '+after['html_url'], flush=True)


if __name__ == '__main__':
    main()
