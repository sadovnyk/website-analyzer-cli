import pytest
from unittest.mock import patch, MagicMock
from starlette.testclient import TestClient
from urllib.parse import quote
from web.main import app, add_site_post

from starlette.requests import Request
client = TestClient(app)


@pytest.fixture
def mock_template_response():
    from starlette.responses import Response

    def fake_template_response(request=None, name=None, context=None, **kwargs):
        resp = Response(content=f"rendered:{name}", status_code=200)
        resp.template_name = name
        resp.template_context = context
        return resp

    with patch("web.main.templates.TemplateResponse", side_effect=fake_template_response) as mock_tr:
        yield mock_tr


def test_root_success_renders_index_with_sites(mock_template_response):
    sites = [{"id": 1, "url": "https://a.com", "is_active": True, "status_code": 200, "title": "A"}]
    with patch("web.main.get_sites", return_value={"success": True, "error": None, "result": sites}):
        response = client.get("/")

    assert response.status_code == 200
    call_kwargs = mock_template_response.call_args.kwargs
    assert call_kwargs["name"] == "index.html"
    assert call_kwargs["context"]["sites"] == sites
    assert call_kwargs["context"]["error"] is None


def test_root_db_failure_renders_index_with_error(mock_template_response):
    with patch("web.main.get_sites", return_value={"success": False, "error": "db_select_failed", "result": []}):
        response = client.get("/")

    assert response.status_code == 200
    call_kwargs = mock_template_response.call_args.kwargs
    assert call_kwargs["context"]["sites"] == []
    assert call_kwargs["context"]["error"] == "Temporary database issues. Please refresh the page."

def test_add_site_get_renders_form(mock_template_response):
    response = client.get("/add-site")

    assert response.status_code == 200
    call_kwargs = mock_template_response.call_args.kwargs
    assert call_kwargs["name"] == "add_site.html"
    assert call_kwargs["context"]["error"] is None


def test_add_site_post_failure_renders_form_with_error(mock_template_response):
    with patch("web.main.add_site_db", return_value={"success": False, "error": "db_insert_failed", "last_id": None}), \
         patch("web.main.scan_one_site") as mock_scan_one_site:

        response = client.post("/add-site", data={"url": "https://bad.com"})

    assert response.status_code == 200
    call_kwargs = mock_template_response.call_args.kwargs
    assert call_kwargs["name"] == "add_site.html"
    assert call_kwargs["context"]["error"] == "The data could not be saved. Please try again in a few minutes."
    mock_scan_one_site.assert_not_called()


def test_add_site_post_missing_url_returns_422():
    response = client.post("/add-site", data={})
    assert response.status_code == 422


def test_add_site_post_url_is_properly_quoted_in_redirect(mock_template_response):
    test_url = "https://example.com/path?query=1&other=2"
    with patch("web.main.add_site_db", return_value={"success": True, "error": None, "last_id": 1}), \
         patch("web.main.scan_one_site"):

        response = client.post("/add-site", data={"url": test_url}, follow_redirects=False)

    expected_location = f"/?scanning=1&url={quote(test_url)}"
    assert response.headers["location"] == expected_location


def test_site_detail_success_renders_with_reversed_chart_data(mock_template_response):
    scans = [{"scan_id": 1}, {"scan_id": 2}, {"scan_id": 3}]
    result = {
        "success": True,
        "error": None,
        "site": {"id": 5, "url": "https://a.com"},
        "scans": scans,
    }
    with patch("web.main.get_site_details", return_value=result):
        response = client.get("/site/5")

    assert response.status_code == 200
    call_kwargs = mock_template_response.call_args.kwargs
    assert call_kwargs["name"] == "site_detail.html"
    assert call_kwargs["context"]["site"] == {"id": 5, "url": "https://a.com"}
    assert call_kwargs["context"]["scans"] == scans
    assert call_kwargs["context"]["chart_scans"] == list(reversed(scans))


def test_site_detail_not_found_renders_empty_state(mock_template_response):
    result = {"success": False, "error": "site_not_found", "site": None, "scans": []}
    with patch("web.main.get_site_details", return_value=result):
        response = client.get("/site/999")

    assert response.status_code == 200
    call_kwargs = mock_template_response.call_args.kwargs
    assert call_kwargs["context"]["site"] is None
    assert call_kwargs["context"]["error"] == "That page was not found."
    assert call_kwargs["context"]["scans"] == []
    assert call_kwargs["context"]["chart_scans"] == []


def test_site_detail_invalid_id_type_returns_422():
    response = client.get("/site/not-a-number")
    assert response.status_code == 422

def test_delete_site_success_redirects_home():
    with patch("web.main.delete_site", return_value={"success": True, "error": None}):
        response = client.post("/site/5/delete", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_delete_site_failure_renders_index_with_error(mock_template_response):
    sites = [{"id": 1, "url": "https://a.com"}]
    with patch("web.main.delete_site", return_value={"success": False, "error": "db_delete_failed"}), \
         patch("web.main.get_sites", return_value={"success": True, "error": None, "result": sites}):

        response = client.post("/site/5/delete")

    assert response.status_code == 200
    call_kwargs = mock_template_response.call_args.kwargs
    assert call_kwargs["name"] == "index.html"
    assert call_kwargs["context"]["error"] == "The site could not be deleted. Please try again."
    assert call_kwargs["context"]["sites"] == sites


def test_toggle_site_success_redirects_home():
    with patch("web.main.toggle_site_active", return_value={"success": True, "error": None}):
        response = client.post("/site/5/toggle", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_toggle_site_failure_renders_index_with_error(mock_template_response):
    sites = [{"id": 2, "url": "https://b.com"}]
    with patch("web.main.toggle_site_active", return_value={"success": False, "error": "db_update_failed"}), \
         patch("web.main.get_sites", return_value={"success": True, "error": None, "result": sites}):

        response = client.post("/site/5/toggle")

    assert response.status_code == 200
    call_kwargs = mock_template_response.call_args.kwargs
    assert call_kwargs["context"]["error"] == "The site status could not be updated. Please try again."
    assert call_kwargs["context"]["sites"] == sites


@pytest.mark.asyncio
async def test_add_site_post_returns_template_on_url_error():
    module_path = add_site_post.__module__

    mock_request = MagicMock(spec=Request)
    mock_bg_tasks = MagicMock()
    raw_url = "invalid_url_string"
    expected_error = "invalid_scheme"
    user_error_text = "Not correct protocol of URL"

    with patch(f"{module_path}.get_normalized_url") as mock_normalize, \
            patch(f"{module_path}.get_user_message", return_value=user_error_text) as mock_msg, \
            patch(f"{module_path}.templates.TemplateResponse") as mock_template_response:
        mock_normalize.return_value = {"url": None, "error": expected_error}

        # 3. Виклик функції
        response = await add_site_post(
            request=mock_request,
            background_tasks=mock_bg_tasks,
            url=raw_url,
        )

        mock_normalize.assert_called_once_with(raw_url)
        mock_msg.assert_called_once_with(expected_error)

        mock_template_response.assert_called_once_with(
            request=mock_request,
            name="add_site.html",
            context={"request": mock_request, "error": user_error_text},
        )
        assert response == mock_template_response.return_value

def test_healthz_all_up_returns_200():
    with patch("web.main.check_mysql_connection", return_value=True), \
         patch("web.main.check_mongo_connection", return_value=True):

        response = client.get("/healthz")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "up"
    assert data["components"]["mysql"] == "ok"
    assert data["components"]["mongo"] == "ok"


def test_healthz_mysql_down_returns_503():
    with patch("web.main.check_mysql_connection", return_value=False), \
         patch("web.main.check_mongo_connection", return_value=True):

        response = client.get("/healthz")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "down"
    assert data["components"]["mysql"] == "down"
    assert data["components"]["mongo"] == "ok"


def test_healthz_mongo_down_returns_503():
    with patch("web.main.check_mysql_connection", return_value=True), \
         patch("web.main.check_mongo_connection", return_value=False):

        response = client.get("/healthz")

    assert response.status_code == 503
    data = response.json()
    assert data["components"]["mysql"] == "ok"
    assert data["components"]["mongo"] == "down"


def test_healthz_both_down_returns_503():
    with patch("web.main.check_mysql_connection", return_value=False), \
         patch("web.main.check_mongo_connection", return_value=False):

        response = client.get("/healthz")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "down"
    assert data["components"]["mysql"] == "down"
    assert data["components"]["mongo"] == "down"

@patch("web.main.toggle_site_pin")
def test_pin_route_success_redirects_home(mock_toggle):
    mock_toggle.return_value = {"success": True, "error": None}

    response = client.post("/site/1/pin", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    mock_toggle.assert_called_once_with(1)


@patch("web.main.get_sites")
@patch("web.main.toggle_site_pin")
def test_pin_route_failure_renders_index_with_error(mock_toggle, mock_get_sites):
    mock_toggle.return_value = {"success": False, "error": "site_not_found"}
    mock_get_sites.return_value = {"success": True, "result": []}

    response = client.post("/site/999/pin", follow_redirects=False)

    assert response.status_code == 200
    assert "Error" in response.text


@patch("web.main.toggle_site_pin")
def test_pin_route_toggles_twice(mock_toggle):
    mock_toggle.return_value = {"success": True, "error": None}

    response1 = client.post("/site/5/pin", follow_redirects=False)
    assert response1.status_code == 303

    response2 = client.post("/site/5/pin", follow_redirects=False)
    assert response2.status_code == 303

    assert mock_toggle.call_count == 2