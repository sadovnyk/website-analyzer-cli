import pytest
from unittest.mock import patch, MagicMock

from core import database


def test_get_connection_uses_env_vars(monkeypatch):
    monkeypatch.setenv("DB_PORT", "3306")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_USER", "root")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    monkeypatch.setenv("DB_NAME", "testdb")

    with patch("core.database.pymysql.connect") as mock_connect:
        database.get_connection()
        mock_connect.assert_called_once_with(
            port=3306,
            host="localhost",
            user="root",
            password="pass",
            database="testdb",
            charset="utf8mb4",
            connect_timeout=5,
        )

def make_scan_data(**overrides):
    data = {
        "status": {
            "status_code": 200,
            "title": "Title",
            "description": "Desc",
            "duration_ms": 100,
            "error": None,
        },
        "ip": "1.2.3.4",
        "geo": {"country": "UA", "city": "Kyiv", "org": "Org", "error": None},
        "cert": {"ssl_days_left": 90, "valid": True, "error": None},
        "number_of_links": 3,
        "links": {"error": None},
    }
    data.update(overrides)
    return data


def test_save_scan_success(mock_connection, mock_cursor):
    mock_cursor.lastrowid = 42
    with patch("core.database.get_connection", return_value=mock_connection):
        result = database.save_scan("https://example.com", make_scan_data(), site_id=1)

    assert result["success"] is True
    assert result["scan_id"] == 42
    assert result["error"] is None
    mock_connection.commit.assert_called_once()
    mock_connection.close.assert_called_once()


def test_save_scan_db_error_rolls_back(mock_connection, mock_cursor):
    mock_cursor.execute.side_effect = Exception("db error")
    with patch("core.database.get_connection", return_value=mock_connection):
        result = database.save_scan("https://example.com", make_scan_data(), site_id=1)

    assert result["success"] is False
    assert result["error"] == "db_insert_failed"
    mock_connection.rollback.assert_called_once()
    mock_connection.commit.assert_not_called()
    mock_connection.close.assert_called_once()


def test_save_scan_connection_always_closed_even_on_connect_failure():
    with patch("core.database.get_connection", side_effect=Exception("no connection")):
        result = database.save_scan("https://example.com", make_scan_data(), site_id=1)

    assert result["success"] is False
    assert result["error"] == "db_insert_failed"

def test_save_links_success(mock_mongo_collection, monkeypatch):
    client, collection = mock_mongo_collection
    monkeypatch.setenv("MONGO_DB", "mydb")
    monkeypatch.setenv("MONGO_CL", "mycol")

    with patch("core.database.pymongo.MongoClient", return_value=client):
        result = database.save_links(42, {"broken_links": ["http://broken.com"]})

    assert result["success"] is True
    assert result["scan_id"] == 42
    collection.insert_one.assert_called_once_with({
        "my_sql_scan_id": 42,
        "broken_links": ["http://broken.com"],
    })


def test_save_links_mongo_error(monkeypatch):
    monkeypatch.setenv("MONGO_DB", "mydb")
    monkeypatch.setenv("MONGO_CL", "mycol")

    with patch("core.database.pymongo.MongoClient", side_effect=Exception("mongo down")):
        result = database.save_links(42, {"broken_links": []})

    assert result["success"] is False
    assert result["error"] == "db_insert_failed"

def test_get_sites_returns_mapped_rows(mock_connection, mock_cursor):
    mock_cursor.fetchall.return_value = [
        (1, "https://a.com", True, 200, "A"),
        (2, "https://b.com", False, None, None),
    ]
    with patch("core.database.get_connection", return_value=mock_connection):
        result = database.get_sites()

    assert result["success"] is True
    assert result["result"] == [
        {"id": 1, "url": "https://a.com", "is_active": True, "status_code": 200, "title": "A"},
        {"id": 2, "url": "https://b.com", "is_active": False, "status_code": None, "title": None},
    ]


def test_get_sites_only_active_adds_where_clause(mock_connection, mock_cursor):
    mock_cursor.fetchall.return_value = []
    with patch("core.database.get_connection", return_value=mock_connection):
        database.get_sites(only_active=True)

    executed_query = mock_cursor.execute.call_args[0][0]
    assert "WHERE sts.is_active = TRUE" in executed_query


def test_get_sites_db_error(mock_connection, mock_cursor):
    mock_cursor.execute.side_effect = Exception("boom")
    with patch("core.database.get_connection", return_value=mock_connection):
        result = database.get_sites()

    assert result["success"] is False
    assert result["error"] == "db_select_failed"
    assert result["result"] == []

def test_add_site_db_success(mock_connection, mock_cursor):
    mock_cursor.lastrowid = 7
    with patch("core.database.get_connection", return_value=mock_connection):
        result = database.add_site_db("https://new.com")

    assert result["success"] is True
    assert result["last_id"] == 7
    mock_cursor.execute.assert_called_once_with(
        "INSERT INTO sites (url) values (%s)", ("https://new.com",)
    )
    mock_connection.commit.assert_called_once()


def test_add_site_db_failure(mock_connection, mock_cursor):
    mock_cursor.execute.side_effect = Exception("insert failed")
    with patch("core.database.get_connection", return_value=mock_connection):
        result = database.add_site_db("https://new.com")

    assert result["success"] is False
    assert result["error"] == "db_insert_failed"
    assert result["last_id"] is None

def test_get_site_details_success(mock_connection, mock_cursor, mock_mongo_collection, monkeypatch):
    monkeypatch.setenv("MONGO_DB", "mydb")
    monkeypatch.setenv("MONGO_CL", "mycol")

    mock_cursor.fetchall.return_value = [
        {
            "site_id": 1, "url": "https://a.com", "is_active": True, "added_at": "2024-01-01",
            "scan_id": 100, "status_code": 200, "title": "T", "description": "D",
            "duration_ms": 50, "status_error": None, "ip": "1.1.1.1", "country": "UA",
            "city": "Kyiv", "org": "Org", "geo_error": None, "ssl_days_left": 30,
            "valid": True, "cert_error": None, "total_links": 5, "links_error": None,
            "scanned_at": "2024-01-02",
        }
    ]

    client, collection = mock_mongo_collection
    collection.find_one.return_value = {"broken_links": ["http://x.com"]}

    with patch("core.database.get_connection", return_value=mock_connection), \
         patch("core.database.pymongo.MongoClient", return_value=client):
        result = database.get_site_details(1)

    assert result["success"] is True
    assert result["site"]["id"] == 1
    assert len(result["scans"]) == 1
    assert result["scans"][0]["scan_id"] == 100
    assert result["scans"][0]["broken_links"] == ["http://x.com"]


def test_get_site_details_site_not_found(mock_connection, mock_cursor):
    mock_cursor.fetchall.return_value = []
    with patch("core.database.get_connection", return_value=mock_connection):
        result = database.get_site_details(999)

    assert result["success"] is False
    assert result["error"] == "site_not_found"
    assert result["site"] is None


def test_get_site_details_no_broken_links_defaults_to_empty_list(
    mock_connection, mock_cursor, mock_mongo_collection, monkeypatch
):
    monkeypatch.setenv("MONGO_DB", "mydb")
    monkeypatch.setenv("MONGO_CL", "mycol")

    mock_cursor.fetchall.return_value = [
        {
            "site_id": 1, "url": "https://a.com", "is_active": True, "added_at": "2024-01-01",
            "scan_id": 100, "status_code": 200, "title": "T", "description": "D",
            "duration_ms": 50, "status_error": None, "ip": "1.1.1.1", "country": "UA",
            "city": "Kyiv", "org": "Org", "geo_error": None, "ssl_days_left": 30,
            "valid": True, "cert_error": None, "total_links": 5, "links_error": None,
            "scanned_at": "2024-01-02",
        }
    ]
    client, collection = mock_mongo_collection
    collection.find_one.return_value = None

    with patch("core.database.get_connection", return_value=mock_connection), \
         patch("core.database.pymongo.MongoClient", return_value=client):
        result = database.get_site_details(1)

    assert result["scans"][0]["broken_links"] == []


def test_get_site_details_db_error(mock_connection, mock_cursor):
    mock_cursor.execute.side_effect = Exception("boom")
    with patch("core.database.get_connection", return_value=mock_connection):
        result = database.get_site_details(1)

    assert result["success"] is False
    assert result["error"] == "db_select_failed"

    def test_delete_site_success(mock_connection, mock_cursor):
        with patch("core.database.get_connection", return_value=mock_connection):
            result = database.delete_site(1)

        assert result["success"] is True
        mock_cursor.execute.assert_called_once_with(
            "DELETE FROM sites WHERE sites.id = %s", (1,)
        )
        mock_connection.commit.assert_called_once()

    def test_delete_site_failure(mock_connection, mock_cursor):
        mock_cursor.execute.side_effect = Exception("fail")
        with patch("core.database.get_connection", return_value=mock_connection):
            result = database.delete_site(1)

        assert result["success"] is False
        assert result["error"] == "db_delete_failed"

def test_toggle_site_active_success(mock_connection, mock_cursor):
    with patch("core.database.get_connection", return_value=mock_connection):
        result = database.toggle_site_active(1)

    assert result["success"] is True
    mock_cursor.execute.assert_called_once_with(
        "UPDATE sites SET is_active = NOT is_active WHERE sites.id = %s", (1,)
    )
    mock_connection.commit.assert_called_once()


def test_toggle_site_active_failure(mock_connection, mock_cursor):
    mock_cursor.execute.side_effect = Exception("fail")
    with patch("core.database.get_connection", return_value=mock_connection):
        result = database.toggle_site_active(1)

    assert result["success"] is False
    assert result["error"] == "db_update_failed"


def test_check_mysql_connection_success(mock_connection):
    with patch("core.database.get_connection", return_value=mock_connection):
        assert database.check_mysql_connection() is True
    mock_connection.ping.assert_called_once_with(reconnect=True)
    mock_connection.close.assert_called_once()


def test_check_mysql_connection_failure():
    with patch("core.database.get_connection", side_effect=Exception("down")):
        assert database.check_mysql_connection() is False

def test_check_mongo_connection_success():
    mock_client = MagicMock()
    with patch("core.database.pymongo.MongoClient", return_value=mock_client):
        assert database.check_mongo_connection() is True
    mock_client.admin.command.assert_called_once_with("ping")
    mock_client.close.assert_called_once()


def test_check_mongo_connection_failure():
    with patch("core.database.pymongo.MongoClient", side_effect=Exception("down")):
        assert database.check_mongo_connection() is False