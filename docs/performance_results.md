# Performance results

Measured 17 November 2026 on the local arm64 Mac. The benchmark uses Django's in-process HTTP test client with rendered templates and authenticated sessions. It includes Django request handling, database queries and rendering, and does not measure browser or network latency.

```text
Darwin 27.0.0 (arm64)
Python 3.12.14 | Django 5.2.18 | SQLite 3.53.1
File-backed SQLite | 2000 total sessions | 1000 sessions in scope | 2026-08-09 through 2026-11-17 (EAT)
30 in-process authenticated GETs per view after one warm-up; response rendering included.
daily_operations: 30/30 under 2s (100.0%); median 0.009s; maximum 0.010s
reports: 30/30 under 2s (100.0%); median 0.009s; maximum 0.010s
```

Both views met the proposal target of at least 95% under 2 seconds. To repeat, point `DATABASE_URL` at the seeded demo database and run `python manage.py benchmark_classroom`.
