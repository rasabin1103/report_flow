"""A disposable process per job gives a real, enforceable processing deadline."""

import multiprocessing as mp
import time
from multiprocessing.connection import Connection

from app.core.settings import ReportError, Settings


def _entry(connection: Connection, args: tuple):
    try:
        from app.services.reports import execute

        result = execute(*args)
        connection.send((True, result))
    except ReportError as exc:
        connection.send((False, (str(exc), exc.status)))
    except Exception:  # noqa: BLE001 - sanitize untrusted parser errors at the boundary
        connection.send((False, ("Report processing failed; check dataset and configuration", 422)))
    finally:
        connection.close()


def run_job(
    action: str,
    data: bytes,
    filename: str,
    raw: str | None = None,
    options: dict | None = None,
    settings: Settings | None = None,
):
    settings = settings or Settings()
    context = mp.get_context("spawn")
    receiving, sending = context.Pipe(duplex=False)
    process = context.Process(target=_entry, args=(sending, (action, data, filename, raw, options, settings)))
    deadline = time.monotonic() + settings.timeout_seconds
    try:
        process.start()
        sending.close()
        while time.monotonic() < deadline:
            if receiving.poll(min(0.05, max(0, deadline - time.monotonic()))):
                try:
                    ok, payload = receiving.recv()
                except EOFError:
                    raise ReportError("Report worker stopped unexpectedly", 503) from None
                if not ok:
                    raise ReportError(*payload)
                return payload
            if not process.is_alive():
                raise ReportError("Report worker stopped unexpectedly", 503)
        raise ReportError("Processing time limit exceeded", 504)
    finally:
        receiving.close()
        sending.close()
        if process.pid is not None:
            process.join(timeout=0.2)
            if process.is_alive():
                process.terminate()
                process.join(timeout=2)
            if process.is_alive():
                process.kill()
                process.join()
            process.close()
