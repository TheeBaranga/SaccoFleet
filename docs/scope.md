# Saccofleet first release

Build the four approved screens as a working fleet management application.

## Screens

- Login with authenticated access to fleet records and sign out.
- Dashboard with fleet totals, active vehicles, and today's recorded collections.
- Vehicles with search, registration, driver, route, status, and an Add vehicle form.
- Vehicle details with capacity, assigned driver, route, and maintenance dates.

## Data rules

- A fleet owns its vehicles and collection records.
- Access to fleet records must be checked on the server for every read and write.
- Vehicle registration must be unique within a fleet.
- Vehicle status is Active, Idle, or Maintenance.
- Capacity must be a positive whole number.
- Money is stored in integer Kenyan shillings, never floating point values.
- Today's collections use Africa/Nairobi calendar dates and recorded collections, not placeholder totals.
- Empty fleets show an empty state and zero totals. No sample records are inserted into real accounts.
- Next service cannot precede the last service date.

## Visual direction

Retain the approved simple white and green design with Dashboard and Vehicles navigation.
Primary color is #176747, background #F6F8F6, text #20312B, and border #E1E7E3.
No maps, charts, or additional dashboard widgets in the first release.
