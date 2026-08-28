from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi import Request
from core.database import get_sites,add_site_db
from fastapi import Form
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
async def add_site_post(request: Request,url: str = Form()):
    result = add_site_db(url)
    if result["success"] is True:
        return RedirectResponse(url="/", status_code=303)
    else:
        return templates.TemplateResponse(request=request, name="add_site.html",
                                          context={"request": request, "error": result["error"]},)
