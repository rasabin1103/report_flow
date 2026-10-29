# API v1
All dataset operations accept multipart file uploads. HTTP consumers never provide input/output paths. Responses are not persisted.

| Method | Path | Fields / response |
|---|---|---|
| GET | `/health` | `{"status":"ok"}`; liveness, not a full worker readiness probe |
| GET | `/api/v1/report-capabilities` | formats, aggregations, charts, operators, templates, schema version |
| GET | `/api/v1/report-config-schema` | authoritative Pydantic JSON schema |
| POST | `/api/v1/datasets/inspect` | `file`; optional `sheet_name`, `encoding`, `delimiter`; counts, types, nulls, distinct values, first five rows, warnings |
| POST | `/api/v1/reports/validate` | `file`, `config` JSON string; `valid`, loaded/analyzed record counts, selected columns, warnings |
| POST | `/api/v1/reports/generate` | `file`, `config` JSON string; HTTP 200 `application/pdf`, attachment `report.pdf`, `Cache-Control: no-store` |

Validation rejects invalid requests with 422 and a sanitized `detail`. Size/dimension/page/expansion violations return 413; processing deadline 504; capacity or unexpected worker death 503. Unhandled server failures return a generic 500. Validation failures use non-2xx rather than `valid:false`. Validation checks data/configuration compatibility but does not lay out pages; rendering can subsequently exceed page limits. Inspect samples can contain sensitive data: authorize access at your gateway.

`config` is a form field, not a JSON file upload. Inspection uses form fields; generation/validation put parsing options under `dataset` in the configuration. Supported encodings: UTF-8, UTF-8 with BOM, Latin-1 and CP1252. Delimiter is a single character; detection considers comma, semicolon, tab and pipe.

A complete HTTP request is capped at the file limit plus 1.6 MB for configuration and multipart overhead. Reverse proxies should also cap request bodies and enforce upload deadlines. Synchronous jobs have a strict processing deadline after upload/parsing admission; network upload deadlines belong at the gateway.

## Presentation uploads and overrides
Both report endpoints accept optional multipart `logo` (PNG/JPEG file), `title`, `subtitle`, and `cover_style` (`compact` or `full`). Config remains a required JSON form field. Explicit presentation form fields override the corresponding JSON fields. A logo upload overrides branding.logo_base64; no filename or filesystem path is read from JSON. Images are decoded/validated, constrained to 500,000 bytes and 2000 pixels per dimension, and re-encoded without metadata while retaining alpha transparency. Oversized logos return 413; empty or invalid images return 422. Upload handles close on success and failure.

JSON report metadata also supports prepared_for, reporting_period, document_reference and confidentiality. See BRANDING.md for complete examples.
