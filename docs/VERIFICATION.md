# Verification record

## Professional editorial refinement - 2026-10-29

- Lightened the standalone cover and enlarged the logo; the title surface now follows measured content height.
- Rewrote generic narrative and removed duplicate chart findings already present in the executive brief.
- Replaced arbitrary raw-row samples in all examples with complete grouped summaries.
- Added include_total for additive grouped tables, with correct handling of omitted groups and all-null sums; invalid nonadditive totals are rejected.
- Added eight analytical/editorial regression tests. Final suite: 94 passed in 36.93 seconds; one upstream Starlette/httpx warning. Ruff, format checks and mypy passed.
- Final visual review: all eleven pages rendered and inspected (branded 4, quality 3, sales 2, projects 2). Short time series use measured compact chart geometry; chart images retain their intended aspect ratio. Methodology no longer occupies a separate sales page.
- Historical example descriptions below refer to their dated revisions; current examples no longer sample twelve source rows.

## Cover and branding revision - 2026-10-28

- Added safe optional logo-file uploads and title/subtitle/cover-style form fields to generate/validate, with matching CLI options and a shared override validator.
- Added a measured standalone cover with logo, title/subtitle, recipient, reporting period, document reference and confidentiality; compact cover remains the default.
- PNG alpha and JPEG orientation are preserved; images are reconstructed without source metadata.
- Added final X-of-Y page counts and localized numbered table captions.
- Final automated suite: 86 passed in 31.70 seconds (one upstream Starlette/httpx deprecation warning). Ruff/format and mypy checks passed across 28 application/CLI source files.
- Regenerated and rendered all twelve pages: QA (3), sales (3), projects (2), and the new branded example (4). Reviewed the complete contact sheet plus full-size cover, analysis and appendix pages.
- The logo in the branded example is explicitly fictional demonstration branding. It can be replaced using --logo or the multipart logo field.

## Editorial revision - 2026-10-28

- Full application regression suite: 73 passed in 25.91 seconds on Python 3.14.3 / Windows.
- Ruff check and format check passed; mypy passed across 26 application/CLI source files.
- The suite exercises API and CLI PDF generation, ingestion limits, analytical correctness, worker cleanup, long-table pagination, number formatting and PDF text/content checks.
- Editorial regressions cover Spanish accents/prose, localized number/date/boolean presentation, first-page evidence, standalone cover/contents, ties, null aggregate groups, negative/nonadditive metrics, complete-group share denominators and partial-interval disclosures.
- All eight pages of the three updated examples were rendered with Poppler and inspected. A separate landscape variant was also rendered and inspected.
- Corrected chart/section pagination, detached appendix headings, circular-chart labels, KPI card height alignment and metadata density.

## Example artifacts

- Quality: 3 pages (previously 6).
- Sales: 3 pages (previously 7).
- Projects: 2 pages (previously 8).

The page reduction combines editorial layout changes with a deliberate example configuration change: detail tables now show twelve rows rather than 100/80/90. Each omitted-row count is printed. All KPIs, observations and charts still use the full filtered dataset. These are not equal-detail-volume page-count comparisons. The seeded synthetic datasets were also improved to avoid perfectly correlated categories and inconsistent project completion/status values.

## Original runtime baseline

The initial implementation was verified with a Python 3.12 Linux Docker image and a healthy Compose service using non-root/read-only settings and resource limits. Host port 8000 was occupied, so that verification used REPORTFLOW_PORT=18080. HTTP inspect, validate and PDF generation returned 200; the installed reportflow entry point was checked. The verification stack was stopped afterward. The editorial revision was subsequently tested through the shared API/CLI paths; Docker was not rebuilt in this revision.

## Practical scope

The report engine remains backend-only, stateless and independently reusable. Generic observations describe data without causes, predictions or business recommendations. Commercial acceptance still depends on the intended audience, actual customer data and brand requirements; passing tests alone is not a commercial-quality certificate. Public deployment retains the authentication, authorization, gateway and resource-control requirements documented in SECURITY.md. One upstream Starlette warning about the httpx TestClient adapter remains; it does not fail the suite.

No push or production deployment was performed.
