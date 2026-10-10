"""Regression tests for operator mistakes and the three review findings."""
import copy
import io
import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from test_kit import site_fixture, inventory_fixture, HASH, ROOT
import render
import prepare
import http_transport
import metrics_proxy


class OperatorTests(unittest.TestCase):
    def inputs(self):
        elemental=json.loads((ROOT/'config/elemental.json').read_text())
        elemental.update(seed_image='example.invalid/seed@sha256:'+HASH,
                         compatibility_evidence='test',ssh_public_key='ssh-ed25519 TEST')
        for pool in elemental['pools']:pool['install_device']='/dev/disk/by-id/test-'+pool['name']
        return {'site':site_fixture(),'elemental':elemental,'model-files':inventory_fixture()}

    def test_all_missing_inputs_reported(self):
        errors=prepare.check_inputs(prepare.load_inputs(ROOT/'config'))
        self.assertTrue(any('site.runtime_image' in e for e in errors))
        self.assertTrue(any('elemental.seed_image' in e for e in errors))
        self.assertTrue(any('model-files.files' in e for e in errors))

    def test_minor_mismatch_blocks_bundle(self):
        data=self.inputs();data['site']['pod_security_version']='v1.30'
        self.assertTrue(prepare.check_inputs(data))

    def test_bundle_preserves_previous_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);config=root/'config';config.mkdir()
            for name,value in self.inputs().items():(config/(name+'.json')).write_text(json.dumps(value))
            output=root/'bundle'
            prepare.prepare(config,output)
            original=(output/'workload.json').read_bytes()
            with self.assertRaises(FileExistsError):prepare.prepare(config,output)
            self.assertEqual((output/'workload.json').read_bytes(),original)
            self.assertTrue((output/'CHECKSUMS.txt').exists())

    def test_monitoring_cannot_connect_to_inference_port(self):
        items=render.workload(site_fixture(),inventory_fixture())
        allowed=[p['port'] for item in items if item['kind']=='NetworkPolicy'
                 for rule in item['spec'].get('ingress',[]) for p in rule.get('ports',[])]
        self.assertEqual(allowed,[30001])
        pod=next(i for i in items if i['kind']=='Deployment')['spec']['template']['spec']
        proxy=next(c for c in pod['containers'] if c['name']=='metrics-proxy')
        self.assertNotIn('nvidia.com/gpu',proxy['resources']['limits'])

    def test_proxy_only_allows_exact_metrics_path(self):
        # Invoke the real handler without binding a network socket.
        for path in ('/v1/chat/completions','/metrics?url=http://other','/metrics/','http://other/metrics'):
            handler=object.__new__(metrics_proxy.Handler);handler.path=path
            with patch.object(handler,'send_error') as deny,patch('urllib.request.build_opener') as upstream:
                handler.do_GET();deny.assert_called_once_with(404);upstream.assert_not_called()

    def test_stream_stops_at_done_and_rejects_truncated_stream(self):
        self.assertEqual(http_transport.read_response(io.BytesIO(b'data: [DONE]\nignored'),True),b'data: [DONE]\n')
        with self.assertRaises(ValueError):http_transport.read_response(io.BytesIO(b'data: {}\n'),True)
        with patch.object(http_transport,'MAX_BYTES',4):
            with self.assertRaises(ValueError):http_transport.read_response(io.BytesIO(b'12345'),False)

    def test_trickling_stream_cannot_outlive_deadline(self):
        received=threading.Event()
        class SlowHandler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                received.set()
                self.send_response(200);self.end_headers()
                try:
                    for _ in range(40):
                        self.wfile.write(b': keepalive\n');self.wfile.flush();time.sleep(.1)
                except OSError:pass
        server=ThreadingHTTPServer(('127.0.0.1',0),SlowHandler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            started=time.monotonic()
            with self.assertRaisesRegex(ValueError,'deadline'):
                http_transport.fetch('http://127.0.0.1:'+str(server.server_port),{}, {'stream':True}, .6)
            self.assertTrue(received.is_set(), 'Request must reach the server before timing out')
            self.assertGreaterEqual(time.monotonic()-started,.5)
            self.assertLess(time.monotonic()-started,3)
        finally:
            server.shutdown();server.server_close();thread.join()

    def test_real_http_worker_reads_json_and_stream(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                self.send_response(200);self.end_headers();self.wfile.write(b'{"ok":true}')
            def do_POST(self):
                self.send_response(200);self.end_headers();self.wfile.write(b'data: [DONE]\n\n')
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            url='http://127.0.0.1:'+str(server.server_port)
            self.assertEqual(json.loads(http_transport.fetch(url,{},deadline=5)),{'ok':True})
            self.assertIn(b'[DONE]',http_transport.fetch(url,{}, {'stream':True},5))
        finally:
            server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main()
