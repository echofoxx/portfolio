# Upgrade to v0.6.1

v0.6.1 is a navigation, guidance, and accessibility patch. It does not add a database migration and is compatible with the v0.5.0/v0.6.0 PostgreSQL volume.

## Upgrade

1. Back up the database and upload volume.
2. Extract v0.6.1 into a clean directory and retain the existing `.env` values.
3. Rebuild and restart the web container.
4. Hard refresh the browser. Static asset URLs use `v=0.6.1`.
5. Sign in with representative roles and verify the role focus strip, process guide, My Work, and Display preferences.

## Browser-local settings

Theme, text size, spacing, sidebar state, and process-guide visibility are saved in browser local storage. They do not change the user record and do not follow the user to another browser.

## Rollback

Because there is no database migration, stop v0.6.1 and restart the prior v0.6.0 image against the same backed-up volumes.
