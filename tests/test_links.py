import aiohttp
import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from aioresponses import aioresponses
from core import links
from core.links import broken_links, extract_links,check_link,check_links


@pytest.mark.parametrize("exception_to_raise, expected_error", [
    (aiohttp.InvalidURL(url="hdfhdfhu"),"invalid_url"),
    (ValueError,"invalid_url"),

    (aiohttp.ClientConnectorError(connection_key=MagicMock, os_error=OSError()),"connection_failed"),

    (asyncio.TimeoutError,"timeout")
])

async def test_get_exception_returns_error_for_extract_links(mock_aiohttp_get,exception_to_raise,expected_error):

    mock_aiohttp_get.__aenter__.side_effect = exception_to_raise

    result = await extract_links("https://www.google.com")

    assert result["error"] == expected_error
    assert result["links"] is None
    assert result["status"] is None


async def test_extract_links_handles_non_200_status(mock_aiohttp_get):

    mock_aiohttp_get.status = 404

    result = await extract_links("https://www.google.com")

    assert result["status"] == mock_aiohttp_get.status
    assert result["links"] is None
    assert result["error"] is None

@pytest.mark.parametrize("exception_to_raise, expected_error", [
    (aiohttp.ClientConnectorError(
        connection_key=None, os_error=OSError()
    ), "connection_failed"),
    (asyncio.TimeoutError(), "timeout")
])

async def test_check_link_returns_errors(session, exception_to_raise, expected_error):
    with aioresponses() as mock:
        mock.head("https://www.google.com", exception=exception_to_raise)
        response = await check_link(session, "https://www.google.com")

        assert response["error"] == expected_error
        assert response["status"] is None

async def test_check_links_isistance(session):
    with aioresponses() as mock:
        mock.head("https://www.google.com", status=200)
        results = await check_links(["https://www.google.com"])
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["status"] == 200

async def test_broken_links_page_not_found():
    with aioresponses() as mock:
        mock.get("https://www.google.com", status=404)
        results = await broken_links("https://www.google.com")
        assert results["error"] == "Unable to check links — the page returned status code 404"
        assert results["broken_links"] == []
async def test_broken_links_finds_404():
    mock_extracted = {
        "status": 200,
        "error": None,
        "links": ["https://www.google.com/bad-link"]
    }

    with patch("core.links.extract_links", return_value=mock_extracted):
        with aioresponses() as mock:

            mock.head("https://www.google.com/bad-link", status=404)
            results = await broken_links("https://www.google.com")

            assert results["error"] is None
            assert results["total_links"] == 1
            assert len(results["broken_links"]) == 1
            assert results["broken_links"][0]["status"] == 404

@pytest.mark.parametrize("exception_to_raise, expected_error", [
    (aiohttp.InvalidURL(url="hdfhdfhu"), "invalid_url"),
    (ValueError, "invalid_url"),
    (aiohttp.ClientConnectorError(connection_key=MagicMock, os_error=OSError()), "connection_failed"),
    (asyncio.TimeoutError, "timeout")
])
async def test_get_exception_returns_error_for_extract_links(mock_aiohttp_get, exception_to_raise, expected_error):
    mock_aiohttp_get.__aenter__.side_effect = exception_to_raise

    result = await extract_links("https://www.google.com")

    assert result["error"] == expected_error
    assert result["links"] is None
    assert result["status"] is None


async def test_extract_links_handles_non_200_status(mock_aiohttp_get):
    mock_aiohttp_get.status = 404

    result = await extract_links("https://www.google.com")

    assert result["status"] == mock_aiohttp_get.status
    assert result["links"] is None
    assert result["error"] is None

async def test_extract_links_success_returns_set_of_hrefs(mock_aiohttp_get):
    mock_aiohttp_get.status = 200
    mock_aiohttp_get.text = AsyncMock(
        return_value=(
            '<html><body>'
            '<a href="https://www.google.com/a">A</a>'
            '<a href="/relative-b">B</a>'
            '</body></html>'
        )
    )

    result = await extract_links("https://www.google.com")

    assert result["status"] == 200
    assert result["error"] is None
    assert isinstance(result["links"], set)
    assert result["links"] == {"https://www.google.com/a", "/relative-b"}


async def test_extract_links_deduplicates_repeated_hrefs(mock_aiohttp_get):
    mock_aiohttp_get.status = 200
    mock_aiohttp_get.text = AsyncMock(
        return_value=(
            '<html><body>'
            '<a href="https://www.google.com/a">A</a>'
            '<a href="https://www.google.com/a">A again</a>'
            '</body></html>'
        )
    )

    result = await extract_links("https://www.google.com")

    assert result["links"] == {"https://www.google.com/a"}


async def test_extract_links_no_anchors_returns_empty_set(mock_aiohttp_get):
    mock_aiohttp_get.status = 200
    mock_aiohttp_get.text = AsyncMock(return_value="<html><body>No links here</body></html>")

    result = await extract_links("https://www.google.com")

    assert result["status"] == 200
    assert result["error"] is None
    assert result["links"] == set()


async def test_extract_links_ignores_anchors_without_href(mock_aiohttp_get):
    mock_aiohttp_get.status = 200
    mock_aiohttp_get.text = AsyncMock(
        return_value='<html><body><a name="anchor">No href</a></body></html>'
    )

    result = await extract_links("https://www.google.com")

    assert result["links"] == set()


async def test_extract_links_strips_whitespace_from_href(mock_aiohttp_get):
    mock_aiohttp_get.status = 200
    mock_aiohttp_get.text = AsyncMock(
        return_value='<html><body><a href="  https://www.google.com/a  ">A</a></body></html>'
    )

    result = await extract_links("https://www.google.com")

    assert result["links"] == {"https://www.google.com/a"}


@pytest.mark.parametrize("exception_to_raise, expected_error", [
    (aiohttp.ClientConnectorError(connection_key=None, os_error=OSError()), "connection_failed"),
    (asyncio.TimeoutError(), "timeout")
])
async def test_check_link_returns_errors(session, exception_to_raise, expected_error):
    with aioresponses() as mock:
        mock.head("https://www.google.com", exception=exception_to_raise)
        response = await check_link(session, "https://www.google.com")

        assert response["error"] == expected_error
        assert response["status"] is None
        assert response["url"] == "https://www.google.com"


async def test_check_link_success_returns_200(session):
    with aioresponses() as mock:
        mock.head("https://www.google.com", status=200)
        response = await check_link(session, "https://www.google.com")

        assert response["status"] == 200
        assert response["error"] is None
        assert response["url"] == "https://www.google.com"


async def test_check_link_reports_server_error_status(session):
    with aioresponses() as mock:
        mock.head("https://www.google.com", status=500)
        response = await check_link(session, "https://www.google.com")

        assert response["status"] == 500
        assert response["error"] is None

async def test_check_links_isistance(session):
    with aioresponses() as mock:
        mock.head("https://www.google.com", status=200)
        results = await check_links(["https://www.google.com"])
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["status"] == 200


async def test_check_links_multiple_urls_all_processed():
    with aioresponses() as mock:
        mock.head("https://www.google.com/a", status=200)
        mock.head("https://www.google.com/b", status=404)
        mock.head("https://www.google.com/c", status=500)

        results = await check_links([
            "https://www.google.com/a",
            "https://www.google.com/b",
            "https://www.google.com/c",
        ])

    assert len(results) == 3
    statuses = sorted(r["status"] for r in results)
    assert statuses == [200, 404, 500]


async def test_check_links_empty_input_returns_empty_list():
    results = await check_links([])
    assert results == []


async def test_check_links_preserves_order_matching_input_urls():
    with aioresponses() as mock:
        mock.head("https://www.google.com/first", status=200)
        mock.head("https://www.google.com/second", status=404)

        results = await check_links([
            "https://www.google.com/first",
            "https://www.google.com/second",
        ])

    assert [r["url"] for r in results] == [
        "https://www.google.com/first",
        "https://www.google.com/second",
    ]

async def test_broken_links_page_not_found():
    with aioresponses() as mock:
        mock.get("https://www.google.com", status=404)
        results = await broken_links("https://www.google.com")
        assert results["error"] == "Unable to check links — the page returned status code 404"
        assert results["broken_links"] == []
        assert results["total_links"] is None


async def test_broken_links_finds_404():
    mock_extracted = {
        "status": 200,
        "error": None,
        "links": ["https://www.google.com/bad-link"]
    }

    with patch("core.links.extract_links", return_value=mock_extracted):
        with aioresponses() as mock:
            mock.head("https://www.google.com/bad-link", status=404)
            results = await broken_links("https://www.google.com")

            assert results["error"] is None
            assert results["total_links"] == 1
            assert len(results["broken_links"]) == 1
            assert results["broken_links"][0]["status"] == 404


async def test_broken_links_all_healthy_returns_empty_broken_list():
    mock_extracted = {
        "status": 200,
        "error": None,
        "links": {"https://www.google.com/a", "https://www.google.com/b"},
    }

    with patch("core.links.extract_links", return_value=mock_extracted):
        with aioresponses() as mock:
            mock.head("https://www.google.com/a", status=200)
            mock.head("https://www.google.com/b", status=200)

            results = await broken_links("https://www.google.com")

    assert results["error"] is None
    assert results["total_links"] == 2
    assert results["broken_links"] == []


async def test_broken_links_no_links_found_on_page():
    mock_extracted = {"status": 200, "error": None, "links": set()}

    with patch("core.links.extract_links", return_value=mock_extracted):
        results = await broken_links("https://www.google.com")

    assert results["error"] is None
    assert results["total_links"] == 0
    assert results["broken_links"] == []


async def test_broken_links_mixed_statuses_filters_only_broken_ones():
    mock_extracted = {
        "status": 200,
        "error": None,
        "links": {
            "https://www.google.com/ok",
            "https://www.google.com/missing",
            "https://www.google.com/server-error",
        },
    }

    with patch("core.links.extract_links", return_value=mock_extracted):
        with aioresponses() as mock:
            mock.head("https://www.google.com/ok", status=200)
            mock.head("https://www.google.com/missing", status=404)
            mock.head("https://www.google.com/server-error", status=500)

            results = await broken_links("https://www.google.com")

    assert results["error"] is None
    assert results["total_links"] == 3
    broken_statuses = sorted(item["status"] for item in results["broken_links"])
    assert broken_statuses == [404, 500]
    assert len(results["broken_links"]) == 2


async def test_broken_links_relative_hrefs_resolved_to_absolute_before_checking():
    mock_extracted = {
        "status": 200,
        "error": None,
        "links": {"/relative-path"},
    }

    with patch("core.links.extract_links", return_value=mock_extracted):
        with aioresponses() as mock:
            mock.head("https://www.google.com/relative-path", status=200)
            results = await broken_links("https://www.google.com")

    assert results["error"] is None
    assert results["total_links"] == 1
    assert results["broken_links"] == []


async def test_broken_links_propagates_error_from_extract_links():
    mock_extracted = {"status": None, "error": "timeout", "links": None}

    with patch("core.links.extract_links", return_value=mock_extracted):
        results = await broken_links("https://www.google.com")

    assert results["error"] == "timeout"
    assert results["broken_links"] == []
    assert results["total_links"] is None


async def test_broken_links_treats_check_link_exception_as_broken():
    """
    check_links оборачує винятки в результати через asyncio.gather(..., return_exceptions=True),
    тому навіть непередбачений виняток при перевірці одного лінку має потрапити в broken_links,
    а не завалити всю функцію broken_links.
    """
    mock_extracted = {
        "status": 200,
        "error": None,
        "links": {"https://www.google.com/weird"},
    }

    async def fake_check_links(urls):
        return [{"url": urls[0], "status": None, "error": "unexpected_error"}]

    with patch("core.links.extract_links", return_value=mock_extracted), \
         patch("core.links.check_links", side_effect=fake_check_links):
        results = await broken_links("https://www.google.com")

    assert results["error"] is None
    assert results["total_links"] == 1
    assert len(results["broken_links"]) == 1
    assert results["broken_links"][0]["error"] == "unexpected_error"