"""Credential setup must stay private and preserve an existing installation."""
import ast
from pathlib import Path
import sys

import pytest
from werkzeug.security import check_password_hash

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import configure


def inputs(tmp_path, monkeypatch, **values):
    values = {'password': 'example-shelf-password', 'client-id': 'example-id',
              'client-secret': 'example-secret', 'refresh-token': 'example-refresh', **values}
    output = tmp_path / '.env'
    args = ['configure.py', '--public-url', 'https://shelf.example', '--output', str(output)]
    for name, value in values.items():
        path = tmp_path / name
        path.write_text(value)
        args += ['--' + name + '-file', str(path)]
    monkeypatch.setattr(sys, 'argv', args)
    return output


def test_file_setup_writes_private_quoted_credentials(tmp_path, monkeypatch, capsys):
    output = inputs(tmp_path, monkeypatch)
    configure.main()
    settings = dict((key, ast.literal_eval(value)) for key, value in
                    (line.split('=', 1) for line in output.read_text().splitlines()))
    assert output.stat().st_mode & 0o777 == 0o600
    assert settings['PUBLIC_URL'] == 'https://shelf.example'
    assert settings['SPOTIFY_CLIENT_SECRET'] == 'example-secret'
    assert settings['SPOTIFY_REFRESH_TOKEN'] == 'example-refresh'
    assert check_password_hash(settings['APP_PASSWORD_HASH'], 'example-shelf-password')
    assert 'example-secret' not in capsys.readouterr().out
    with pytest.raises(SystemExit):
        configure.main()
    assert output.read_text().count('SPOTIFY_CLIENT_ID=') == 1


@pytest.mark.parametrize('values', [
    {'password': 'short'}, {'client-secret': ''},
    {'refresh-token': "example'quoted"}, {'refresh-token': 'example\nmultiline'},
])
def test_invalid_credentials_do_not_create_output(tmp_path, monkeypatch, values):
    output = inputs(tmp_path, monkeypatch, **values)
    with pytest.raises(SystemExit):
        configure.main()
    assert not output.exists()


def test_interactive_setup_and_archived_import(tmp_path, monkeypatch):
    output = tmp_path / '.env'
    answers = iter(['example-shelf-password', 'example-id', 'example-secret', 'example-refresh'])
    monkeypatch.setattr(configure.getpass, 'getpass', lambda prompt: next(answers))
    monkeypatch.setattr(sys, 'argv', ['configure.py', '--public-url', 'https://shelf.example', '--output', str(output)])
    configure.main()
    assert "SPOTIFY_CLIENT_ID='example-id'" in output.read_text()
    output.unlink()
    arduino = tmp_path / 'env.h'
    arduino.write_text('const char clientId[] = "archived-id";\n'
                       'const char clientSecret[] = "archived-secret";\n'
                       'const char SPOTIFY_REFRESH_TOKEN[] = "archived-refresh";\n')
    password = tmp_path / 'password'
    password.write_text('example-shelf-password')
    monkeypatch.setattr(sys, 'argv', ['configure.py', '--public-url', 'https://shelf.example', '--output', str(output),
                                     '--arduino-env', str(arduino), '--password-file', str(password)])
    configure.main()
    assert "SPOTIFY_CLIENT_ID='archived-id'" in output.read_text()
