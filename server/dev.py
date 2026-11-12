"""Loopback-only development app with isolated data and simulated Spotify."""
import argparse
import hashlib
import hmac
from pathlib import Path
import secrets

from flask import Response, session
from werkzeug.security import generate_password_hash

from app import create_app

ROOT = Path(__file__).resolve().parent


class PreviewSpotify:
    def devices(self):
        return [{'id': 'local-preview', 'name': 'Local preview', 'is_active': True}]

    def play(self, uri, preference, shuffle):
        return 'Local preview', 'Simulated playback. No music was started.'


def revision():
    # Watch source only, excluding local databases, credentials, and environment files.
    files = list(ROOT.glob('*.py')) + [ROOT / 'artwork.json', ROOT / 'seed-cards.json']
    files += list((ROOT / 'templates').glob('*.html'))
    files += list((ROOT / 'static').glob('*.css')) + list((ROOT / 'static').glob('*.js'))
    state = '\n'.join(str(path.relative_to(ROOT)) + ':' + str(path.stat().st_mtime_ns)
                      for path in sorted(files) if path.exists())
    return hashlib.sha256(state.encode()).hexdigest()


def create_dev_app(port=18787, data_dir=None):
    password_hash = generate_password_hash(secrets.token_urlsafe(32), method='pbkdf2:sha256:1000')
    app = create_app({
        'DATA_DIR': str(Path(data_dir).resolve() if data_dir else ROOT / '.dev-data'),
        'PUBLIC_URL': 'http://127.0.0.1:' + str(port),
        'PASSWORD_HASH': password_hash,
        'SESSION_COOKIE_NAME': 'fauxvinyl_dev',
        'SESSION_COOKIE_SECURE': False,
        'TEMPLATES_AUTO_RELOAD': True,
    }, spotify_client=PreviewSpotify())
    auth = hmac.new(app.secret_key.encode(), password_hash.encode(), 'sha256').hexdigest()

    @app.before_request
    def local_sign_in():
        # This launcher binds exclusively to loopback; production never imports it.
        session['auth'] = auth
        if 'csrf' not in session:
            session['csrf'] = secrets.token_urlsafe(32)

    @app.get('/__dev__/revision')
    def current_revision():
        return {'revision': revision()}

    @app.get('/__dev__/live.js')
    def live_reload():
        return Response("""'use strict';
const loaded = document.currentScript.dataset.revision;
let checking = false;
setInterval(async () => {
  if (checking || document.hidden) return;
  checking = true;
  try {
    const response = await fetch('/__dev__/revision', {cache: 'no-store'});
    if (response.ok && (await response.json()).revision !== loaded) location.reload();
  } catch { /* Retry when the Python reloader is ready. */ }
  finally { checking = false; }
}, 900);
""", mimetype='text/javascript')

    @app.get('/__dev__/dev.css')
    def dev_style():
        return Response("""nav form{display:none}""", mimetype='text/css')

    @app.after_request
    def mark_local_pages(response):
        if response.mimetype == 'text/html':
            html = response.get_data(as_text=True)
            html = html.replace('</head>', '<link rel="stylesheet" href="/__dev__/dev.css"></head>')
            html = html.replace('<title>', '<title>Local · ', 1)
            html = html.replace('</body>', '<script defer src="/__dev__/live.js" data-revision="' + revision() + '"></script></body>')
            response.set_data(html)
        return response

    return app


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=18787)
    parser.add_argument('--data-dir', type=Path, help='Optional isolated development database directory')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('Use a port between 1024 and 65535.')
    print('Local FauxVinyl: http://127.0.0.1:' + str(args.port), flush=True)
    print('Automatic sign-in, separate .dev-data/, simulated Spotify, and browser live reload.', flush=True)
    create_dev_app(args.port, args.data_dir).run(host='127.0.0.1', port=args.port, debug=False,
        use_reloader=True, threaded=True, load_dotenv=False,
        extra_files=[str(ROOT / 'artwork.json'), str(ROOT / 'seed-cards.json')])
