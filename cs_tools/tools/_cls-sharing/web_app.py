import pathlib
import os

from starlette.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, Request


HERE = pathlib.Path(__file__).parent


web_app = FastAPI()
web_app.mount('/static', StaticFiles(directory=f'{HERE}/static'), name='static')
web_app.mount('/new', StaticFiles(directory=f'{HERE}/static2'), name='static2')
templates = Jinja2Templates(directory=f'{HERE}/static2')


@web_app.get('/')
async def read_index():
    return RedirectResponse(url='/static/index.html')


@web_app.get('/new', response_class=HTMLResponse)
async def read_index_new(request: Request):
    data = {
        'request': request,
        'host': os.environ['TS_HOST'],
        'user': os.environ['TS_USER']
    }
    return templates.TemplateResponse('index.html', data)
