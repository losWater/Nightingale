"""最小 GitHub API 助手：凭据取自 git credential（与 git push 同一份），不落盘、不打印。
api(方法, url, 数据) → (状态码, json)；数据为 dict 时发 JSON，为 bytes 时原样上传（ctype 指定类型）。
"""
import json, subprocess, urllib.error, urllib.request


def _token():
    out = subprocess.run(['git', 'credential', 'fill'], input='protocol=https\nhost=github.com\n',
                         capture_output=True, text=True, check=True).stdout
    return dict(l.split('=', 1) for l in out.splitlines() if '=' in l)['password']


def api(method, url, data=None, ctype='application/json'):
    body = data if isinstance(data, (bytes, type(None))) else json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method=method, headers={
        'Authorization': 'Bearer ' + _token(), 'Accept': 'application/vnd.github+json', 'Content-Type': ctype})
    try:
        with urllib.request.urlopen(req, timeout=1800) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, json.loads(raw) if raw else {}
