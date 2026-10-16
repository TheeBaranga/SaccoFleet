# Saccofleet repository guide

Saccofleet is one Django application. Python handles authentication and data access on the server; Django templates and CSS produce the pages in the browser. SQLite stores local development data. DATABASE_URL can select PostgreSQL for a future deployment. No separate frontend framework or JavaScript build is required for this step.

## How the dashboard works

1. `/dashboard/` requires an authenticated session.
2. `core/views.py` filters vehicles to the fleet owned by the signed-in user.
3. It counts all those vehicles and the subset whose status is Active.
4. It sums that owner’s vehicle collections for the current Africa/Nairobi date.
5. The template displays the three totals and the first five vehicles, ordered by registration. Empty fleets show zero totals and a useful empty state.
6. Add vehicle and Record collection forms use explicit allowed fields and enforce ownership on the server. Posted fleet IDs are ignored, and a collection’s vehicle choices are restricted to the owner’s fleet.
7. Vehicle registrations are normalized to uppercase without whitespace and must be unique within a fleet. Collections use positive whole Kenyan shillings, and future dates are rejected by forms and model validation.
8. View all vehicles opens a searchable list with twenty records per page. Editing and individual vehicle details are a later step.

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
| `core/views.py` | Redirects home-page visitors, protects the dashboard, calculates owner-scoped totals using Kenya’s current date, and serves the process health endpoint. |
| `core/tests.py` | Tests home redirects, protected dashboard access, health output and admin login requirements. |
| `core/templates/core/dashboard.html` | Shows total vehicles, active vehicles, today’s recorded collections, the first five vehicles and entry actions. It extends the shared app shell. |
| `core/static/core/app.css` | Styles the login and dashboard shell, including the approved colors, form spacing, responsive layouts, focus indicators and errors. |
| `templates/base.html` | Shared HTML document structure, page titles, viewport settings and CSS loading. Other page templates extend it. |
| `templates/brand.html` | Reusable Sacco Fleet wordmark and bus icon, included on the login and app screens. |
| `templates/app.html` | Shared signed-in layout with Dashboard and Vehicles navigation, the user’s email, success messages and POST sign-out. |

## Fleet data and entry forms

| File | Purpose |
| --- | --- |
| `fleet/__init__.py` | Marks fleet as a Python package. |
| `fleet/apps.py` | Registers the fleet application with Django. |
| `fleet/models.py` | Defines Fleet, Vehicle and Collection. Adds registration uniqueness, status, capacity and amount constraints, and service date validation. |
| `fleet/forms.py` | Defines the vehicle and collection forms. Validates registrations and limits collection vehicle choices to the signed-in owner’s fleet. |
| `fleet/views.py` | Handles the searchable vehicle list and the two entry forms. Assigns ownership on the server and redirects after successful submissions. |
| `fleet/urls.py` | Maps `/vehicles/`, `/vehicles/add/` and `/collections/add/` to their views. |
| `fleet/admin.py` | Registers fleets, vehicles and collections for staff who have the appropriate Django administration permissions. |
| `fleet/tests.py` | Tests dashboard totals, the Kenya date boundary, data isolation, entry validation, CSRF protection, registration uniqueness, search and pagination. |
| `fleet/migrations/__init__.py` | Marks the fleet migration directory as a Python package. |
| `fleet/migrations/0001_initial.py` | Creates the three fleet tables, relationships and database constraints. Does not seed user records. |
| `fleet/templates/fleet/vehicle_table.html` | Reusable status table, status labels and empty/search states used by the dashboard and full vehicle list. |
| `fleet/templates/fleet/vehicles.html` | Search form, paginated vehicle list and Add vehicle link inside the app layout. |
| `fleet/templates/fleet/form.html` | Shared entry form layout with labels, validation errors, save/cancel actions and a prompt to add a vehicle before recording a collection. |

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

Accounts are created by an administrator using `createsuperuser` or Django admin; public registration is not included. Only email login is supported. Password recovery currently directs users to their Sacco administrator; no email reset service is configured. Each account currently owns one fleet. Vehicle listing and creation, collection entry and dashboard totals are implemented. Vehicle editing, individual vehicle details and multi-user fleet membership are future steps. The customer `/login/` route is throttled; the built-in `/admin/login/` route needs its own production access restriction or throttling before public deployment. The application is still local development software, with deployment configuration and operational checks to follow.
