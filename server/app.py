import csv
from datetime import timedelta
from functools import wraps
import hmac
import io
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from urllib.parse import urlsplit

from flask import Flask, Response, abort, flash, redirect, render_template, request, send_from_directory, session, url_for
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash

from spotify import Spotify, SpotifyError
from store import Store
from uploads import prepare_cover, save_cover


def spotify_uri(value):
    value = value.strip()
    if value.startswith('https://open.spotify.com/'):
        parts = urlsplit(value)
        match = re.fullmatch(r'/(?:intl-[a-z]{2}/)?(album|playlist|track)/([A-Za-z0-9]{22})/?', parts.path)
        if parts.hostname != 'open.spotify.com' or not match:
            raise ValueError('Use a Spotify album, playlist, or track link.')
        return 'spotify:' + ':'.join(match.groups())
    if re.fullmatch(r'spotify:(album|playlist|track):[A-Za-z0-9]{22}', value):
        return value
    raise ValueError('Use a Spotify album, playlist, or track link.')


def setting_env(name, default=''):
    path = os.environ.get(name + '_FILE')
    return Path(path).read_text().strip() if path else os.environ.get(name, default)


def create_app(config=None, spotify_client=None):
    # Minimal Linux images may not have a system MIME registry for WebP.
    mimetypes.add_type('image/webp', '.webp')
    app = Flask(__name__)
    data_dir = Path(os.environ.get('DATA_DIR', 'data'))
    app.config.update(
        DATA_DIR=str(data_dir), PUBLIC_URL=os.environ.get('PUBLIC_URL', 'https://vinyl.bray.dev'),
        PASSWORD_HASH=setting_env('APP_PASSWORD_HASH'),
        SESSION_COOKIE_NAME='fauxvinyl_session', SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(days=90),
        MAX_CONTENT_LENGTH=17 * 1024 * 1024, MAX_FORM_MEMORY_SIZE=500 * 1024, MAX_FORM_PARTS=30,
    )
    if config:
        app.config.update(config)
    public = urlsplit(app.config['PUBLIC_URL'])
    if public.scheme not in ('http', 'https') or not public.netloc or public.path not in ('', '/'):
        raise ValueError('PUBLIC_URL must be an origin such as https://vinyl.bray.dev')
    app.config['PUBLIC_URL'] = app.config['PUBLIC_URL'].rstrip('/')
    if not app.config['PASSWORD_HASH']:
        raise ValueError('APP_PASSWORD_HASH is required. Run configure.py before starting the app.')
    app.config['TRUSTED_HOSTS'] = [public.hostname]
    directory = Path(app.config['DATA_DIR'])
    directory.mkdir(parents=True, exist_ok=True)
    upload_directory = directory / 'artwork'
    upload_directory.mkdir(exist_ok=True)
    secret_path = directory / 'session.key'
    try:
        fd = os.open(secret_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as out:
            out.write(secrets.token_hex(32))
    except FileExistsError:
        pass
    app.secret_key = secret_path.read_text().strip()
    store = Store(directory / 'fauxvinyl.sqlite3')
    with store.connect() as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS used_actions (nonce TEXT PRIMARY KEY, expires INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS login_failures (created REAL NOT NULL);
        ''')
    # Seed once; future restarts must never undo edits to a card's content.
    if not store.setting('seed_imported', False):
        for card in json.loads(Path(__file__).with_name('seed-cards.json').read_text()):
            if not store.card(card['id']):
                store.save_card(card['id'], card['title'], spotify_uri(card['uri']))
        store.set('seed_imported', True)
    client = spotify_client or Spotify(store, setting_env('SPOTIFY_CLIENT_ID'),
        setting_env('SPOTIFY_CLIENT_SECRET'), setting_env('SPOTIFY_REFRESH_TOKEN'))
    app.extensions.update(store=store, spotify=client)
    artwork_path = Path(__file__).with_name('artwork.json')
    artwork = json.loads(artwork_path.read_text()) if artwork_path.exists() else {}
    signer = URLSafeTimedSerializer(app.secret_key, salt='fauxvinyl-play')
    # A password change invalidates all remembered logins.
    auth_version = hmac.new(app.secret_key.encode(), app.config['PASSWORD_HASH'].encode(), 'sha256').hexdigest()

    def authenticated():
        return secrets.compare_digest(str(session.get('auth', '')), auth_version)

    def csrf():
        if 'csrf' not in session:
            session['csrf'] = secrets.token_urlsafe(32)
        return session['csrf']

    @app.context_processor
    def template_context():
        return {'csrf': csrf, 'authenticated': authenticated(), 'public_url': app.config['PUBLIC_URL']}

    @app.before_request
    def protect_posts():
        if request.method == 'POST':
            expected = session.get('csrf', '')
            supplied = request.form.get('csrf', '')
            if not expected or not secrets.compare_digest(expected, supplied):
                abort(400, 'This page expired. Reload it and try again.')
            origin = request.headers.get('Origin')
            # Firefox privacy/referrer policies can make a same-origin form's
            # Origin opaque. Require independent same-origin browser metadata
            # for that case; the session-bound CSRF token is always mandatory.
            same_origin_opaque = origin == 'null' and request.headers.get('Sec-Fetch-Site') == 'same-origin'
            if origin and origin != app.config['PUBLIC_URL'] and not same_origin_opaque:
                abort(403, 'The request came from a different site.')

    @app.after_request
    def secure_response(response):
        response.headers['Cache-Control'] = 'no-store'
        if request.endpoint == 'static' and request.view_args.get('filename', '').startswith('covers/'):
            # Generated cover filenames contain a content hash, so they can be
            # cached without affecting private shelf pages or updated artwork.
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        if request.endpoint == 'uploaded_artwork' and response.status_code == 200:
            response.headers['Cache-Control'] = 'private, max-age=31536000, immutable'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        return response

    def private(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not authenticated():
                return redirect(url_for('login', next=request.path))
            return view(*args, **kwargs)
        return wrapped

    def next_path(value):
        if value == '/' or re.fullmatch(r'/(?:c/[a-z0-9-]+|settings)', value or ''):
            return value
        return '/'

    @app.get('/healthz')
    def health():
        return {'status': 'ok'}

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        destination = next_path(request.values.get('next'))
        if request.method == 'POST':
            now = time.time()
            with store.connect() as db:
                db.execute('DELETE FROM login_failures WHERE created < ?', (now - 900,))
                attempts = db.execute('SELECT COUNT(*) FROM login_failures').fetchone()[0]
                if attempts >= 30:
                    abort(429, 'Too many sign-in attempts. Try again in 15 minutes.')
                if not check_password_hash(app.config['PASSWORD_HASH'], request.form.get('password', '')):
                    db.execute('INSERT INTO login_failures VALUES (?)', (now,))
                    return render_template('login.html', next=destination,
                        login_error='That password did not match. Try again.'), 401
            session.clear()
            session['auth'] = auth_version
            session['csrf'] = secrets.token_urlsafe(32)
            session.permanent = True
            return redirect(destination, code=303)
        if authenticated():
            return redirect(destination)
        return render_template('login.html', next=destination)

    @app.post('/logout')
    def logout():
        session.clear()
        return redirect(url_for('login'), code=303)

    @app.get('/')
    @private
    def index():
        order = request.args.get('sort', session.get('shelf_sort', 'title'))
        if order not in ('title', 'title-desc', 'newest', 'oldest'):
            order = 'title'
        session['shelf_sort'] = order
        return render_template('index.html', cards=[{**card, 'artwork': card_artwork(card)}
            for card in store.cards(order)], sort_order=order)

    def card_artwork(card):
        covers = {side: url_for('static', filename=filename)
            for side, filename in artwork.get(card['uri'], {}).items() if side in ('front', 'back')}
        covers.update({side: url_for('uploaded_artwork', filename=filename)
            for side, filename in store.artwork(card['id']).items()})
        return covers

    @app.get('/artwork/<filename>')
    @private
    def uploaded_artwork(filename):
        if not re.fullmatch(r'[a-f0-9]{64}\.webp', filename):
            abort(404)
        return send_from_directory(upload_directory, filename, mimetype='image/webp')

    @app.post('/cards')
    @private
    def add_card():
        title = request.form.get('title', '').strip()
        if not title or len(title) > 140:
            abort(400, 'Enter a card title of 1–140 characters.')
        try:
            uri = spotify_uri(request.form.get('uri', ''))
        except ValueError as error:
            flash(str(error), 'error')
            return redirect(url_for('index'), code=303)
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:45] or 'card'
        card_id = slug + '-' + secrets.token_hex(3)
        store.save_card(card_id, title, uri)
        flash('Card added. Copy its permanent URL to your NFC tag.', 'success')
        return redirect(url_for('edit_card', card_id=card_id), code=303)

    def find_card(card_id):
        card = store.card(card_id)
        if not card:
            abort(404, 'This card is not on your shelf.')
        return card

    @app.route('/cards/<card_id>/edit', methods=['GET', 'POST'])
    @private
    def edit_card(card_id):
        card = find_card(card_id)
        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            if not title or len(title) > 140:
                abort(400, 'Enter a card title of 1–140 characters.')
            try:
                uri = spotify_uri(request.form.get('uri', ''))
            except ValueError as error:
                flash(str(error), 'error')
                return redirect(url_for('edit_card', card_id=card_id), code=303)
            try:
                prepared = {side: prepare_cover(upload) for side in ('front', 'back')
                    if not request.form.get('reset_' + side)
                    and (upload := request.files.get(side)) and upload.filename}
            except ValueError as error:
                # Validate both sides before changing the record or storing files.
                return render_template('edit.html', card={**card, 'title': title, 'uri': uri},
                    artwork=card_artwork(card), custom_artwork=store.artwork(card_id),
                    artwork_error=str(error)), 400
            replacements = {side: save_cover(upload_directory, content) for side, content in prepared.items()}
            resets = [side for side in ('front', 'back') if request.form.get('reset_' + side)]
            store.save_card(card_id, title, uri, replacements, resets)
            flash('Saved. Your NFC URL stays the same.', 'success')
            return redirect(url_for('edit_card', card_id=card_id), code=303)
        return render_template('edit.html', card=card, artwork=card_artwork(card),
            custom_artwork=store.artwork(card_id))

    @app.get('/c/<card_id>')
    @private
    def card_page(card_id):
        card = find_card(card_id)
        token = signer.dumps({'card': card_id, 'session': csrf(), 'nonce': secrets.token_urlsafe(24)})
        return render_template('play.html', card=card, action_token=token)

    @app.post('/c/<card_id>/play')
    @private
    def play(card_id):
        card = find_card(card_id)
        try:
            action = signer.loads(request.form.get('action_token', ''), max_age=120)
            if action.get('card') != card_id or not secrets.compare_digest(action.get('session', ''), csrf()):
                abort(400, 'This play request expired. Open the card again.')
        except (BadSignature, SignatureExpired):
            abort(400, 'This play request expired. Open the card again.')
        with store.connect() as db:
            db.execute('DELETE FROM used_actions WHERE expires < ?', (int(time.time()),))
            try:
                db.execute('INSERT INTO used_actions VALUES (?,?)', (action['nonce'], int(time.time()) + 180))
            except sqlite3.IntegrityError:
                abort(409, 'This tap was already processed. Open the card again to replay it.')
        try:
            device, warning = client.play(card['uri'], store.setting('device', 'auto'), store.setting('shuffle', True))
        except SpotifyError as error:
            return render_template('result.html', card=card, error=str(error)), 503
        return render_template('result.html', card=card, device=device, warning=warning)

    @app.route('/settings', methods=['GET', 'POST'])
    @private
    def settings():
        if request.method == 'POST':
            device = request.form.get('device', 'auto').strip()
            if not device or len(device) > 200:
                abort(400, 'Choose a valid device.')
            store.set('device', device)
            store.set('shuffle', request.form.get('shuffle') == 'on')
            flash('Playback settings saved.', 'success')
            return redirect(url_for('settings'), code=303)
        devices, error = [], None
        try:
            devices = client.devices()
        except SpotifyError as failure:
            error = str(failure)
        return render_template('settings.html', devices=devices, spotify_error=error,
            preference=store.setting('device', 'auto'), shuffle=store.setting('shuffle', True))

    @app.get('/cards.csv')
    @private
    def export_cards():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['card_id', 'title', 'spotify_uri', 'nfc_url'])
        for card in store.cards():
            # Neutralize spreadsheet formula interpretation of user-provided titles.
            title = card['title']
            if title.startswith(('=', '+', '-', '@', '\t', '\r')):
                title = "'" + title
            writer.writerow([card['id'], title, card['uri'], app.config['PUBLIC_URL'] + '/c/' + card['id']])
        return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=fauxvinyl-cards.csv'})

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(409)
    @app.errorhandler(413)
    @app.errorhandler(429)
    def friendly_error(error):
        if error.code == 413:
            return render_template('error.html', message='Upload up to two covers, 8 MB each. Go back and choose smaller files.'), 413
        return render_template('error.html', message=error.description), error.code

    return app
