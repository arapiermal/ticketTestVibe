# Event Ticket Booking System — Applying Reliable Programming Principles

A mini project that demonstrates reliable programming patterns: strict validation, redundancy with failover, chaos monkey simulation, and automated tests.

## Repository Structure

```
backend/
  app.py
  db.py
  requirements.txt
  tests/
    test_reservations.py
frontend/
  index.html
  styles.css
  app.js
README.md
DOCUMENTATION.md
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

## Run the Application

```bash
cd backend
export FLASK_APP=app.py
flask run
```

Open the app in your browser: http://127.0.0.1:5000

## Run Tests

```bash
cd backend
pytest
```

## Chaos Monkey

Enable failure of the primary database:

```bash
curl -X POST http://127.0.0.1:5000/admin/chaos/enable
```

Disable chaos mode:

```bash
curl -X POST http://127.0.0.1:5000/admin/chaos/disable
```

## API Examples

List events:

```bash
curl http://127.0.0.1:5000/api/events
```

Create a reservation:

```bash
curl -X POST http://127.0.0.1:5000/api/reservations \
  -H 'Content-Type: application/json' \
  -d '{"name":"Ada Lovelace","email":"ada@example.com","event":"Tech Conference 2025"}'
```

List reservations:

```bash
curl http://127.0.0.1:5000/api/reservations
```

Check system status:

```bash
curl http://127.0.0.1:5000/api/status
```
