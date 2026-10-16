# Saccofleet repository guide

Saccofleet is one Django application. Python handles authentication and data access on the server; Django templates and CSS produce the pages in the browser. SQLite stores local development data. DATABASE_URL can select PostgreSQL for a future deployment. No separate frontend framework or JavaScript build is required for this step.

## How sign in works step by step

1. The browser requests `/login/`. `config/urls.py` includes the routes in `accounts/urls.py`.
2. `SignInView` in `accounts/views.py` creates `EmailAuthenticationForm` and renders `accounts/templates/accounts/login.html` inside `templates/base.html`.
3. The browser loads `core/static/core/app.css`. The form includes Django's CSRF token, which helps prevent another website from submitting a sign-in request on the visitor's behalf.
4. On submission, `accounts/rate_limit.py` reserves a login attempt in the database. It uses keyed hashes rather than storing the email and IP address in the counter keys. Five failed attempts for an email or twenty for an IP address within ten minutes temporarily block additional attempts. Forwarded IP headers are ignored; a future trusted reverse proxy must explicitly preserve a suitable REMOTE_ADDR.
5. `accounts/forms.py` validates and normalizes the email. Django's authentication backend loads `accounts.User` and compares the submitted password with the stored password hash. Unknown, inactive and incorrect-password accounts get the same credential error.
6. On success, Django rotates the session key, stores a server-side authenticated session, and sends a session cookie to the browser. Successful logins release their attempt reservation. Cookies are HttpOnly, last up to eight hours, and require HTTPS when DEBUG is false.
7. Django redirects to a safe same-origin `next` path, or `/dashboard/`. External redirect destinations are rejected by Django's built-in LoginView behavior.
8. The `login_required` decorator on `core.views.dashboard` checks authentication on every request. Login and dashboard responses are marked not to be stored in caches.
9. Sign out submits a POST with a CSRF token. Django invalidates the server-side session and redirects to `/login/`. A GET request cannot sign the user out.

## Root files

| File | Purpose |
| --- | --- |
| `manage.py` | Loads local environment overrides and runs Django commands, such as migrate, test, createsuperuser and runserver. |
| `requirements.txt` | Pins the Python package versions used by the project. Install these inside a virtual environment. |
| `.env.example` | Documents configuration variables without real credentials. Copy it to an ignored `.env` for local overrides. |
| `.gitignore` | Keeps passwords, local databases, virtual environments, generated static files and Python caches out of Git. |
| `README.md` | Explains project status, setup, commands and the next development steps. |
| `.github/workflows/checks.yml` | Runs Django system checks, migration consistency checks and tests in GitHub Actions. |

## Project configuration

| File | Purpose |
| --- | --- |
| `config/__init__.py` | Marks config as a Python package. It has no runtime logic. |
| `config/settings.py` | Configures installed apps, middleware, database, custom user model, templates, timezone, sessions and security settings. |
| `config/urls.py` | The main URL map. Routes the home page, account URLs, protected dashboard, health endpoint and Django admin. |
| `config/wsgi.py` | Exposes the application to a WSGI server for synchronous hosting. Loads environment overrides before Django starts. |
| `config/asgi.py` | Exposes the application to an ASGI server for asynchronous-capable hosting. This is an alternative entry point to WSGI. |

## Accounts and authentication

| File | Purpose |
| --- | --- |
| `accounts/__init__.py` | Marks accounts as a Python package. |
| `accounts/apps.py` | Registers the accounts application with Django. |
| `accounts/models.py` | Defines the email-based User model and UserManager. Also defines LoginBucket, the database-backed sign-in attempt counter. Password hashing is delegated to Django. |
| `accounts/admin.py` | Makes custom users manageable through Django admin, including names, account status, password changes and permissions. |
| `accounts/forms.py` | Defines the email/password form, email normalization, input labels, autocomplete behavior and generic credential error text. It subclasses Django's AuthenticationForm. |
| `accounts/views.py` | Defines SignInView and SignOutView. Adds customer sign-in throttling to Django's built-in views and renders a 429 response when blocked. |
| `accounts/urls.py` | Maps `/login/` and `/logout/` to those views. |
| `accounts/rate_limit.py` | Implements the database-backed ten-minute attempt window, email and IP limits, reservation and successful-attempt release. |
| `accounts/templates/accounts/login.html` | The approved login screen, real POST form, CSRF token, validation messages and password-recovery instructions. |
| `accounts/tests.py` | Exercises account creation, password checks, sign-in, sign-out, sessions, CSRF, safe redirects and throttling. |
| `accounts/migrations/__init__.py` | Marks the database migration directory as a Python package. |
| `accounts/migrations/0001_initial.py` | Creates the original custom user table and email uniqueness rule. Existing migrations stay unchanged once applied. |
| `accounts/migrations/0002_loginbucket.py` | Adds the login counter table without changing existing user records. |
| `accounts/management/__init__.py` | Marks the custom command package. |
| `accounts/management/commands/__init__.py` | Marks the directory Django searches for custom commands. |
| `accounts/management/commands/prune_login_buckets.py` | Adds `python manage.py prune_login_buckets`, removing counters older than one day. Schedule it daily when deploying. |

## Shared pages and styles

| File | Purpose |
| --- | --- |
| `core/__init__.py` | Marks core as a Python package. |
| `core/apps.py` | Registers the shared-pages application. |
| `core/views.py` | Sends signed-out home-page visitors to login and signed-in visitors to the dashboard. Protects the dashboard and serves the basic process health endpoint. |
| `core/tests.py` | Tests home redirects, protected dashboard access, health output and admin login requirements. |
| `core/templates/core/dashboard.html` | A protected welcome page with the signed-in email and POST sign-out form. It does not show invented vehicle totals. |
| `core/static/core/app.css` | Styles the login and dashboard shell, including the approved colors, form spacing, responsive layouts, focus indicators and errors. |
| `templates/base.html` | Shared HTML document structure, page titles, viewport settings and CSS loading. Other page templates extend it. |
| `templates/brand.html` | Reusable Sacco Fleet wordmark and bus icon, included on both screens. |

## Documentation

| File | Purpose |
| --- | --- |
| `docs/scope.md` | Records the four approved screens, visual direction and intended fleet data rules. Some belong to future steps. |
| `docs/repository-guide.md` | This file: explains the architecture, request flow and every tracked file. |

## Local files that are not in Git

- `.venv/` contains the installed Python interpreter environment and packages.
- `db.sqlite3` contains local users, sessions and login counters. It is created by migrations; it is not a source file and must not be uploaded.
- `.env` contains optional local configuration and secrets. It is not committed.
- `__pycache__/` contains Python-generated bytecode caches.
- `staticfiles/` is the optional output of `collectstatic` for deployment.
- `.git/` contains local version history and remote configuration; it is managed by Git.

The original development placeholder `core/templates/core/home.html` was removed. `/` now redirects to login or dashboard instead of rendering that placeholder.

## Current limits

Accounts are created by an administrator using `createsuperuser` or Django admin; public registration is not included. Only email login is supported. Password recovery currently directs users to their Sacco administrator; no email reset service is configured. Fleet models and the full dashboard are the next development step. The customer `/login/` route is throttled; the built-in `/admin/login/` route needs its own production access restriction or throttling before public deployment. The application is still local development software, with deployment configuration and operational checks to follow.
