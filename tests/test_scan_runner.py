import pytest
from unittest.mock import patch, AsyncMock
from core.scan_runner import scan_one_site


@pytest.mark.asyncio
async def test_scan_one_site_success():
    fake_scan_data = {
        "status": {
            "status_code": 200,
            "title": "Example",
            "description": "desc",
            "duration_ms": 123,
            "error": None,
        },
        "ip": "1.2.3.4",
        "geo": {"country": "UA", "city": "Kyiv", "org": "Org", "error": None},
        "cert": {"ssl_days_left": 90, "valid": True, "error": None},
        "number_of_links": 5,
        "links": {"error": None, "broken_links": []},
    }

    with patch("core.scan_runner.analyze", new=AsyncMock(return_value=fake_scan_data)) as mock_analyze, \
         patch("core.scan_runner.save_scan") as mock_save_scan, \
         patch("core.scan_runner.save_links") as mock_save_links:

        mock_save_scan.return_value = {"success": True, "scan_id": 42, "error": None}

        await scan_one_site("https://example.com", site_id=1)

        mock_analyze.assert_awaited_once_with("https://example.com")
        mock_save_scan.assert_called_once_with("https://example.com", fake_scan_data, 1)
        mock_save_links.assert_called_once_with(42, fake_scan_data["links"])


@pytest.mark.asyncio
async def test_scan_one_site_save_scan_fails():
    fake_scan_data = {"links": {"broken_links": []}}

    with patch("core.scan_runner.analyze", new=AsyncMock(return_value=fake_scan_data)), \
         patch("core.scan_runner.save_scan") as mock_save_scan, \
         patch("core.scan_runner.save_links") as mock_save_links, \
         patch("core.scan_runner.logger") as mock_logger:

        mock_save_scan.return_value = {"success": False, "error": "db_insert_failed", "scan_id": None}

        await scan_one_site("https://example.com", site_id=1)

        mock_save_links.assert_not_called()
        mock_logger.error.assert_called_once()