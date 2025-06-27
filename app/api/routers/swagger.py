from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.status import HTTP_401_UNAUTHORIZED

from app.core.config import settings

__all__ = ["router"]

router = APIRouter()
security = HTTPBasic()


@router.get(
    "/docs",
    include_in_schema=False,
    response_class=HTMLResponse,
)
async def get_docs() -> HTMLResponse:
    from app.api.routers.main_router import router

    return get_swagger_ui_html(openapi_url=f"{router.prefix}/openapi.json", title="Control System API Swagger")


@router.get("/redoc", include_in_schema=False, response_class=Response)
async def get_redoc() -> HTMLResponse:
    from app.api.routers.main_router import router

    return get_redoc_html(
        openapi_url=f"{router.prefix}/openapi.json", title="Control System Redoc", with_google_fonts=True
    )


@router.get(
    "/openapi.json",
    include_in_schema=False,
    response_class=JSONResponse,
)
async def get_openapi_json(creds: HTTPBasicCredentials = Depends(security)) -> JSONResponse:
    from app.api.routers.main_router import router

    if creds.username != settings.swagger.USERNAME or creds.password != settings.swagger.PASSWORD:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)

    openapi_schema = get_openapi(version="1.0.0", title="Control System OpenApi", routes=router.routes)
    return JSONResponse(openapi_schema)
