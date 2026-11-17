# Backup and restore evidence

The backup command uses SQLite's snapshot API and checks database integrity. The restore command creates a separate file and refuses an existing destination. To open the restored data, point `DATABASE_URL` at that file.

```sh
.venv/bin/python manage.py backup_demo --directory .venv/classroom/backups
.venv/bin/python manage.py restore_demo PATH_TO_SNAPSHOT .venv/classroom/restored.sqlite3
```

The Phase 4 verification was performed on the isolated classroom database. SQLite integrity and foreign-key checks passed. The restored counts matched the snapshot for 4 accounts, 2 SACCOs, 20 vehicles, 20 drivers, 2 routes, 20 assignments, 2,000 operation sessions, 2 legacy collections, 2 expenses and 2 service records.

Five session relationship samples, two service-to-expense samples and two legacy collection samples matched. The verified session links included assignment, vehicle, driver, route, creator, last editor and SACCO. All four fictional accounts signed into the restored app. Manager reports loaded and cross-SACCO session URLs returned HTTP 404.
