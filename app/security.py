import base64
import io
import warnings

from PIL import Image, ImageOps

from app.core.settings import ReportError


def decode_logo(encoded: str | None) -> bytes | None:
    if encoded is None:
        return None
    try:
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) > 500000:
            raise ValueError
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as image:
                if image.format not in {"PNG", "JPEG"} or not (
                    1 <= image.width <= 2000 and 1 <= image.height <= 2000
                ):
                    raise ValueError
                image.load()
                safe = io.BytesIO()
                oriented = ImageOps.exif_transpose(image)
                mode = "RGBA" if oriented.mode in {"RGBA", "LA"} or "transparency" in oriented.info else "RGB"
                converted = oriented.convert(mode)
                # Reconstruct pixels so metadata is not carried into the report.
                Image.frombytes(mode, converted.size, converted.tobytes()).save(safe, format="PNG")
                return safe.getvalue()
    except Exception:  # noqa: BLE001 - sanitize untrusted parser errors at the boundary
        raise ReportError("Logo must be base64 PNG/JPEG, at most 500 KB and 2000 x 2000 pixels") from None
