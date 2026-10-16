# Saccofleet

A simple Sacco fleet management application based on the approved Login, Dashboard, Vehicles and Vehicle details designs.

## Current step authentication

The approved login screen now uses real email and password authentication. Sign-in creates a Django session, the dashboard requires login, and sign-out uses a CSRF-protected POST. Fleet records and the full dashboard are the next step.

### Requirements

Python 3.12 or newer. SQLite is included with Python. PostgreSQL can be selected through DATABASE_URL.

### Run locally

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

Choose your own administrator email and password when prompted. There are no default credentials or sample fleet records.

Open http://127.0.0.1:8000/login/ and use the account you created. Successful sign-in opens /dashboard/. The root page redirects according to your sign-in state. /admin/ is for staff administration; /health/ is a basic process health check, not a database readiness check.

The login form accepts email addresses only. Forgot password shows administrator recovery instructions; email-based recovery and public registration are not included yet.

### Check the project

```sh
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

### Project structure

- `config/`: application settings, URL routing and server entry points.
- `accounts/`: custom email based user model, administration and initial migration.
- `core/`: protected dashboard, shared CSS, health check and tests.
- `docs/scope.md`: agreed screens and data rules.
- `.env.example`: configuration names; copy to an ignored `.env` for local overrides.
- `requirements.txt`: exact dependency versions used for this setup.

The custom user model is created before the first database migration so email login can be added without replacing Django's default user table later. Passwords are hashed by Django.

## Authentication behavior

Five failed attempts for an email address or twenty for an IP address within ten minutes pause customer sign-in for ten minutes. Counters are stored in the database and use keyed hashes for their identifiers. Successful sign-ins do not count as failures. Run `python manage.py prune_login_buckets` daily in production to remove expired counters. The admin login route is separate and needs its own production access restriction or throttling.

See [the repository guide](docs/repository-guide.md) for a step-by-step request flow and an explanation of every file.

## Next steps

1. Add fleet ownership, vehicle records, search, create and edit forms.
2. Add maintenance information and recorded collections for dashboard totals.
3. Configure password recovery email, deployment and production security checks.

## Deployment configuration

This setup is for local development. It has not been deployed. Before production, set DJANGO_DEBUG=false, a unique DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, DATABASE_URL and HTTPS. Configure a production WSGI or ASGI server and static file serving. Run `python manage.py check --deploy` with production settings. Provision PostgreSQL and move existing data explicitly; changing DATABASE_URL does not migrate SQLite records.

Local environment files, databases and virtual environments are ignored by Git. Never commit credentials or user data.
