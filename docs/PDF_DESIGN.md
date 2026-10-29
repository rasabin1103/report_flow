# PDF editorial system

## Reading order
The default compact opening page contains a branded masthead, report identity/date, a short scope statement, up to two calculated observations, a data coverage note where relevant, KPI cards and the first evidence chart. The optional full cover and contents remain available for longer reports.

Analysis charts pair visual evidence with a short descriptive finding and a calculation/coverage caption. The appendix separates supporting rows from the executive narrative. Methodology records the source, scope, selected columns, filters, KPI definitions (including local filters), missing-category policy and generation time.

## Visual language
- Navy typography, a restrained blue accent, pale indicator surfaces and a white print-friendly body.
- Embedded DejaVu Sans, a fixed typographic hierarchy and equal-height KPI cards; value type scales down for long amounts.
- Localized dates, numbers, boolean values, headers, captions and methodology; source values and caller labels remain untouched.
- Bar value labels, explicit metric axes/units, short time labels and legends carrying counts and percentages for circular charts.
- Chart percentage denominators are disclosed if only a subset is shown. Observations use all grouped data, never a top-N subset.
- Weighted table widths, numeric alignment, wrapping, repeated headers and explicit omitted-row counts.
- Chart titles travel with their images and findings. Small tables travel with their section/title and footnote. Large tables remain pageable.
- Landscape layouts place observations beside their charts to avoid oversized graphics.

## Template behavior
Executive uses compact 7.5 pt table text, four-point row padding and a shorter chart aspect. Detailed uses 8 pt table text, five-point padding and slightly taller charts. Neither template silently drops content to meet a page target; configured max_rows and chart limits are disclosed.

## Evidence rules
Observations are deterministic descriptions. They cover leading categories, ties, additive shares and changes between available time buckets. Shares are suppressed for averages, distinct counts, negative contributions or null aggregate groups. Zero baselines suppress percentage changes. Available time buckets may be partial; no recommendation, cause or prediction is generated.

## Review procedure
Regenerate all examples with scripts/generate_examples.py. Extract expected titles, values, locale strings and omissions; run the analytical regression tests. Render the PDFs through Poppler and inspect every page for clipped text, inconsistent card heights, unreadable labels, lonely headings and excessive breaks. Test long-table pagination separately with the 540-row fixture. Page counts alone do not certify commercial quality.

The synthetic example data uses a fixed random seed and independent category assignments. Project completion and delivery status are consistent. Examples show complete grouped summaries with additive totals where meaningful; raw row-level detail remains available through configuration. Chart/KPI calculations retain the entire configured scope.

## Personalized covers
Full covers use reporting/cover.py to measure title/subtitle text, maintain logo aspect ratio and present recipient, period, reference and confidentiality. Compact covers keep their opening-page composition. reporting/pagination.py adds final page totals after layout, including multi-pass contents. Tables use numbered captions. See BRANDING.md for CLI, multipart and JSON examples.

## Editorial refinement - 2026-10-29
Standalone covers now use a pale title surface sized to its measured text and a larger logo, reducing solid dark ink and avoiding a fixed oversized block. Executive findings appear once rather than repeating below the same chart. Narrative language names record counts and changes directly. Example tables summarize every group rather than an arbitrary first-row sample. Additive totals are explicit and maintain their full-group denominator under display limits.

Short line charts (at most eight displayed observations) use a compact aspect ratio; the raster and its PDF placement use the same geometry. This preserves label proportions and avoids a separate page solely for methodology in the sales example. Metadata rows use compact padding while preserving the configured font size.
