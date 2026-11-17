# SACCO accounts

Apply migrations with `python manage.py migrate`. Existing accounts become managers of their previous fleets. Accounts with no fleet receive an empty SACCO. Their email addresses, passwords and fleet records carry over.

To create a new SACCO, run `python manage.py bootstrap_sacco --name "Example SACCO" --email manager@example.test`. The command prompts for a password and uses Django's password validators. The manager signs in and opens **Staff accounts** to create or deactivate operations staff for that SACCO.

Operations staff currently have read access to the fleet dashboard and vehicle register. Managers have access to the existing finance, maintenance and reporting features and manage fleet records. The daily operations workflow comes in a later phase.
