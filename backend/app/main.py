import logging
from contextlib import asynccontextmanager
from threading import Event, Thread
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from .config import get_settings
from .database import init_db
from .api.routes import detecciones, eventos, alertas, estadisticas, salud, monitoreo, geografia, informes
from .services import live_firms


@asynccontextmanager
async def lifespan(app):
    if get_settings().database_enabled:
        try:
            init_db()
        except SQLAlchemyError:
            logging.getLogger('tunari').warning('PostGIS no disponible al iniciar; /salud responderá 503 hasta recuperar la conexión')
    stop = Event()
    if get_settings().live_monitoring_enabled and not get_settings().database_enabled:
        Thread(target=live_firms.run, args=(stop,), daemon=True).start()
    try:
        yield
    finally:
        stop.set()


app = FastAPI(title='Tunari Fire Monitor', version='1.0.0', lifespan=lifespan)
settings = get_settings()
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins.split(','),
                   allow_methods=['GET', 'PATCH', 'POST'], allow_headers=['Content-Type', 'Authorization', 'X-API-Token'])
for module in (detecciones, eventos, alertas, estadisticas, salud, monitoreo, informes):
    app.include_router(module.router, prefix='/api')
app.add_api_route('/salud', salud.salud, methods=['GET'], tags=['sistema'])
app.add_api_route('/detecciones/recientes', detecciones.recientes, methods=['GET'], tags=['detecciones'])
app.add_api_route('/alertas', alertas.listar_array, methods=['GET'], tags=['alertas'])
app.include_router(geografia.router, prefix='/geografia', tags=['geografia'])
app.include_router(geografia.router, prefix='/api/geografia', tags=['geografia'])
app.mount('/geo', StaticFiles(directory=settings.data_dir / 'geo'), name='geo')


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, error: SQLAlchemyError):
    logging.getLogger('tunari').error('Error de base de datos: %s', type(error).__name__)
    return JSONResponse(status_code=503, content={'detail': 'PostGIS no está disponible'})
