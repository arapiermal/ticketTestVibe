# Reliability Documentation

## Error Handling

- All API endpoints validate input and return structured JSON errors with meaningful codes.
- Database operations are wrapped with `try/except` and return user-friendly messages.
- A global error handler ensures unexpected exceptions never crash the server.

## Redundancy Strategy

- Two tables are maintained in the same SQLite database: `reservations` (primary) and `reservations_backup` (backup).
- Writes always attempt the primary insert and then the backup insert.
- Reads normally use the primary table but automatically fall back to the backup table when the primary is unavailable or an error occurs.

## Failover Logic

- A shared in-memory `PRIMARY_DB_DOWN` flag simulates an outage of the primary store.
- When the flag is enabled, all primary table operations raise an exception to force failover.
- The `/api/status` endpoint reports `active_store` and `last_error` so operators can see when failover occurred.

## Chaos Simulation

- `POST /admin/chaos/enable` flips the in-memory flag to simulate a primary outage.
- `POST /admin/chaos/disable` restores normal operation.
- Backup operations continue to succeed while chaos mode is enabled.

## Testing Strategy

The pytest suite covers:

- Successful reservation creation with valid input.
- Validation failures for invalid email, missing name, and invalid event.
- Redundancy validation that writes exist in both tables.
- Failover behavior when chaos mode is enabled and reads are served from backup.
- Chaos mode allowing writes to continue via the backup store.
- Duplicate reservation rejection.
