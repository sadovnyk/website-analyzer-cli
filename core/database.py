from dotenv import load_dotenv
import os
import pymysql
import pymongo

load_dotenv()
def get_connection():
    return pymysql.connect(port=int(os.environ.get("DB_PORT")) ,host=os.environ.get("DB_HOST"),user=os.environ.get("DB_USER"),password=os.environ.get("DB_PASSWORD"),database=os.environ.get("DB_NAME"),charset="utf8mb4")

def save_scan(url,data,site_id):
    access = {
        "success": False,
        "error": None,
        "scan_id": None
    }
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            query = (
                "INSERT INTO scans (url, status_code, title, description, duration_ms, "
                "status_error, ip, country, city, org, geo_error, ssl_days_left, valid, cert_error, total_links, links_error,site_id) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)"
            )
            values = (
                url,
                data["status"]["status_code"],
                data["status"]["title"],
                data["status"]["description"],
                data["status"]["duration_ms"],
                data["status"]["error"],
                data["ip"],
                data["geo"]["country"],
                data["geo"]["city"],
                data["geo"]["org"],
                data["geo"]["error"],
                data["cert"]["ssl_days_left"],
                data["cert"]["valid"],
                data["cert"]["error"],
                data["number_of_links"],
                data["links"]["error"],
                site_id
            )
            cursor.execute(query, values)
            access["scan_id"] = cursor.lastrowid
        connection.commit()
        access["success"] = True

    except Exception as e:
        access["error"] = "db_insert_failed"
        connection.rollback()

    finally:
        connection.close()

    return access

def save_links(scan_id,links_data):
    access = {
        "success": False,
        "error": None,
        "scan_id": scan_id
    }

    my_document = {
        "my_sql_scan_id": scan_id,
        "broken_links": links_data["broken_links"]
    }

    try:
        with pymongo.MongoClient(os.environ.get("MONGO_URI")) as client:
            db = os.environ.get("MONGO_DB")
            collection = os.environ.get("MONGO_CL")
            client[db][collection].insert_one(my_document)
            access["success"] = True
    except Exception as e:
        access["error"] = "db_insert_failed"

    return access


def get_sites(only_active = False):
    access = {
        "success": False,
        "error": None,
        "result": []
    }

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            base_query = """
                         SELECT sts.id, sts.url, sts.is_active, scs.status_code, scs.title
                         FROM sites sts
                                  LEFT JOIN scans scs ON sts.id = scs.site_id
                             AND scs.id = (SELECT MAX(id) \
                                           FROM scans sub_scs \
                                           WHERE sub_scs.site_id = sts.id) \
                         """

            if only_active:
                query = base_query + " WHERE sts.is_active = TRUE"
            else:
                query = base_query
            cursor.execute(query)
            rows = cursor.fetchall()
            for row in rows:
                site_dict = {
                    "id": row[0],
                    "url": row[1],
                    "is_active": row[2],
                    "status_code": row[3],
                    "title": row[4]
                }
                access["result"].append(site_dict)

        access["success"] = True
    except Exception as e:
        access["error"] = "db_select_failed"
    finally:
        connection.close()

    return access

def add_site_db(url):
    access = {
        "success": False,
        "error": None
    }
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            query = ("INSERT INTO sites (url) values (%s)")
            values = (url,)
            cursor.execute(query, values)
            access["success"] = True
            connection.commit()
    except Exception as e:
        access["error"] = "db_insert_failed"
    finally:
        connection.close()

    return access