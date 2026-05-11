"""
BizTrack local server — serves index.html + handles SMS via Twilio.
Set your credentials in .env before starting.
Run: python3 server.py
"""
import os, json, urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from twilio.rest import Client

# ── Load .env (simple parser, no extra deps) ────────────────
def load_env(path='.env'):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

load_env(os.path.join(os.path.dirname(__file__), '.env'))

TWILIO_SID   = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_FROM  = os.environ.get('TWILIO_PHONE_NUMBER', '')

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.dirname(__file__), **kwargs)

    def log_message(self, fmt, *args):
        print(f"  {self.address_string()} — {fmt % args}")

    def do_POST(self):
        if self.path == '/api/send-sms':
            self._handle_sms()
        else:
            self.send_error(404)

    def _handle_sms(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body   = json.loads(self.rfile.read(length))
            to     = body.get('to', '').strip()
            msg    = body.get('message', '').strip()

            if not to or not msg:
                return self._json(400, {'success': False, 'error': 'Missing to or message'})

            if not TWILIO_SID or not TWILIO_TOKEN or not TWILIO_FROM:
                return self._json(503, {'success': False,
                    'error': 'Twilio credentials not configured. Add them to .env'})

            client  = Client(TWILIO_SID, TWILIO_TOKEN)
            message = client.messages.create(body=msg, from_=TWILIO_FROM, to=to)
            print(f"  SMS sent → {to}  sid={message.sid}")
            self._json(200, {'success': True, 'sid': message.sid})

        except Exception as e:
            print(f"  SMS error: {e}")
            self._json(500, {'success': False, 'error': str(e)})

    def _json(self, code, data):
        payload = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(payload))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(payload)


if __name__ == '__main__':
    port = 8080
    httpd = HTTPServer(('', port), Handler)
    print(f"\n  BizTrack server running → http://localhost:{port}")
    print(f"  SMS: {'✓ configured' if TWILIO_SID else '✗ not configured — edit .env'}\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\n  Server stopped.')
