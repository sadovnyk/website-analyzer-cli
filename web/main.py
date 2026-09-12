from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Request, BackgroundTasks, FastAPI, Form, Response, status
from core.database import get_sites,add_site_db,get_site_details,delete_site,toggle_site_active,check_mysql_connection,check_mongo_connection, toggle_site_pin
from core.scan_runner import scan_one_site
from starlette.responses import RedirectResponse
from urllib.parse import quote
from web.errors import get_user_message
from core.security import get_normalized_url

max_active_scan_links = 5
max_total_scan_links = 50
app = FastAPI()
templates = Jinja2Templates(directory="web/templates")
app.mount("/static", StaticFiles(directory="web/static"), name="static")
@app.get("/")
async def root(request: Request):
    result = get_sites()
    if result["success"] is True:
        return templates.TemplateResponse(request=request,context={"request": request, "sites": result["result"], "error": None}
                                          ,name="index.html")
    else:
        return templates.TemplateResponse(request=request,context={"request": request, "sites": [],"error": get_user_message(result["error"])},
                                          name="index.html")

@app.get("/add-site")
async def add_site(request: Request):
    return templates.TemplateResponse(request=request, name="add_site.html",
                                      context={"request": request, "error": None})


@app.post("/add-site")
async def add_site_post(request: Request,background_tasks: BackgroundTasks,url: str = Form()):
    dict_url = get_normalized_url(url)
    if dict_url["error"] is not None:
        error_message = dict_url["error"]
        return templates.TemplateResponse(request=request, name="add_site.html",
                                          context={"request": request, "error": get_user_message(error_message)})
    checked_url = dict_url["url"]
    all_sites = get_sites()
    if len(all_sites["result"]) >= max_total_scan_links:
        return templates.TemplateResponse(request=request, name="add_site.html",
                                          context={"request": request, "error": get_user_message("total_links_reached")})
    active_sites = get_sites(only_active=True)
    if len(active_sites["result"]) >= max_active_scan_links:
        return templates.TemplateResponse(request=request, name="add_site.html",
                                          context={"request": request, "error": get_user_message("total_active_links_reached")})
    result = add_site_db(checked_url)
    if result["success"] is True:
        background_tasks.add_task(scan_one_site, checked_url, result["last_id"])
        return RedirectResponse(url=f"/?scanning=1&url={quote(checked_url)}", status_code=303)
    else:
        return templates.TemplateResponse(request=request, name="add_site.html",
                                          context={"request": request, "error": result["error"]})

@app.get("/site/{site_id}")
async def site_detail(request: Request, site_id: int):
    result = get_site_details(site_id)
    if result["success"] is True:
        chart_data = list(reversed(result["scans"]))
        return templates.TemplateResponse(request=request,name="site_detail.html",
                                          context={"request": request, "site":result["site"],"scans":result["scans"],"chart_scans": chart_data, "error": None})
    else:
        return templates.TemplateResponse(request=request,name="site_detail.html",
                                          context={"request": request, "site": None, "error": get_user_message(result["error"]),"scans":[],"chart_scans": []})

@app.post("/site/{site_id}/delete")
async def delete_site_route(request: Request, site_id: int):
    result = delete_site(site_id)
    if result["success"] is True:
        return RedirectResponse(url="/", status_code=303)
    else:
        old_result = get_sites()
        return templates.TemplateResponse(request=request,name="index.html",context={"request": request,"sites": old_result["result"], "error": get_user_message(result["error"])})

@app.post("/site/{site_id}/toggle")
async def toggle_site(request: Request, site_id: int):
    result = toggle_site_active(site_id)
    if result["success"] is True:
        return RedirectResponse(url="/", status_code=303)
    else:
        old_result = get_sites()
        return templates.TemplateResponse(request=request,name="index.html",context={"request": request,"sites": old_result["result"], "error": get_user_message(result["error"])})

@app.get("/healthz")
async def health(response: Response):
    mysql_ok = check_mysql_connection()
    mongo_ok = check_mongo_connection()
    result = {
        "status": "up",
        "components": {
            "mysql": "ok" if mysql_ok else "down",
            "mongo": "ok" if mongo_ok else "down",
        }
    }


    if not mysql_ok or not mongo_ok:
        result["status"] = "down"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return result

@app.post("/site/{site_id}/pin")
async def pin_site(request: Request, site_id: int):
    result = toggle_site_pin(site_id)
    if result["success"] is True:
        return RedirectResponse(url="/", status_code=303)
    else:
        old_result = get_sites()
        return templates.TemplateResponse(
            request=request, name="index.html",
            context={"request": request, "sites": old_result["result"], "error": get_user_message(result["error"])}
        )