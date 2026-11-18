# Demo rehearsal results

Rehearsed on 18 November 2026 using a separate, file-backed SQLite copy of the fictional Acacia and Baobab dataset. The checks sent actual HTTP requests with sessions and CSRF tokens to the local Django server. This was a scripted functional rehearsal. The participant usability study has not been run.

| Check | Actual result |
|---|---|
| Four fictional accounts | Both SACCOs' managers and operations staff signed in successfully |
| Invalid login | Generic error returned and protected content stayed inaccessible |
| Registers and assignments | Lists loaded. Manager created a fictional vehicle, driver, route and dated assignment |
| Assignment overlap | Rejected with a field error and unchanged assignment count |
| Daily return | Staff recorded 2 trips, 40 km and KSh 2,500 and opened the saved entry |
| Invalid odometer and duplicate | Both rejected without additional records. Form values were preserved |
| Manager correction | Manager changed the trip count to 3. Creator stayed staff and last editor became manager |
| Roles and SACCO isolation | Manager-only staff requests returned 403. Foreign session URLs returned 404 |
| Seed report and CSV | The 17 November fixture returned 5 trips, 200 km and KSh 10,500 from two sessions |
| Expenses and maintenance | KSh 200 fuel plus one KSh 300 service expense. Service schedule updated and report difference was KSh 2,000 |
| Sign out and return | Protected page required authentication after sign-out. Staff signed in again |
| Backup and restore | Counts, SQLite integrity, foreign keys and sampled relationships matched. All four accounts signed in to the restored app |

The rehearsal exposed a vehicle-list mismatch. A saved assignment could still appear as Unassigned because the table and search read the legacy driver field. The list and dashboard now use the driver from the assignment active at the current time, with a legacy fallback. Two regression tests cover the assignment's end boundary, search, SACCO isolation and a bounded query.

The full regression suite passed 98 tests after this correction.

## Data preservation

The original database SHA-256 before and after the rehearsal was identical. All entry, correction and restore operations used the fictional copy. No production accounts or operational records were used.
