"""Persistent card addresses, preferences, and rotating Spotify credentials."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS cards (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, uri TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS card_artwork (
                    card_id TEXT NOT NULL, side TEXT NOT NULL, filename TEXT NOT NULL,
                    PRIMARY KEY (card_id, side)
                );
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def cards(self, order='title'):
        ordering = {
            'title': 'title COLLATE NOCASE, id',
            'title-desc': 'title COLLATE NOCASE DESC, id',
            'newest': 'created_at DESC, rowid DESC',
            'oldest': 'created_at, rowid',
        }.get(order, 'title COLLATE NOCASE, id')
        with self.connect() as db:
            return [dict(row) for row in db.execute('SELECT * FROM cards ORDER BY ' + ordering)]

    def card(self, card_id):
        with self.connect() as db:
            row = db.execute('SELECT * FROM cards WHERE id = ?', (card_id,)).fetchone()
            return dict(row) if row else None

    def save_card(self, card_id, title, uri, artwork=None, reset_artwork=()):
        with self.connect() as db:
            db.execute('''INSERT INTO cards(id, title, uri) VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET title=excluded.title, uri=excluded.uri''', (card_id, title, uri))
            for side in reset_artwork:
                db.execute('DELETE FROM card_artwork WHERE card_id = ? AND side = ?', (card_id, side))
            for side, filename in (artwork or {}).items():
                db.execute('''INSERT INTO card_artwork(card_id,side,filename) VALUES (?,?,?)
                    ON CONFLICT(card_id,side) DO UPDATE SET filename=excluded.filename''',
                    (card_id, side, filename))

    def artwork(self, card_id):
        with self.connect() as db:
            return {row['side']: row['filename'] for row in db.execute(
                'SELECT side, filename FROM card_artwork WHERE card_id = ?', (card_id,))}

    def setting(self, key, default=None):
        with self.connect() as db:
            row = db.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
            return json.loads(row['value']) if row else default

    def set(self, key, value):
        with self.connect() as db:
            db.execute('INSERT INTO settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, json.dumps(value)))
