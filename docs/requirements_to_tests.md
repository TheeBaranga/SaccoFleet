# Requirements and test evidence

| Requirement | Verification | Result |
|---|---|---|
| FR1 Authentication and SACCO access | `test_bad_password_does_not_create_authenticated_session_or_echo_password`, `test_inactive_user_cannot_sign_in`, `test_fr1_manager_creates_staff_in_own_sacco_and_staff_can_sign_in`, `test_fr1_public_signup_is_closed_and_staff_cannot_manage_accounts`, `test_fr1_direct_foreign_ids_and_staff_register_writes_are_rejected` | Pass |
| FR2 Reference registers and historical records | `test_fr2_registers_allow_managers_to_create_edit_and_list`, `test_fr2_deactivation_preserves_history_and_blocks_new_references`, `test_deactivating_vehicle_preserves_its_records` | Pass |
| FR3 Dated assignments | `test_fr3_assignments_reject_driver_and_vehicle_conflicts_and_allow_boundary`, `test_fr3_assignment_edits_cannot_invalidate_existing_sessions` | Pass |
| FR4 Daily operations | `test_fr4_daily_operation_saves_distance_and_audit_metadata` | Pass |
| FR5 Session validation | `test_fr5_rejects_invalid_sessions_and_preserves_input`, `test_fr5_duplicate_overlap_and_visible_odometer_gap`, `test_fr2_deactivation_preserves_history_and_blocks_new_references` | Pass |
| FR6 Summary, drill-down and CSV | `test_fr6_totals_drilldown_and_all_csvs_match_the_same_sessions`, `test_fr6_empty_period_has_zero_totals_and_explicit_empty_state` | Pass |
| FR7 Creation and correction accountability | `test_fr7_staff_cannot_correct_and_manager_updates_audit_metadata` | Pass |
| Usability | [Core task script](usability_tasks.md) | Script ready. Participant study pending |
| Performance | [30 measured requests per view](performance_results.md) | Pass |
| Security | FR1/FR7 tests, `test_email_is_normalized_and_password_hashed`, `test_login_and_logout_require_csrf` | Pass locally. HTTPS deployment untested |
| Reliability | FR3/FR5 rejected writes, `test_restore_matches_counts_relationships_and_refuses_overwrite`, [restore evidence](backup_restore.md) | Pass |
| Maintainability | Separate models, forms, views, templates and reusable reporting. Full regression suite below | Pass |
| Compatibility | Narrow viewport checks for Chrome and Firefox | Browser checks pending |

SaccoFleet uses server-rendered Django and SQLite for the classroom. The proposal's React and Django REST Framework split and PostgreSQL deployment were not implemented. SQLite uses a database write lock for the conflict checks. PostgreSQL row locking was not verified. Expense, service and legacy collection ownership follow existing foreign-key paths to the SACCO.

```text
Creating test database for alias 'default'...
.Not Found: /demo-inbox/
Not Found: /demo-inbox/
Not Found: /demo-inbox/
...............................................................................................
----------------------------------------------------------------------
Ran 96 tests in 6.459s

OK
Destroying test database for alias 'default'...
Found 96 test(s).
System check identified no issues (0 silenced).
Removed 1 expired login counters.
```

## Rehearsal follow-up

On 18 November 2026, the scripted HTTP demo rehearsal and restored-app checks passed. The driver display/search correction adds `test_current_assignment_drives_vehicle_list_dashboard_and_search` and `test_current_assignment_list_query_is_bounded_and_sacco_scoped`. The current full suite passed 98 tests. See [rehearsal results](demo_rehearsal_results.md) and [actual test output](demo-rehearsal-test-output.txt). The earlier 96-test output above records the Phase 4 run. Firefox startup still failed before page load, so Firefox compatibility and participant usability results remain pending.
