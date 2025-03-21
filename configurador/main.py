from fastapi import FastAPI, Request, HTTPException, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from utils_frontend import templates
from utils_yml import (
    backup_config, restore_backup, read_config, write_config,
    get_routers, get_services, get_middlewares
)
from utils_certs import read_acme, get_acme_crts
from schemas import ServiceConfig, Router, Service, Middleware
from utils_frontend import flash
from starlette.middleware.sessions import SessionMiddleware
from config import Config
from utils import create_htpassword
import json
from typing import Optional
# Importamos los routers
from service_routes import router as service_router
from middleware_routes import router as middleware_router
from certificates_routes import router as certificates_router

import uvicorn

app = FastAPI(title="Simplest Traefik Proxy Manager", 
              description="Aplicación web para configurar servicios seguros en Traefik",
              version="1.0.0")

# Añadir SessionMiddleware para habilitar sesiones
app.add_middleware(
    SessionMiddleware, 
    secret_key=Config.middleware_key,
    max_age=14 * 24 * 60 * 60,          # 14 días
    https_only=False                    # Cambiar a True en producción
)

# Incluimos los routers
app.include_router(service_router)
app.include_router(middleware_router)
app.include_router(certificates_router)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Se eliminó el endpoint "/" que ahora está en service_routes.py

@app.post("/backup")
async def create_backup():
    try:
        backup_config()
        return {"status": "success", "message": "Backup creado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear backup: {str(e)}")

@app.post("/restore")
async def restore_configuration():
    try:
        restore_backup()
        return {"status": "success", "message": "Configuración restaurada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al restaurar configuración: {str(e)}")

# Se eliminó la función generar_password que ahora está en middleware_routes.py

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=9000, reload=True)