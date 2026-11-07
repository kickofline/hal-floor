"""HAL floor: a public, no-auth page that lists the team's HAL boxes and lets anyone claim one.

State comes from the workbench (POST /api/state, X-Floor-Key). Claims are made in the browser and
are advisory: the page is the handshake, the workbench polls GET /api/claims and honours them.
"""
from __future__ import annotations
import json
import os
from http import HTTPStatus
import http.server
import secrets
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

DATA = Path(os.environ.get('FLOOR_DATA', '/data'))
STATE = DATA / 'state.json'
CLAIMS = DATA / 'claims.json'
PORT = int(os.environ.get('PORT', '8000'))
KEY = os.environ.get('HAL_FLOOR_KEY', '')
CLAIM_MIN, CLAIM_MAX, CLAIM_DEFAULT = 10, 180, 45
WRITE_WINDOW, WRITE_LIMIT = 300.0, 20.0
LOCK = threading.Lock()
HITS: dict[str, list[float]] = {}
WEB = Path(__file__).with_name('web') / 'index.html'


def load(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return fallback


def save(path: Path, value) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=1), encoding='utf-8')
    os.replace(tmp, path)


def claims() -> dict:
    now = time.time()
    data = {h: c for h, c in (load(CLAIMS, {}) or {}).items() if float(c.get('expires') or 0) > now}
    return data


def state() -> dict:
    raw = load(STATE, {}) or {}
    cl = claims()
    boxes = []
    for box in raw.get('boxes', []):
        item = dict(box)
        item['claim'] = cl.get(box.get('host', ''))
        boxes.append(item)
    waiting = raw.get('waiting', [])
    return {'boxes': boxes, 'waiting': waiting, 'slots': raw.get('slots') or {},
            'updated': raw.get('updated'), 'claims': list(cl.values())}


def limited(ip: str) -> bool:
    now = time.time()
    with LOCK:
        hits = [t for t in HITS.get(ip, []) if now - t < WRITE_WINDOW]
        if len(hits) >= WRITE_LIMIT:
            HITS[ip] = hits
            return True
        hits.append(now)
        HITS[ip] = hits
    return False


def clean(text, limit: int) -> str:
    text = ' '.join(str(text or '').split())
    return text[:limit]


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = 'HalFloor'

    def log_message(self, *args):
        pass

    def _json(self, payload, status=HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _text(self, body: bytes, ctype: str, status=HTTPStatus.OK) -> None:
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        try:
            size = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            return {}
        if size <= 0 or size > 64 * 1024:
            return {}
        try:
            data = json.loads(self.rfile.read(size) or b'{}')
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path in ('/', '/index.html'):
            with open(WEB, 'rb') as fh:
                self._text(fh.read(), 'text/html; charset=utf-8')
        elif path == '/healthz':
            self._text(b'ok', 'text/plain; charset=utf-8')
        elif path == '/api/floor':
            self._json(state())
        elif path == '/api/claims':
            self._json({'claims': claims(), 'now': time.time()})
        else:
            self._json({'error': 'not found'}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        ip = (self.headers.get('X-Forwarded-For') or self.client_address[0]).split(',')[0].strip()
        if path == '/api/state':
            if not KEY or secrets.compare_digest(self.headers.get('X-Floor-Key', ''), KEY):
                pass
            else:
                self._json({'error': 'bad key'}, HTTPStatus.FORBIDDEN)
                return
            body = self._body()
            boxes = body.get('boxes')
            if not isinstance(boxes, list) or len(boxes) > 200:
                self._json({'error': 'bad boxes'}, HTTPStatus.BAD_REQUEST)
                return
            save(STATE, {'boxes': boxes, 'waiting': body.get('waiting') or [],
                         'slots': body.get('slots') or {}, 'updated': time.time()})
            self._json({'ok': True, 'boxes': len(boxes)})
            return
        if path in ('/api/claim', '/api/claims/clear'):
            if limited(ip):
                self._json({'error': 'too many writes, wait a few minutes'}, HTTPStatus.TOO_MANY_REQUESTS)
                return
            body = self._body()
            host = clean(body.get('host'), 120).lower()
            known = {b.get('host') for b in (load(STATE, {}) or {}).get('boxes', [])}
            if not host or (known and host not in known):
                self._json({'error': 'unknown box'}, HTTPStatus.BAD_REQUEST)
                return
            cl = claims()
            if path == '/api/claims/clear':
                cl.pop(host, None)
                save(CLAIMS, cl)
                self._json({'ok': True, 'cleared': host})
                return
            try:
                minutes = int(body.get('minutes') or CLAIM_DEFAULT)
            except (TypeError, ValueError):
                minutes = CLAIM_DEFAULT
            minutes = max(CLAIM_MIN, min(CLAIM_MAX, minutes))
            now = time.time()
            cl[host] = {'host': host, 'owner': clean(body.get('owner'), 32) or 'someone',
                        'note': clean(body.get('note'), 160), 'since': now, 'expires': now + minutes * 60}
            save(CLAIMS, cl)
            self._json({'ok': True, 'claim': cl[host]})
            return
        self._json({'error': 'not found'}, HTTPStatus.NOT_FOUND)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    http.server.ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()


if __name__ == '__main__':
    main()
