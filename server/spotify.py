"""Spotify transport and device selection, independent of HTTP routes."""
import threading
import time
import requests


class SpotifyError(Exception):
    pass


class Spotify:
    def __init__(self, store, client_id, client_secret, refresh_token):
        self.store = store
        self.client_id = client_id
        self.client_secret = client_secret
        self.initial_refresh_token = refresh_token
        self._token = None
        self._expires = 0
        self._lock = threading.RLock()
        self.http = requests.Session()

    def access_token(self, force=False):
        with self._lock:
            if not force and self._token and time.monotonic() < self._expires:
                return self._token
            refresh = self.store.setting('spotify_refresh_token', self.initial_refresh_token)
            if not all([self.client_id, self.client_secret, refresh]):
                raise SpotifyError('Spotify credentials are missing from the app configuration.')
            try:
                response = self.http.post('https://accounts.spotify.com/api/token',
                    auth=(self.client_id, self.client_secret),
                    data={'grant_type': 'refresh_token', 'refresh_token': refresh}, timeout=15)
            except requests.RequestException:
                raise SpotifyError('Could not reach Spotify. Try again in a moment.') from None
            if response.status_code != 200:
                if response.status_code in (400, 401):
                    raise SpotifyError('Spotify authorization needs attention. Renew the refresh token or check the client credentials.')
                raise SpotifyError('Spotify token service is unavailable. Try again shortly.')
            try:
                result = response.json()
                self._token = result['access_token']
                self._expires = time.monotonic() + max(0, int(result.get('expires_in', 3600)) - 60)
            except (ValueError, KeyError, TypeError):
                raise SpotifyError('Spotify returned an unexpected token response.') from None
            if result.get('refresh_token'):
                self.store.set('spotify_refresh_token', result['refresh_token'])
            return self._token

    def request(self, method, path, **kwargs):
        for attempt in range(2):
            token = self.access_token(force=attempt > 0)
            try:
                response = self.http.request(method, 'https://api.spotify.com/v1/' + path,
                    headers={'Authorization': 'Bearer ' + token}, timeout=15, **kwargs)
            except requests.RequestException:
                raise SpotifyError('Could not reach Spotify. Try again in a moment.') from None
            if response.status_code == 401 and attempt == 0:
                continue
            if response.status_code == 429:
                raise SpotifyError('Spotify is rate limiting requests. Wait a moment before trying again.')
            if response.status_code == 403:
                if 'Active premium subscription required for the owner of the app' in response.text:
                    raise SpotifyError('Spotify requires active Premium on the account that owns this developer app. Check that owner account’s subscription; changes can take a few hours to apply.')
                raise SpotifyError('Spotify denied playback. Check Premium membership, playback permissions, and app access.')
            if response.status_code >= 400:
                raise SpotifyError('Spotify could not complete the request. Open Spotify on the speaker or device and try again.')
            if response.status_code == 204 or not response.content:
                return {}
            try:
                return response.json()
            except ValueError:
                raise SpotifyError('Spotify returned an unexpected response.') from None
        raise SpotifyError('Spotify authorization could not be refreshed.')

    def devices(self):
        return [d for d in self.request('GET', 'me/player/devices').get('devices', [])
                if d.get('id') and not d.get('is_restricted')]

    @staticmethod
    def choose_device(devices, preference='auto'):
        if preference != 'auto':
            for device in devices:
                if device.get('name') == preference or device.get('id') == preference:
                    return device
            raise SpotifyError('Your selected device is offline. Open Spotify on it, or choose another device in Settings.')
        for device in devices:
            if device.get('is_active'):
                return device
        for name in ('Living Room TV', 'Living Room'):
            for device in devices:
                if device.get('name') == name:
                    return device
        if len(devices) == 1:
            return devices[0]
        if not devices:
            raise SpotifyError('No Spotify devices are available. Open Spotify on the device you want to use.')
        raise SpotifyError('Choose a playback device in Settings, or start Spotify on one device first.')

    def play(self, uri, preference='auto', shuffle=True):
        # Serialize playback so two scans do not interleave transfer/play/shuffle.
        with self._lock:
            device = self.choose_device(self.devices(), preference)
            params = {'device_id': device['id']}
            if not device.get('is_active'):
                self.request('PUT', 'me/player', json={'device_ids': [device['id']], 'play': False})
            body = {'uris': [uri]} if uri.startswith('spotify:track:') else {'context_uri': uri}
            self.request('PUT', 'me/player/play', params=params, json=body)
            warning = None
            try:
                self.request('PUT', 'me/player/shuffle', params={**params, 'state': str(shuffle).lower()})
            except SpotifyError:
                warning = 'Playback started, but Spotify could not update shuffle.'
            return device['name'], warning
