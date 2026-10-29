import asyncio
from typing import Annotated

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from app.core.settings import ReportError, Settings
from app.schemas.config import Config, Dataset
from app.services.reports import CAPABILITIES, presentation_config
from app.services.worker import run_job

settings = Settings()
app = FastAPI(title="ASE ReportFlow", version="0.1.0")
slots = asyncio.Semaphore(settings.max_concurrent_jobs)


class BodyLimit:
    """Bound the complete multipart request, including chunked transfer bodies."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") in {"GET", "HEAD", "OPTIONS"}:
            return await self.app(scope, receive, send)
        limit = settings.max_file_bytes + 1600000
        total = 0
        chunks = []
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            total += len(chunk)
            if total > limit:
                return await JSONResponse({"detail": "Request size limit exceeded"}, status_code=413)(
                    scope, receive, send
                )
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        sent = False

        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


app.add_middleware(BodyLimit)


@app.exception_handler(ReportError)
async def report_error(request: Request, exc: ReportError):
    return JSONResponse({"detail": str(exc)}, status_code=exc.status)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse({"detail": "Invalid request fields"}, status_code=422)


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    return JSONResponse({"detail": "Internal processing error"}, status_code=500)


async def process(
    action: str,
    file: UploadFile,
    config: str | None = None,
    options: dict | None = None,
    logo: UploadFile | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    cover_style: str | None = None,
):
    try:
        if config is not None:
            logo_bytes = await logo.read(500001) if logo is not None else None
            config = presentation_config(
                config, title=title, subtitle=subtitle, cover_style=cover_style, logo=logo_bytes
            )
        data = await file.read(settings.max_file_bytes + 1)
        if len(data) > settings.max_file_bytes:
            raise ReportError("File size limit exceeded", 413)
        if slots.locked():
            raise ReportError("Service at capacity; retry later", 503)
        async with slots:
            return await run_in_threadpool(
                run_job, action, data, file.filename or "dataset", config, options, settings
            )
    finally:
        await file.close()
        if logo is not None:
            await logo.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/report-capabilities")
def capabilities():
    return CAPABILITIES


@app.get("/api/v1/report-config-schema")
def config_schema():
    return Config.model_json_schema()


@app.post("/api/v1/datasets/inspect")
async def inspect(
    file: Annotated[UploadFile, File()],
    sheet_name: Annotated[str | None, Form()] = None,
    encoding: Annotated[str, Form()] = "utf-8-sig",
    delimiter: Annotated[str | None, Form()] = None,
):
    try:
        options = Dataset.model_validate(
            {"sheet_name": sheet_name, "encoding": encoding, "delimiter": delimiter}
        ).model_dump()
    except ValueError:
        raise ReportError("Invalid encoding or delimiter") from None
    return await process("inspect", file, options=options)


@app.post("/api/v1/reports/validate")
async def validate(
    file: Annotated[UploadFile, File()],
    config: Annotated[str, Form()],
    logo: Annotated[UploadFile | None, File()] = None,
    title: Annotated[str | None, Form()] = None,
    subtitle: Annotated[str | None, Form()] = None,
    cover_style: Annotated[str | None, Form()] = None,
):
    return await process(
        "validate", file, config, logo=logo, title=title, subtitle=subtitle, cover_style=cover_style
    )


@app.post("/api/v1/reports/generate")
async def generate(
    file: Annotated[UploadFile, File()],
    config: Annotated[str, Form()],
    logo: Annotated[UploadFile | None, File()] = None,
    title: Annotated[str | None, Form()] = None,
    subtitle: Annotated[str | None, Form()] = None,
    cover_style: Annotated[str | None, Form()] = None,
):
    data = await process(
        "generate", file, config, logo=logo, title=title, subtitle=subtitle, cover_style=cover_style
    )
    return Response(
        data,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="report.pdf"', "Cache-Control": "no-store"},
    )
