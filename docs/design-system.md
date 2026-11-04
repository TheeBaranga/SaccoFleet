# Shared application design

All authenticated pages extend `templates/app.html`, which extends `templates/base.html`. The existing login and form flows use the same stylesheet. No frontend framework, chart library, or new dependency is required.

- `core/static/core/app.css`: shared color tokens, typography, surfaces, controls, tables, charts, and responsive breakpoints. The premium application theme follows the existing styles; mobile tables scroll within their containers.
- `templates/icons.html`: one SVG symbol library per page. `templates/icon.html` renders a reusable icon by name.
- `templates/stat.html`: a summary card with an optional currency prefix, icon, note, and dark treatment.
- `templates/cash_flow.html`: the same accessible date-aware SVG chart on Dashboard, Reports and vehicle details. Exact amounts accompany the bars.
- `templates/list_filters.html`: shared search/date controls for Collections and Expenses. Forms use GET, so filtered URLs can be bookmarked.
- `fleet/presentation.py`: shared owner-scoped vehicle counts, financial aggregates, and daily chart calculations. Amounts remain whole Kenyan shillings; dates use Django's configured local timezone.
- `core/views.py`: assembles dashboard totals, bounded recent collections and maintenance reminders from the signed-in owner's records.
- `fleet/views.py`: keeps existing CRUD and ownership checks, and supplies page summaries, filters, and expense-category proportions.
- `core/tests.py`: verifies dashboard calculations and financial filtering cannot expose another owner's data.

Financial list cards reflect the search and date filters. Dashboard, Reports and vehicle details share validated date controls; financial totals and chart data use the same inclusive range, defaulting to the last seven days. Vehicle status search is preserved across pagination. Read-only views never create sample transactions.

## Reporting and vehicle details

- `fleet/forms.py` → `DateRangeForm` validates preset/custom periods; malformed, future, reversed or oversized ranges show errors. No database migration is required.
- `fleet/presentation.py` → `reporting_period` supplies the shared form and dates. `cash_flow` uses two grouped database queries for a bounded daily/weekly/monthly chart; `chart_context` adds granularity and activity state.
- `templates/date_range.html` → one GET form reused on all three reporting screens.
- `templates/financial_stats.html` → shared financial summary cards for Reports and vehicle details.
- `fleet/templates/fleet/financial_history.html` → reusable recent collection/expense table, limited to five records per vehicle and selected period. View all links open the vehicle search across all dates.
- `fleet/test_reporting.py` → inclusive boundaries, invalid ranges, empty and expense-only charts, two-query aggregation, scoped history and safe quick-entry preselection.

Fleet status and service reminders describe the current fleet, independently of historical financial dates. Reporting controls do not modify records. Real browser checks use existing data without adding test transactions to the user's database.

## Classroom-only completion

- `fleet/models.py` / migration `0004`: `ServiceRecord` points to one `Expense`. No duplicate cost, vehicle or service date columns.
- `fleet/services.py`: atomic service + expense persistence; sync vehicle schedule from latest history. Generic expense editing redirects to its service form, and generic deletion of a linked expense is blocked.
- `fleet/exports.py` and `templates/csv_link.html`: shared owner-scoped CSV downloads, preserving active filters and exporting every matching row. Formula-like text is escaped; numeric amounts remain numbers.
- `accounts/views.py`, reset templates and routes: Django's token-based reset flow, separate reset throttling and a loopback-only demo inbox. No external SMTP service.
- `core/context_processors.py`: shared local-demo visibility flag for recovery pages.
- `core/backups.py`, `core/middleware.py`, `backup_demo` command: checked local SQLite copies, daily on the first signed-in demo request or on demand. No cloud tasks, paid resources or production deployment.
- `start-demo.command`: a small macOS entry point that runs migrations and the loopback development server using the existing virtual environment.
- `fleet/test_demo_features.py`, `accounts/test_recovery.py`, `core/test_backups.py`: accounting consistency, rollback, filters, CSV safety, token reset/reuse, inbox access and snapshot integrity.

Services use positive whole-shilling costs and may be edited. Their notes are preserved separately from the expense's short service description. Vehicle deletion cascades service history through its expense entries. No records or credentials are preloaded into new databases.
