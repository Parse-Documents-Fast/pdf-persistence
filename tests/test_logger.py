import io
import json
import logging
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from pdf_persistence.db import get_db
from pdf_persistence.logger import JsonFormatter, setup_logging


def test_json_formatter_structure():
    formatter = JsonFormatter(service="pdf-persistence")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="test message",
        args=(),
        exc_info=None,
    )
    record.fields = {"pdf_id": "12345", "checksum": "abc"}

    output = formatter.format(record)
    data = json.loads(output)

    assert data["service"] == "pdf-persistence"
    assert data["level"] == "INFO"
    assert data["msg"] == "test message"
    assert data["pdf_id"] == "12345"
    assert data["checksum"] == "abc"
    assert "time" in data
    assert data["time"].endswith("Z")


def test_json_formatter_warn_mapping():
    formatter = JsonFormatter(service="pdf-persistence")
    record = logging.LogRecord(
        name="test",
        level=logging.WARNING,
        pathname="test.py",
        lineno=10,
        msg="warning occurred",
        args=(),
        exc_info=None,
    )

    output = formatter.format(record)
    data = json.loads(output)
    assert data["level"] == "WARN"


def test_setup_logging_invalid_level():
    effective = setup_logging("INVALID_LEVEL_NAME")
    assert effective == "INFO"


def test_setup_logging_level_filtering():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter(service="pdf-persistence"))

    root = logging.getLogger()
    old_handlers = root.handlers
    old_level = root.level
    try:
        root.handlers = [handler]
        root.setLevel(logging.INFO)

        logger = logging.getLogger("test_filtering")
        logger.debug("should not appear")
        logger.info("should appear")

        lines = [
            json.loads(line)
            for line in stream.getvalue().strip().split("\n")
            if line.strip()
        ]
        assert len(lines) == 1
        assert lines[0]["msg"] == "should appear"
    finally:
        root.handlers = old_handlers
        root.setLevel(old_level)


@pytest.mark.asyncio
async def test_middleware_logging():
    from unittest.mock import patch

    from pdf_persistence.main import app

    app.dependency_overrides[get_db] = lambda: AsyncMock()
    try:
        with patch(
            "pdf_persistence.api.list_documents", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = []
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/documents")
                assert resp.status_code == 200
    finally:
        app.dependency_overrides.pop(get_db, None)
