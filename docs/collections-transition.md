# Collections transition plan

Existing collection rows stay in the original SQLite table with their IDs, vehicle links, dates and amounts. The Legacy Collections page and its CSV provide read-only access for the SACCO manager. Standalone collection creation, editing and deletion are retired. No schema or data migration is required.

Daily operation sessions are the source of reported collections for the dashboard, reports, vehicle history and current Collections. The date filters use the session's start date in Africa/Nairobi. The old entries lack an assignment, route, session timestamps, trip count and odometer readings, so the app preserves them as historical evidence. Legacy amounts are excluded from session totals. Administrators can compare the archive to an existing backup if needed.

Before restarting a local app on this commit, take a SQLite backup. Then compare the Legacy Collections count and CSV with the pre-change records and verify a sample daily operation against the dashboard and filtered CSV. The previous code can still read the same database because the table and rows stay in place.
