# Architecture
The transport-independent pipeline is `ingestion.loader -> transformations.engine -> analytics.metrics -> charts.renderer / reporting.renderer`. `services.reports.execute` composes these steps and can be called directly from Python without FastAPI. Pydantic models reject unknown keys and define the versioned public schema.

API and CLI both call `services.worker.run_job`. Each job gets a disposable spawned process and a one-way IPC pipe. The parent drains results before joining, enforces a wall-clock deadline, and terminates and joins workers on every exit path. API admission uses a per-process concurrency semaphore and returns 503 when busy. There is no queue or background persistence.

Uploads are bounded before parsing. CSV rows are checked before DataFrame construction. XLSX uses read-only, data-only OpenPyXL, checks ZIP expansion totals and worksheet dimensions, and closes the workbook. Data is held only for the current job. Starlette may spool multipart files temporarily; upload handles are closed after processing. Reports and logos use memory buffers. Matplotlib may create its normal font cache; it contains no dataset content.

PDFs use ReportLab Platypus, embedded DejaVu Sans, repeating table headers, splitting rows and page callbacks. Two templates share the editorial system in reporting/design.py; detailed uses more spacious tables and charts. reporting/localization.py owns vocabulary and locale-independent formatting. analytics/observations.py generates deterministic descriptive findings from complete groupings. A multi-pass build resolves optional table-of-contents page references. No browser or LibreOffice is involved.

Limits bound resource usage, but Python workers do not impose a portable per-process hard RSS limit. Use container/cgroup memory and CPU controls in deployment. Each web process has its own concurrency capacity; size total capacity accordingly.
