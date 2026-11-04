# Shared application design

All authenticated pages extend `templates/app.html`, which extends `templates/base.html`. The existing login and form flows use the same stylesheet. No frontend framework, chart library, or new dependency is required.

- `core/static/core/app.css`: shared color tokens, typography, surfaces, controls, tables, charts, and responsive breakpoints. The premium application theme follows the existing styles; mobile tables scroll within their containers.
- `templates/icons.html`: one SVG symbol library per page. `templates/icon.html` renders a reusable icon by name.
- `templates/stat.html`: a summary card with an optional currency prefix, icon, note, and dark treatment.
- `templates/cash_flow.html`: the same accessible seven-day SVG chart on Dashboard and Reports. Exact amounts accompany the bars.
- `templates/list_filters.html`: shared search/date controls for Collections and Expenses. Forms use GET, so filtered URLs can be bookmarked.
- `fleet/presentation.py`: shared owner-scoped vehicle counts, financial aggregates, and daily chart calculations. Amounts remain whole Kenyan shillings; dates use Django's configured local timezone.
- `core/views.py`: assembles dashboard totals, bounded recent collections and maintenance reminders from the signed-in owner's records.
- `fleet/views.py`: keeps existing CRUD and ownership checks, and supplies page summaries, filters, and expense-category proportions.
- `core/tests.py`: verifies dashboard calculations and financial filtering cannot expose another owner's data.

Financial list cards reflect the search and date filters. Reports totals remain all time and are labelled accordingly; the chart is explicitly seven days. Vehicle status search is preserved across pagination. Read-only views never create sample transactions.
