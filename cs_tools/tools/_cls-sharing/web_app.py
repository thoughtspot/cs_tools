from typing import List
import pathlib

from pydantic import BaseModel
from starlette.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, Request, Body
import typer


HERE = pathlib.Path(__file__).parent


_scoped = {}
web_app = FastAPI()
web_app.mount('/static', StaticFiles(directory=f'{HERE}/static'), name='static')
web_app.mount('/new', StaticFiles(directory=f'{HERE}/static2'), name='static2')
templates = Jinja2Templates(directory=f'{HERE}/static2')


@web_app.on_event('startup')
async def _():
    typer.launch('http://cs_tools.localho.st:5000/new')

#


@web_app.post('/api/defined_permission')
# async def _(request: Request):  # could also do it like this ... how lazy to be?
async def _(type: str=Body(...), guids: List[str]=Body(...)):
    """
    TSGetTablePermissionsRequest
    """
    r = _scoped['api']._security.defined_permission(type=type, id=guids)
    return r.json()


@web_app.get('/api/list_columns/{guid}')
async def _(guid: str):
    """
    TSGetColumnsRequest
    """
    r = _scoped['api']._metadata.list_columns(guid=guid)
    return r.json()


@web_app.get('/api/user_groups')
async def _():
    """
    TSGetUserGroupsRequest
    """
    params = {
        'type': 'USER_GROUP',
        'category': 'ALL',
        'sort': 'DEFAULT',
        'offset': -1,
        'auto_created': False
    }
    r = _scoped['api'].metadata.list_object_headers(**params)
    return r.json()


@web_app.get('/api/tables')
async def _():
    """
    TSGetTablesRequest
    """
    params = {
        'type': 'LOGICAL_TABLE',
        'subtypes': ['ONE_TO_ONE_LOGICAL'],
        'category': 'ALL',
        'sort': 'DEFAULT',
        'offset': -1
    }
    r = _scoped['api'].metadata.list_object_headers(**params)
    return r.json()

#


@web_app.get('/')
async def read_index():
    return RedirectResponse(url='/static/index.html')


@web_app.get('/new', response_class=HTMLResponse)
async def read_index_new(request: Request):
    data = {
        'request': request,
        'host': _scoped['api'].config.thoughtspot.host,
        'user': _scoped['api'].logged_in_user.display_name
    }
    return templates.TemplateResponse('index.html', data)
