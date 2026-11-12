"""Small TrueNAS JSON-RPC client. Never log request arguments or credentials."""
import json
import uuid
import time
from pathlib import Path
import websocket


class TrueNAS:
    def __init__(self, host, password_file, username='bray'):
        self.ws = websocket.create_connection('ws://' + host + '/api/current', timeout=30)
        result = self.call('auth.login_ex', [{'mechanism': 'PASSWORD_PLAIN',
            'username': username, 'password': Path(password_file).read_text().strip(),
            'login_options': {'user_info': True}}])
        if result.get('response_type') != 'SUCCESS':
            self.ws.close()
            raise RuntimeError('TrueNAS login: ' + result.get('response_type', 'unknown response'))

    def call(self, method, params=None, timeout=30):
        request_id = str(uuid.uuid4())
        self.ws.settimeout(timeout)
        self.ws.send(json.dumps({'jsonrpc': '2.0', 'id': request_id,
            'method': method, 'params': params or []}))
        while True:
            message = json.loads(self.ws.recv())
            if message.get('id') != request_id:
                continue
            if 'error' in message:
                error = message['error']
                detail = error.get('data') or {}
                raise RuntimeError(method + ': ' + str(detail.get('reason') or error.get('message')))
            return message.get('result')

    def close(self):
        self.ws.close()

    def wait_job(self, result, timeout=900):
        # This TrueNAS release returns an integer job ID, even over JSON-RPC.
        if not isinstance(result, int):
            return result
        deadline = time.monotonic() + timeout
        last_progress = None
        while time.monotonic() < deadline:
            jobs = self.call('core.get_jobs', [[['id', '=', result]],
                {'select': ['state', 'error', 'result', 'progress']}])
            if not jobs:
                raise RuntimeError('TrueNAS installation job disappeared.')
            job = jobs[0]
            if job['state'] == 'SUCCESS':
                return job['result']
            if job['state'] in ('FAILED', 'ABORTED'):
                raise RuntimeError('TrueNAS job failed: ' + str(job.get('error')))
            progress = (job.get('progress') or {}).get('description')
            if progress and progress != last_progress:
                print(progress, flush=True)
                last_progress = progress
            time.sleep(2)
        raise RuntimeError('Timed out waiting for TrueNAS installation job.')
