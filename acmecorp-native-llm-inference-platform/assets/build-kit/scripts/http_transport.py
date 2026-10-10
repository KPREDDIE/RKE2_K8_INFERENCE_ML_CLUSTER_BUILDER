"""Bounded HTTP helper. Parent kills this process at the total request deadline.

Credentials travel through stdin, never command arguments or diagnostic output.
Streaming responses are read as SSE events and stop at [DONE], without waiting
for a server to close its connection. No request/response bodies are logged.
"""
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

MAX_BYTES = 2 * 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Redirect refused')


def fetch(url, headers, payload=None, deadline=60):
    """Enforce wall-clock time including DNS, TLS and slow streaming reads."""
    try:
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), '--worker'],
            input=json.dumps({'url': url, 'headers': headers, 'payload': payload}).encode(),
            capture_output=True, timeout=deadline, check=True,
        )
        return result.stdout
    except (subprocess.SubprocessError, OSError):
        raise ValueError('HTTP request failed or exceeded total deadline') from None


def read_response(response, streaming):
    """Cap response memory; SSE must terminate explicitly to count as complete."""
    if not streaming:
        data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError('Response too large')
        return data
    chunks = []
    size = 0
    while True:
        line = response.readline(MAX_BYTES - size + 1)
        if not line:
            raise ValueError('Stream ended before DONE')
        size += len(line)
        if size > MAX_BYTES:
            raise ValueError('Response too large')
        chunks.append(line)
        if line.strip() == b'data: [DONE]':
            return b''.join(chunks)


def worker():
    settings = json.load(sys.stdin)
    payload = settings['payload']
    headers = settings['headers']
    if payload is not None:
        headers['Content-Type'] = 'application/json'
    request = urllib.request.Request(settings['url'], headers=headers,
        data=None if payload is None else json.dumps(payload).encode())
    # Disable ambient proxies: a localhost tunnel must stay on this workstation.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(request, timeout=15) as response:
        data = read_response(response, bool(payload and payload.get('stream')))
    sys.stdout.buffer.write(data)


if __name__ == '__main__':
    try:
        if sys.argv[1:] != ['--worker']:
            raise ValueError('Use through smoke.py')
        worker()
    except Exception:
        sys.exit(1)  # Never print a token, URL, response body or raw exception.
