# Phase 2 Travel Map Plan — Geographic Decision Intelligence

## Outcome

Extend the v0.8.3 cost-and-compliance map into a briefing-ready geographic analysis workspace while retaining offline operation, source traceability, accessible alternatives, role scope, and explicit unmapped exposure.

## Workstream 1 — Governed geographic foundation

- Package simplified, per-country Natural Earth geometry as a same-origin static asset with ISO-3 identifiers and documented source/version metadata.
- Add a steward-managed registry for canonical location, country, COCOM AOR, confidence, aliases, effective dates, and disposition status.
- Never silently omit unresolved locations. Every view must show unmapped request count and estimated cost.
- Version AOR assignments and boundaries because geographic responsibility can change.

## Workstream 2 — Markers / Regions views

- Retain v0.8.3 Markers as the default operational view.
- Add Regions choropleth shaded by estimated cost or request count, with accessible table parity.
- Preserve the compliance story through an amber border or explicit gap badge rather than encoding two competing fill scales.
- Use the same filters, source drill-through, executive chips, selection model, and URL state across views.

## Workstream 3 — COCOM AOR overlay

- Add toggleable, locally packaged INDOPACOM, EUCOM, CENTCOM, AFRICOM, NORTHCOM, and SOUTHCOM planning boundaries.
- Display per-AOR chips for requests, estimated cost, engagements, completed travel, linked reports, missing reports, and unmapped exposure.
- Label overlays as planning/reference geometry unless the boundary asset has an approved authoritative owner.

## Workstream 4 — Fiscal time exploration

- Add server-side location-by-FY-quarter aggregation so filtering remains accurate and does not expose traveler-level routes.
- Provide an FY selector and accessible Q1–Q4 range scrubber with request-count mini-bars.
- Keep standard date fields synchronized for users who need exact ranges.
- Refit and recompute markers, regions, AOR chips, compliance, and the location index after every time change.

## Workstream 5 — Conditional density view

- Add a request-count-weighted heat/density view only when the filtered dataset meets an approved minimum point/location threshold.
- Do not weight heat by estimated cost; a single high-cost trip must not create a false activity cluster.
- Hide or disable the mode with a plain-language explanation when density is insufficient.
- Package all rendering code locally; no external tiles, APIs, fonts, or telemetry.

## Workstream 6 — Briefing and export

- Add saved named map views with owner, role scope, filters, view mode, measure, AOR state, and time range.
- Add a presentation mode and accessible PNG/PDF briefing snapshot containing timestamp, filters, definitions, unmapped totals, and cost-basis disclaimer.
- Provide a source table/export for every visual aggregate.

## Acceptance gates

- Country/AOR totals reconcile to the filtered source records, with unmapped values reported separately.
- Marker, Regions, and AOR totals reconcile with the accessible table alternative.
- Sparse heat data never renders as a misleading density surface.
- Keyboard, screen reader, reduced-motion, high-contrast, touch, and responsive behavior pass target-browser testing.
- Geometry provenance, version, effective date, and stewardship owner are documented.
- Role and sensitivity scope are enforced server-side before data reaches the browser.
- Docker offline startup, migration compatibility, restart persistence, and export generation are validated on the target host.

## Suggested delivery sequence

1. Geometry package and stewardship registry.
2. Country rollups and Regions view.
3. AOR registry, overlays, and AOR chips.
4. FY-quarter aggregation and scrubber.
5. Saved views and briefing export.
6. Conditional heat view after density thresholds are validated with real operating data.
