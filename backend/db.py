import os
import sqlite3
from datetime import datetime

def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


PRIMARY_DB_DOWN = False
LAST_ERROR = None
ACTIVE_STORE = "primary"


def get_db_path(config_path=None):
    if config_path:
        return config_path
    return os.path.join(os.path.dirname(__file__), "reservations.db")


def init_db(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                user_email TEXT NOT NULL,
                event_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_email, event_name)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reservations_backup (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                user_email TEXT NOT NULL,
                event_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_email, event_name)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = _dict_factory
    return conn


def set_primary_down(value):
    global PRIMARY_DB_DOWN
    PRIMARY_DB_DOWN = value


def get_status():
    return {
        "chaos_enabled": PRIMARY_DB_DOWN,
        "active_store": ACTIVE_STORE,
        "last_error": LAST_ERROR,
    }


def _set_error(message):
    global LAST_ERROR
    LAST_ERROR = message


def _set_active(store):
    global ACTIVE_STORE
    ACTIVE_STORE = store


def _primary_guard():
    if PRIMARY_DB_DOWN:
        raise RuntimeError("Primary database is down (chaos monkey enabled)")


def create_reservation(db_path, user_name, user_email, event_name):
    created_at = datetime.utcnow().isoformat()
    primary_id = None
    backup_id = None

    try:
        _primary_guard()
        with _connect(db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO reservations (user_name, user_email, event_name, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_name, user_email, event_name, created_at),
            )
            primary_id = cursor.lastrowid
        _set_active("primary")
    except sqlite3.IntegrityError as exc:
        _set_error(str(exc))
        _set_active("primary")
        raise
    except Exception as exc:
        _set_error(str(exc))
        _set_active("backup")

    try:
        with _connect(db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO reservations_backup (user_name, user_email, event_name, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_name, user_email, event_name, created_at),
            )
            backup_id = cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        _set_error(str(exc))
        raise
    except Exception as exc:
        _set_error(str(exc))
        if primary_id is None:
            raise

    reservation_id = primary_id if primary_id is not None else backup_id
    return {
        "id": reservation_id,
        "user_name": user_name,
        "user_email": user_email,
        "event_name": event_name,
        "created_at": created_at,
        "stored_in": "primary" if primary_id is not None else "backup",
    }


def list_reservations(db_path):
    try:
        _primary_guard()
        with _connect(db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, user_name, user_email, event_name, created_at
                FROM reservations
                ORDER BY id DESC
                """
            ).fetchall()
        _set_active("primary")
        return rows
    except Exception as exc:
        _set_error(str(exc))
        with _connect(db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, user_name, user_email, event_name, created_at
                FROM reservations_backup
                ORDER BY id DESC
                """
            ).fetchall()
        _set_active("backup")
        return rows


def delete_reservation(db_path, reservation_id):
    deleted = False
    try:
        _primary_guard()
        with _connect(db_path) as conn:
            result = conn.execute(
                "DELETE FROM reservations WHERE id = ?",
                (reservation_id,),
            )
            deleted = result.rowcount > 0
        _set_active("primary")
    except Exception as exc:
        _set_error(str(exc))
        _set_active("backup")

    try:
        with _connect(db_path) as conn:
            conn.execute("DELETE FROM reservations_backup WHERE id = ?", (reservation_id,))
    except Exception as exc:
        _set_error(str(exc))
        if not deleted:
            raise

    return deleted


def get_backup_rows(db_path):
    with _connect(db_path) as conn:
        return conn.execute(
            """
            SELECT id, user_name, user_email, event_name, created_at
            FROM reservations_backup
            ORDER BY id DESC
            """
        ).fetchall()
