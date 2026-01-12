import os
import re
import sqlite3
from flask import Flask, jsonify, request, send_from_directory

from db import (
    create_reservation,
    delete_reservation,
    get_db_path,
    get_status,
    init_db,
    list_reservations,
    set_primary_down,
)

EVENTS = [
    "Tech Conference 2025",
    "Music Festival",
    "Art Expo",
    "Startup Pitch Night",
]

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def create_app(test_config=None):
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
    app = Flask(__name__, static_folder=frontend_path, static_url_path="")

    if test_config:
        app.config.update(test_config)

    db_path = get_db_path(app.config.get("DATABASE_PATH"))
    init_db(db_path)

    def success(data, status=200):
        return jsonify({"ok": True, "data": data}), status

    def error(code, message, details=None, status=400):
        payload = {"code": code, "message": message}
        if details is not None:
            payload["details"] = details
        return jsonify({"ok": False, "error": payload}), status

    def validate_reservation(payload):
        if not payload:
            return error("INVALID_JSON", "Request body must be JSON.")

        user_name = (payload.get("name") or "").strip()
        user_email = (payload.get("email") or "").strip()
        event_name = (payload.get("event") or "").strip()

        if not user_name or len(user_name) > 100:
            return error("INVALID_NAME", "Name is required and must be under 100 characters.")
        if not EMAIL_PATTERN.match(user_email):
            return error("INVALID_EMAIL", "Email address is not valid.")
        if event_name not in EVENTS:
            return error("INVALID_EVENT", "Selected event is not available.")

        return None

    @app.route("/api/events", methods=["GET"])
    def api_events():
        return success({"events": EVENTS})

    @app.route("/", methods=["GET"])
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/api/reservations", methods=["POST"])
    def api_create_reservation():
        payload = request.get_json(silent=True)
        validation_error = validate_reservation(payload)
        if validation_error:
            return validation_error

        try:
            reservation = create_reservation(
                db_path,
                payload["name"].strip(),
                payload["email"].strip(),
                payload["event"].strip(),
            )
        except sqlite3.IntegrityError:
            return error(
                "DUPLICATE_RESERVATION",
                "A reservation already exists for this email and event.",
                status=409,
            )
        except sqlite3.Error as exc:
            return error("DB_ERROR", "Database error occurred.", details=str(exc), status=500)
        except Exception as exc:
            return error("UNEXPECTED_ERROR", "Unexpected error occurred.", details=str(exc), status=500)

        status_info = get_status()
        data = {
            "reservation": reservation,
            "active_store": status_info["active_store"],
            "last_error": status_info["last_error"],
        }
        return success(data, status=201)

    @app.route("/api/reservations", methods=["GET"])
    def api_list_reservations():
        try:
            reservations = list_reservations(db_path)
        except sqlite3.Error as exc:
            return error("DB_ERROR", "Database error occurred.", details=str(exc), status=500)
        except Exception as exc:
            return error("UNEXPECTED_ERROR", "Unexpected error occurred.", details=str(exc), status=500)

        status_info = get_status()
        return success(
            {
                "reservations": reservations,
                "active_store": status_info["active_store"],
                "last_error": status_info["last_error"],
            }
        )

    @app.route("/api/reservations/<int:reservation_id>", methods=["DELETE"])
    def api_delete_reservation(reservation_id):
        try:
            deleted = delete_reservation(db_path, reservation_id)
        except sqlite3.Error as exc:
            return error("DB_ERROR", "Database error occurred.", details=str(exc), status=500)
        except Exception as exc:
            return error("UNEXPECTED_ERROR", "Unexpected error occurred.", details=str(exc), status=500)

        if not deleted:
            return error("NOT_FOUND", "Reservation not found.", status=404)

        return success({"deleted": True})

    @app.route("/api/status", methods=["GET"])
    def api_status():
        return success(get_status())

    @app.route("/admin/chaos/enable", methods=["POST"])
    def enable_chaos():
        set_primary_down(True)
        return success(get_status())

    @app.route("/admin/chaos/disable", methods=["POST"])
    def disable_chaos():
        set_primary_down(False)
        return success(get_status())

    @app.errorhandler(404)
    def not_found(_error):
        return error("NOT_FOUND", "Resource not found.", status=404)

    @app.errorhandler(Exception)
    def handle_exception(exc):
        return error("INTERNAL_SERVER_ERROR", "Server error occurred.", details=str(exc), status=500)

    return app


if __name__ == "__main__":
    config = {"DATABASE_PATH": os.environ.get("DATABASE_PATH")}
    app = create_app(config)
    app.run(host="0.0.0.0", port=5000, debug=True)
