import json, os, sys, urllib.request, urllib.error
BASE = (os.environ.get('HAL_COOLIFY_BASE') or 'https://ballista.west-alpha.ts.net/api/v1').rstrip('/')
TOK = os.environ['COOLIFY_ACCESS_TOKEN']

def call(method, path, body=None, raw=False):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
        headers={'Authorization': 'Bearer ' + TOK, 'X-Forwarded-For': '100.79.11.35',
                 'Content-Type': 'application/json', 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            text = r.read()
            return (r.status, text if raw else json.loads(text or b'{}'))
    except urllib.error.HTTPError as e:
        return (e.code, e.read(400).decode(errors='replace'))
