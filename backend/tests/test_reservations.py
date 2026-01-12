import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from db import get_backup_rows, list_reservations, set_primary_down


@pytest.fixture
def client(tmp_path):
    set_primary_down(False)
    db_path = tmp_path / "test.db"
    app = create_app({"TESTING": True, "DATABASE_PATH": str(db_path)})
    with app.test_client() as client:
        yield client


@pytest.fixture
def sample_payload():
    return {
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "event": "Tech Conference 2025",
    }


def test_successful_reservation(client, sample_payload):
    response = client.post("/api/reservations", json=sample_payload)
    data = response.get_json()

    assert response.status_code == 201
    assert data["ok"] is True
    assert data["data"]["reservation"]["id"] is not None


def test_invalid_email_rejected(client, sample_payload):
    payload = dict(sample_payload, email="invalid-email")
    response = client.post("/api/reservations", json=payload)
    data = response.get_json()

    assert response.status_code == 400
    assert data["ok"] is False
    assert data["error"]["code"] == "INVALID_EMAIL"


def test_missing_name_rejected(client, sample_payload):
    payload = dict(sample_payload, name="")
    response = client.post("/api/reservations", json=payload)
    data = response.get_json()

    assert response.status_code == 400
    assert data["ok"] is False
    assert data["error"]["code"] == "INVALID_NAME"


def test_invalid_event_rejected(client, sample_payload):
    payload = dict(sample_payload, event="Unknown")
    response = client.post("/api/reservations", json=payload)
    data = response.get_json()

    assert response.status_code == 400
    assert data["ok"] is False
    assert data["error"]["code"] == "INVALID_EVENT"


def test_reservation_written_to_both_tables(client, sample_payload, tmp_path):
    response = client.post("/api/reservations", json=sample_payload)
    assert response.status_code == 201

    db_path = tmp_path / "test.db"
    primary_rows = list_reservations(str(db_path))
    backup_rows = get_backup_rows(str(db_path))

    assert len(primary_rows) == 1
    assert len(backup_rows) == 1
    assert primary_rows[0]["user_email"] == backup_rows[0]["user_email"]


def test_failover_reads_from_backup(client, sample_payload):
    client.post("/api/reservations", json=sample_payload)

    client.post("/admin/chaos/enable")
    response = client.get("/api/reservations")
    data = response.get_json()

    assert response.status_code == 200
    assert data["data"]["active_store"] == "backup"
    assert len(data["data"]["reservations"]) == 1


def test_chaos_allows_backup_write(client, sample_payload):
    client.post("/admin/chaos/enable")
    response = client.post("/api/reservations", json=sample_payload)
    data = response.get_json()

    assert response.status_code == 201
    assert data["data"]["reservation"]["stored_in"] == "backup"


def test_duplicate_reservation_rejected(client, sample_payload):
    client.post("/api/reservations", json=sample_payload)
    response = client.post("/api/reservations", json=sample_payload)
    data = response.get_json()

    assert response.status_code == 409
    assert data["error"]["code"] == "DUPLICATE_RESERVATION"
