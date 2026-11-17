# SaccoFleet

SaccoFleet is a fleet management project for Kenyan matatu SACCOs. Managers maintain vehicles, drivers, routes and assignments. Operations staff record daily sessions, and managers review date-filtered activity, reported collections, expenses and maintenance. The app uses Python 3.12, Django templates and SQLite.

## Run locally

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

Open [SaccoFleet](http://127.0.0.1:8000/login/). Use your existing account or run `python manage.py bootstrap_sacco --name "Example SACCO" --email manager@example.test` for a new organisation. Managers create staff accounts in the app.

## Classroom data

From the repository directory, create a fresh isolated SQLite file for the fictional exercise.

```sh
mkdir -p .venv/classroom
demo_dir=$(mktemp -d "$PWD/.venv/classroom/demo.XXXXXXXX")
export DATABASE_URL="sqlite:///$demo_dir/demo.sqlite3"
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_classroom --demo-db "$demo_dir/demo.sqlite3"
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

| SACCO | Manager | Operations staff |
|---|---|---|
| Acacia Classroom SACCO | `manager.acacia@example.test` | `staff.acacia@example.test` |
| Baobab Classroom SACCO | `manager.baobab@example.test` | `staff.baobab@example.test` |

The password for these fictional accounts is `ClassroomFleet-2026!`. On the seed date, select **Today** or enter that date as a custom range to see 5 trips, 200 km and KSh 10,500 per SACCO.

Run tests with `.venv/bin/python manage.py test` and benchmark the seeded database with `.venv/bin/python manage.py benchmark_classroom`. See [test evidence](docs/requirements_to_tests.md), [backup and restore](docs/backup_restore.md), and the [screenshots checklist](docs/screenshots_checklist.md).
