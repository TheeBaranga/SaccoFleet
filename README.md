# SaccoFleet — classroom demo

A local Django fleet-management project for class demonstrations. No production deployment, paid hosting, external email provider, or cloud backup service is required. Keep the demo bound to `127.0.0.1`.

## Run locally

The project uses Python 3.12, Django, server-rendered HTML/CSS and SQLite. From the repository directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

On this existing checkout the environment, account, and data are already present: run only the last command, or open `start-demo.command` on macOS. Keep its terminal running while presenting. Open http://127.0.0.1:8000/login/. Credentials and database contents are not committed. Existing demo accounts can use Forgot password if needed.

## Demonstration flow

1. Sign in and review fleet totals, cash flow and reminders. Choose a custom historical date range if the latest week has no transactions.
2. Open Vehicles, search a registration and open its details. Record collection/expense actions preselect that vehicle; forms still enforce ownership.
3. Use **Record service** on Maintenance or vehicle details. Enter its date, type, positive whole-KSh cost, notes and optional next service. One linked repairs expense records the cost exactly once. **Edit** in service history updates the same expense. Vehicle service dates reflect the latest completed service in recorded history. Historical date-only information is not fabricated into service records.
4. Download CSV from Collections, Expenses or Reports. Downloads include all matching records, not just the current page. Reports export the selected inclusive date range; financial lists export their current search/date filters. Text cells are escaped against spreadsheet formulas.
5. Sign out, select Forgot password, and enter your account email. The demo operator can retrieve the link from the local mail files in `.venv/demo-emails/` or open **Local demo inbox** from the reset request page in a separate browser profile signed in as a superuser. Use the link to choose a new password. No external mail is sent. Links expire after 30 minutes and cannot be reused. The browser inbox requires a superuser session, DEBUG mode, and localhost.

Dashboard, Reports and vehicle financial details share Today, Last 7 days, This month and Custom range controls. Custom ranges cover up to 366 days and cannot end in the future. Charts group daily, weekly or monthly and show an explicit empty state when appropriate. Each account sees only its own fleet. Vehicle status is entered manually, not GPS tracking.

## Free local backups

The first signed-in request of each demo day automatically creates an integrity-checked SQLite snapshot under `backups/`. The app must be running and used for this to happen; no cloud scheduler runs while it is closed. Backups are not overwritten and are excluded from Git by the existing `*.sqlite3` rule.

Before presenting or changing data, you can also run:

```sh
.venv/bin/python manage.py backup_demo
```

To restore: stop the server, make an extra backup, then copy the chosen `.sqlite3` backup over `db.sqlite3` and restart. Restore replaces the current data with that snapshot. Keep backups on your own computer and copy them to a USB drive if you need protection against disk loss. These snapshots are SQLite-only; PostgreSQL is not required or provisioned for this class project.

## Code organization

- `config/`: settings and URL routing.
- `accounts/`: email/password sign-in, Django sessions, reset flow and local demo inbox. Login and reset requests have separate database-backed rate-limit buckets.
- `core/`: dashboard, shared design, demo context, automatic local snapshots and backup command.
- `fleet/models.py`: owner fleet, vehicles, collections, expenses and service history. A service references one expense rather than duplicating its amount/date/vehicle.
- `fleet/forms.py`: validated record forms and the reusable date-range form.
- `fleet/views.py`: ownership checks, forms, lists, financial pages and exports.
- `fleet/presentation.py`: shared date validation and aggregate chart calculations.
- `fleet/services.py`: atomic service/expense saving and schedule synchronization.
- `fleet/exports.py`: shared streaming CSV response and safe text cells.
- `templates/`: inherited application shell and reusable controls, cards, charts and icons.
- `docs/design-system.md`: design and implementation notes.

No extra frontend framework or new runtime dependency was added for these demo features. SQLite, ignored local email files, backups, secrets and virtual environments stay out of source control. PostgreSQL support via `DATABASE_URL` remains in the original settings but is unused for the default demonstration.

## Verify

```sh
.venv/bin/python manage.py test
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py check
```

Tests create disposable accounts and records in a separate test database. Password-reset tests use local mail only. Do not run demonstrations that alter credentials against another person's account.
