from fastapi.templating import Jinja2Templates
from fastapi import Request, BackgroundTasks, FastAPI, Form
from core.database import get_sites,add_site_db,get_site_details,delete_site
from core.scan_runner import scan_one_site
from starlette.responses import RedirectResponse

app = FastAPI()
templates = Jinja2Templates(directory="web/templates")
@app.get("/")
async def root(request: Request):
    result = get_sites()
    if result["success"] is True:
        return templates.TemplateResponse(request=request,context={"request": request, "sites": result["result"], "error":None}
                                          ,name="index.html")
    else:
        return templates.TemplateResponse(request=request,context={"request": request, "sites": [],"error":result["error"]},
                                          name="index.html")

@app.get("/add-site")
async def add_site(request: Request):
    return templates.TemplateResponse(request=request, name="add_site.html",
                                      context={"request": request, "error":None})


@app.post("/add-site")
async def add_site_post(request: Request,background_tasks: BackgroundTasks,url: str = Form()):
    result = add_site_db(url)
    if result["success"] is True:
        background_tasks.add_task(scan_one_site, url, result["last_id"])
        return RedirectResponse(url="/?scanning=1", status_code=303)
    else:
        return templates.TemplateResponse(request=request, name="add_site.html",
                                          context={"request": request, "error": result["error"]})

@app.get("/site/{site_id}")
async def site_detail(request: Request, site_id: int):
    result = get_site_details(site_id)
    if result["success"] is True:
        return templates.TemplateResponse(request=request,name="site_detail.html",
                                          context={"request": request, "site":result["site"],"scans":result["scans"], "error":result["error"]})
    else:
        return templates.TemplateResponse(request=request,name="site_detail.html",
                                          context={"request": request, "site": None, "error":result["error"],"scans":[]})

@app.post("/site/{site_id}/delete")
async def delete_site_route(request: Request, site_id: int):
    result = delete_site(site_id)
    if result["success"] is True:
        return RedirectResponse(url="/", status_code=303)
    else:
        old_result = get_sites()
        return templates.TemplateResponse(request=request,name="index.html",context={"request": request,"sites": old_result["result"], "error": result["error"]})