import csv
from io import BytesIO, StringIO
from pathlib import Path
import re
import sys
from unittest.mock import Mock

import pytest
from PIL import Image
from werkzeug.security import generate_password_hash

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app, spotify_uri
from spotify import Spotify, SpotifyError
from store import Store


class FakeSpotify:
    def __init__(self):
        self.plays = []

    def devices(self):
        return [{'id': 'speaker-id', 'name': 'Living Room', 'is_active': True}]

    def play(self, uri, preference, shuffle):
        self.plays.append((uri, preference, shuffle))
        return 'Living Room', None


@pytest.fixture
def setup_app(tmp_path):
    spotify = FakeSpotify()
    config = {'TESTING': True, 'DATA_DIR': str(tmp_path), 'PUBLIC_URL': 'https://vinyl.bray.dev',
              'PASSWORD_HASH': generate_password_hash('test-password-1234', method='pbkdf2:sha256:1000')}
    app = create_app(config, spotify_client=spotify)
    return app, spotify, config


def get(client, path):
    return client.get(path, base_url='https://vinyl.bray.dev')


def csrf(client):
    with client.session_transaction(base_url='https://vinyl.bray.dev') as session:
        return session['csrf']


def post(client, path, data=None):
    return client.post(path, data={'csrf': csrf(client), **(data or {})},
                       base_url='https://vinyl.bray.dev', headers={'Origin': 'https://vinyl.bray.dev'})


def login(client, next='/'):
    get(client, '/login')
    return post(client, '/login', {'password': 'test-password-1234', 'next': next})


def test_private_card_preserves_destination_after_login(setup_app):
    app, spotify, _ = setup_app
    client = app.test_client()
    card = app.extensions['store'].cards()[0]
    response = get(client, '/c/' + card['id'])
    assert response.status_code == 302
    assert response.location.endswith('/login?next=/c/' + card['id'])
    assert spotify.plays == []
    response = login(client, '/c/' + card['id'])
    assert response.status_code == 303
    assert response.location == '/c/' + card['id']
    assert '__Host' not in response.headers['Set-Cookie']
    assert 'Secure' in response.headers['Set-Cookie']
    assert 'HttpOnly' in response.headers['Set-Cookie']
    assert 'SameSite=Lax' in response.headers['Set-Cookie']


@pytest.mark.parametrize('password, expected_status', [
    ('test-password-1234', 303), ('wrong-password', 401),
])
def test_privacy_browser_origin_does_not_hide_password_result(setup_app, password, expected_status):
    app, _, _ = setup_app
    client = app.test_client()
    get(client, '/login')
    # Firefox can send an opaque Origin with a no-referrer policy on form POST.
    response = client.post('/login', data={'csrf': csrf(client), 'password': password},
        base_url='https://vinyl.bray.dev', headers={'Origin': 'null', 'Sec-Fetch-Site': 'same-origin'})
    assert response.status_code == expected_status
    if expected_status == 401:
        assert b'That password did not match' in response.data
        assert b'id="login-error"' in response.data
        assert b'aria-describedby="login-error"' in response.data


def test_opaque_origin_still_requires_csrf(setup_app):
    app, _, _ = setup_app
    client = app.test_client()
    get(client, '/login')
    response = client.post('/login', data={'csrf': 'invalid', 'password': 'test-password-1234'},
        base_url='https://vinyl.bray.dev', headers={'Origin': 'null'})
    assert response.status_code == 400


@pytest.mark.parametrize('fetch_site', ['cross-site', 'same-site', 'none', ''])
def test_opaque_origin_without_same_origin_metadata_is_rejected(setup_app, fetch_site):
    app, _, _ = setup_app
    client = app.test_client()
    get(client, '/login')
    response = client.post('/login', data={'csrf': csrf(client), 'password': 'test-password-1234'},
        base_url='https://vinyl.bray.dev', headers={'Origin': 'null', 'Sec-Fetch-Site': fetch_site})
    assert response.status_code == 403


def test_card_edit_retains_id_and_survives_restart(setup_app):
    app, _, config = setup_app
    client = app.test_client()
    login(client)
    card = app.extensions['store'].cards()[0]
    new_uri = 'spotify:album:' + 'A' * 22
    response = post(client, '/cards/' + card['id'] + '/edit', {'title': 'Changed record', 'uri': new_uri})
    assert response.status_code == 303
    restarted = create_app(config, spotify_client=FakeSpotify())
    assert restarted.extensions['store'].card(card['id'])['title'] == 'Changed record'
    assert restarted.extensions['store'].card(card['id'])['uri'] == new_uri
    assert get(client, '/c/' + card['id']).status_code == 200


def test_get_does_not_play_and_each_post_is_consumed_once(setup_app):
    app, spotify, _ = setup_app
    client = app.test_client()
    login(client)
    card = app.extensions['store'].cards()[0]
    response = get(client, '/c/' + card['id'])
    assert spotify.plays == []
    token = re.search(rb'name="action_token" value="([^"]+)"', response.data).group(1).decode()
    response = post(client, '/c/' + card['id'] + '/play', {'action_token': token})
    assert response.status_code == 200
    assert len(spotify.plays) == 1
    assert post(client, '/c/' + card['id'] + '/play', {'action_token': token}).status_code == 409
    assert len(spotify.plays) == 1


def test_csrf_and_cross_origin_block_playback(setup_app):
    app, spotify, _ = setup_app
    client = app.test_client()
    login(client)
    card = app.extensions['store'].cards()[0]
    path = '/c/' + card['id'] + '/play'
    assert client.post(path, base_url='https://vinyl.bray.dev').status_code == 400
    assert client.post(path, data={'csrf': csrf(client)}, base_url='https://vinyl.bray.dev',
                       headers={'Origin': 'https://other.example'}).status_code == 403
    assert spotify.plays == []


def test_action_is_bound_to_logged_in_browser(setup_app):
    app, spotify, _ = setup_app
    client1, client2 = app.test_client(), app.test_client()
    login(client1)
    login(client2)
    card = app.extensions['store'].cards()[0]
    response = get(client1, '/c/' + card['id'])
    token = re.search(rb'name="action_token" value="([^"]+)"', response.data).group(1).decode()
    assert post(client2, '/c/' + card['id'] + '/play', {'action_token': token}).status_code == 400
    assert not spotify.plays


def test_signin_cannot_redirect_to_another_site(setup_app):
    app, _, _ = setup_app
    client = app.test_client()
    assert login(client, '//evil.example').location == '/'


def test_settings_export_and_escaped_titles(setup_app):
    app, _, _ = setup_app
    client = app.test_client()
    login(client)
    assert get(client, '/settings').status_code == 200
    response = post(client, '/cards', {'title': '<script>alert(1)</script>', 'uri': 'https://open.spotify.com/album/' + 'A' * 22 + '?si=tracking'})
    assert response.status_code == 303
    assert b'<script>alert(1)</script>' not in get(client, '/').data
    assert b'&lt;script&gt;' in get(client, '/').data
    exported = get(client, '/cards.csv')
    rows = list(csv.DictReader(StringIO(exported.data.decode())))
    assert rows
    assert all(row['nfc_url'].startswith('https://vinyl.bray.dev/c/') for row in rows)


def test_device_choice_does_not_play_on_arbitrary_device():
    devices = [{'id': 'a', 'name': 'Laptop'}, {'id': 'b', 'name': 'Kitchen'}]
    with pytest.raises(SpotifyError):
        Spotify.choose_device(devices)
    assert Spotify.choose_device(devices, 'Kitchen')['id'] == 'b'
    devices[0]['is_active'] = True
    assert Spotify.choose_device(devices)['id'] == 'a'


def test_rotated_refresh_token_is_persisted(tmp_path):
    store = Store(tmp_path / 'db.sqlite3')
    spotify = Spotify(store, 'id', 'secret', 'initial')
    response = Mock(status_code=200)
    response.json.return_value = {'access_token': 'access', 'expires_in': 3600, 'refresh_token': 'rotated'}
    spotify.http = Mock()
    spotify.http.post.return_value = response
    assert spotify.access_token() == 'access'
    assert store.setting('spotify_refresh_token') == 'rotated'
    spotify.access_token(force=True)
    assert spotify.http.post.call_args.kwargs['data']['refresh_token'] == 'rotated'


def test_api_401_retries_once_with_new_token(tmp_path):
    spotify = Spotify(Store(tmp_path / 'db.sqlite3'), 'id', 'secret', 'refresh')
    spotify.access_token = Mock(side_effect=['old', 'new'])
    denied = Mock(status_code=401, content=b'error')
    success = Mock(status_code=200, content=b'{}')
    success.json.return_value = {'devices': []}
    spotify.http = Mock()
    spotify.http.request.side_effect = [denied, success]
    assert spotify.devices() == []
    assert spotify.access_token.call_args_list[-1].kwargs['force'] is True


def test_spotify_links_are_validated_and_tracking_removed():
    assert spotify_uri('https://open.spotify.com/album/' + 'A' * 22 + '?si=tracking') == 'spotify:album:' + 'A' * 22
    with pytest.raises(ValueError):
        spotify_uri('https://evil.example/album/' + 'A' * 22)
    with pytest.raises(ValueError):
        spotify_uri('spotify:album:not-an-id')


def test_spotify_app_owner_premium_error_is_actionable(tmp_path):
    spotify = Spotify(Store(tmp_path / 'db.sqlite3'), 'id', 'secret', 'refresh')
    spotify.access_token = Mock(return_value='access')
    spotify.http = Mock()
    spotify.http.request.return_value = Mock(status_code=403,
        text='Active premium subscription required for the owner of the app.')
    with pytest.raises(SpotifyError, match='account that owns this developer app'):
        spotify.devices()


def cover(color='red', size=(1800, 900), format='PNG'):
    output = BytesIO()
    Image.new('RGB', size, color).save(output, format)
    output.seek(0)
    return output


def test_front_and_back_uploads_persist_and_are_private(setup_app):
    app, spotify, config = setup_app
    client = app.test_client()
    login(client)
    card = app.extensions['store'].cards()[0]
    response = post(client, '/cards/' + card['id'] + '/edit', {
        'title': card['title'], 'uri': card['uri'],
        'front': (cover('red'), '../../untrusted.svg'),
        'back': (cover('blue'), 'back.png'),
    })
    assert response.status_code == 303
    saved = app.extensions['store'].artwork(card['id'])
    assert set(saved) == {'front', 'back'} and saved['front'] != saved['back']
    front_url = '/artwork/' + saved['front']
    assert front_url.encode() in get(client, '/').data
    response = get(client, front_url)
    assert response.status_code == 200 and response.mimetype == 'image/webp'
    assert 'private' in response.headers['Cache-Control']
    with Image.open(BytesIO(response.data)) as image:
        assert image.size == (1280, 640)
    assert get(app.test_client(), front_url).status_code == 302
    assert get(client, '/artwork/session.key').status_code == 404
    restarted = create_app(config, spotify_client=FakeSpotify())
    assert restarted.extensions['store'].artwork(card['id']) == saved
    assert get(client, '/c/' + card['id']).status_code == 200
    assert not spotify.plays


def test_replacing_one_side_keeps_other_and_reset_restores_bundled_cover(setup_app):
    app, _, _ = setup_app
    store = app.extensions['store']
    client = app.test_client()
    login(client)
    card = store.cards()[0]
    path = '/cards/' + card['id'] + '/edit'
    data = {'title': card['title'], 'uri': card['uri']}
    assert post(client, path, {**data, 'front': (cover('red'), 'f.png'),
        'back': (cover('blue'), 'b.png')}).status_code == 303
    original = store.artwork(card['id'])
    assert post(client, path, {**data, 'front': (cover('green'), 'new.png')}).status_code == 303
    replaced = store.artwork(card['id'])
    assert replaced['back'] == original['back'] and replaced['front'] != original['front']
    assert post(client, path, {**data, 'reset_front': '1'}).status_code == 303
    assert store.artwork(card['id']) == {'back': original['back']}
    assert b'data-front="/static/covers/' in get(client, '/').data
    # Editing text alone never clears the uploaded back or changes its tag.
    assert post(client, path, {**data, 'title': 'Renamed'}).status_code == 303
    assert store.artwork(card['id']) == {'back': original['back']}


@pytest.mark.parametrize('bad_file, message', [
    (lambda: BytesIO(b'<svg xmlns="http://www.w3.org/2000/svg"/>'), b'valid JPEG'),
    (lambda: BytesIO(b'x' * (8 * 1024 * 1024 + 1)), b'8 MB'),
    (lambda: cover(size=(4000, 3100)), b'12 megapixels'),
])
def test_bad_cover_rejects_whole_edit_without_changing_record(setup_app, bad_file, message):
    app, _, config = setup_app
    store = app.extensions['store']
    client = app.test_client()
    login(client)
    card = store.cards()[0]
    response = post(client, '/cards/' + card['id'] + '/edit', {
        'title': 'Must not save', 'uri': card['uri'],
        'front': (cover(), 'valid.png'), 'back': (bad_file(), 'bad.png')})
    assert response.status_code == 400 and message in response.data
    assert store.card(card['id']) == card and store.artwork(card['id']) == {}
    assert list((Path(config['DATA_DIR']) / 'artwork').iterdir()) == []


def test_artwork_upload_requires_csrf_and_rejects_oversized_request(setup_app):
    app, _, _ = setup_app
    client = app.test_client()
    login(client)
    card = app.extensions['store'].cards()[0]
    path = '/cards/' + card['id'] + '/edit'
    response = client.post(path, data={'front': (cover(), 'front.png')}, base_url='https://vinyl.bray.dev')
    assert response.status_code == 400
    assert post(client, path, {'front': (BytesIO(b'x' * (18 * 1024 * 1024)), 'huge.png')}).status_code == 413
    assert app.extensions['store'].artwork(card['id']) == {}


def test_sort_order_remembered_and_date_order_survives_edits(setup_app):
    app, _, _ = setup_app
    store = app.extensions['store']
    client = app.test_client()
    login(client)
    uri = 'spotify:album:' + 'A' * 22
    store.save_card('new-1', 'a custom record', uri)
    store.save_card('new-2', 'Z custom record', uri)

    def ids(response):
        return re.findall(rb'data-record-id="([^"]+)"', response.data)

    assert ids(get(client, '/?sort=newest'))[:2] == [b'new-2', b'new-1']
    assert ids(get(client, '/'))[:2] == [b'new-2', b'new-1']
    assert b'<option value="newest" selected>' in get(client, '/').data
    first_added = store.cards('oldest')[0]['id']
    store.save_card(first_added, 'Edited old record', uri)
    assert ids(get(client, '/?sort=oldest'))[0].decode() == first_added
    assert ids(get(client, '/?sort=title-desc')) == [c['id'].encode() for c in store.cards('title-desc')]
    assert ids(get(client, '/?sort=invalid')) == [c['id'].encode() for c in store.cards('title')]
    assert b'value="custom"' in get(client, '/?sort=title&q=custom').data
