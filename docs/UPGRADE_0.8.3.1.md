# Upgrade to v0.8.3.1

v0.8.3.1 is a presentation-only patch for the v0.8.3 travel map. It aligns the Linked Map Index panel to the rendered map-canvas height and confines overflow to the ranked location list.

## Upgrade

1. Back up the existing database, `.env`, and upload volume according to local policy.
2. Replace the v0.8.3 application files with the v0.8.3.1 release.
3. Rebuild and restart the application:

   ```bash
   docker compose build --no-cache
   docker compose up -d
   ```

4. Sign in and open **Travel → Overview**.
5. Confirm that the Linked Map Index bottom edge matches the map bottom edge at desktop width and after resizing the browser.
6. Confirm that a long Top Locations list scrolls inside the panel without increasing its height.

## Compatibility

- Database migration: none; migration head remains `0009_self_service_v080`.
- New runtime dependency: none.
- Configuration change: none.
- Rollback: restore the v0.8.3 application image/files; no data rollback is required.
