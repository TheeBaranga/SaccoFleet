# Saccofleet

A simple Sacco fleet management application based on the approved Login, Dashboard, Vehicles and Vehicle details designs.

## Step 1 foundation

This first step sets up Django, the database, email based user accounts, the Django administration interface, and automated checks. The customer login screen and fleet features are not implemented yet.

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

Open http://127.0.0.1:8000/ for the development page, /admin/ for administration, and /health/ for a basic process health check. The health endpoint does not test database connectivity.

### Check the project

```sh
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

### Project structure

- `config/`: application settings, URL routing and server entry points.
- `accounts/`: custom email based user model, administration and initial migration.
- `core/`: development page, health check and tests.
- `docs/scope.md`: agreed screens and data rules.
- `.env.example`: configuration names; copy to an ignored `.env` for local overrides.
- `requirements.txt`: exact dependency versions used for this setup.

The custom user model is created before the first database migration so email login can be added without replacing Django's default user table later. Passwords are hashed by Django.

## Next steps

1. Build the approved login screen, sign out and protected dashboard, including login throttling.
2. Add fleet ownership, vehicle records, search, create and edit forms.
3. Add maintenance information and recorded collections for dashboard totals.
4. Configure password recovery email, deployment and production security checks.

## Deployment configuration

This setup is for local development. It has not been deployed. Before production, set DJANGO_DEBUG=false, a unique DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, DATABASE_URL and HTTPS. Configure a production WSGI or ASGI server and static file serving. Run `python manage.py check --deploy` with production settings. Provision PostgreSQL and move existing data explicitly; changing DATABASE_URL does not migrate SQLite records.

Local environment files, databases and virtual environments are ignored by Git. Never commit credentials or user data.
