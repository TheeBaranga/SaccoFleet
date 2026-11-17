# HTTP endpoints

SaccoFleet uses Django page requests with session authentication and CSRF protection for form submissions. IDs and submitted related fields are checked against the signed-in user's SACCO. Ordinary writes take the SACCO from that user.

| Endpoint | Method | Access | Purpose |
|---|---|---|---|
| / | GET | Public | Redirect to login or dashboard |
| /health/ | GET | Public | Application health |
| /login/ | GET, POST | Public | Sign in with email and password |
| /logout/ | POST | Session | End the session |
| /password-reset/ | GET, POST | Public | Request reset through the local demo mailbox |
| /password-reset/sent/, /password-reset/complete/ | GET | Public | Recovery status |
| /password-reset/<uidb64>/<token>/ | GET, POST | Valid token | Set a new password |
| /demo-inbox/ | GET | Local superuser in debug mode | Read local reset messages |
| /admin/ | GET, POST | Django admin privileges | Framework administration |
| /staff/ | GET, POST | Manager | List and create operations staff |
| /staff/<id>/deactivate/ | POST | Manager | Deactivate own SACCO staff |
| /dashboard/ | GET | Both roles | Fleet overview. Date totals and CSV are manager-only |
| /vehicles/, /vehicles/<id>/ | GET | Both roles | Read register and details. Financial history is manager-only |
| /vehicles/add/, /vehicles/<id>/edit/ | GET, POST | Manager | Maintain vehicle records |
| /vehicles/<id>/delete/ | GET, POST | Manager | Confirm and deactivate vehicle |
| /drivers/, /routes/ | GET | Both roles | Read registers |
| /drivers/add/, /routes/add/ | GET, POST | Manager | Create reference record |
| /drivers/<id>/edit/, /routes/<id>/edit/ | GET, POST | Manager | Edit reference record |
| /drivers/<id>/deactivate/, /routes/<id>/deactivate/ | POST | Manager | Deactivate reference record |
| /assignments/ | GET | Both roles | Driver–vehicle assignment history |
| /assignments/add/, /assignments/<id>/edit/ | GET, POST | Manager | Create or correct dated assignments |
| /daily-operations/, /daily-operations/<id>/ | GET | Both roles | List and export filtered sessions or view one session |
| /daily-operations/add/ | GET, POST | Both roles | Record daily operation |
| /daily-operations/<id>/edit/ | GET, POST | Manager | Correct a saved session |
| /collections/ | GET | Manager | View or export reported collections from sessions |
| /collections/legacy/ | GET | Manager | Read or export archived standalone collections |
| /expenses/ | GET | Manager | List and export recorded expenses |
| /expenses/add/, /expenses/<id>/edit/, /expenses/<id>/delete/ | GET, POST | Manager | Maintain expenses. Service expenses are edited with their service |
| /maintenance/ | GET | Manager | Service schedule |
| /maintenance/record/, /maintenance/<id>/edit/ | GET, POST | Manager | Record or correct a completed service |
| /reports/ | GET | Manager | Period summaries and source-session CSV |

Date-filtered pages use `period=today|7|month|custom`. Custom dates use ISO `start` and `end` query parameters. Daily Operations also accepts the optional SACCO-scoped `vehicle` ID. CSV views accept `format=csv`. Expense and archive lists also support `q` and their own date presets. Django's secure cookie and HTTPS redirect settings apply when debug is disabled. Classroom testing runs locally on SQLite.
