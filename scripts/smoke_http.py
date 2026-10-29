"""Exercise a running local service with standard-library multipart requests."""

import json
import os
import urllib.request

BASE = os.environ.get("REPORTFLOW_SMOKE_URL", "http://127.0.0.1:8000")


def request(path, data=None, headers=None):
    with urllib.request.urlopen(
        urllib.request.Request(BASE + path, data=data, headers=headers or {}), timeout=70
    ) as response:
        return response.status, response.headers, response.read()


def main():
    assert json.loads(request("/health")[2])["status"] == "ok"
    boundary = "reportflow-smoke-boundary"
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="sample.csv"\r\nContent-Type: text/csv\r\n\r\n'
        "name,amount\nAlpha,10\nBeta,20\n"
        f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="config"\r\n\r\n'
        '{"report":{"title":"Container smoke report"},"kpis":[{"id":"total","label":"Total","operation":"sum","column":"amount"}]}'
        f"\r\n--{boundary}--\r\n"
    ).encode()
    for endpoint in ["datasets/inspect", "reports/validate", "reports/generate"]:
        status, headers, data = request(
            "/api/v1/" + endpoint, body, {"Content-Type": "multipart/form-data; boundary=" + boundary}
        )
        assert status == 200
        if endpoint.endswith("generate"):
            assert data.startswith(b"%PDF-")
            assert headers["Content-Type"] == "application/pdf"
        print(endpoint, "OK", len(data), "bytes")


if __name__ == "__main__":
    main()
