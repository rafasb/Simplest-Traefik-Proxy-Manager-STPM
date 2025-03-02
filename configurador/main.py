from fastapi import FastAPI, Request, HTTPException, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from utils_frontend import templates
from utils_yml import (
    backup_config, restore_backup, read_config, write_config,
    get_routers, get_services, get_middlewares, add_service_config,
    delete_service_config, get_service_config, get_middleware,
    add_middleware, update_middleware, delete_middleware, parse_middleware_form
)
from utils_certs import read_acme, get_acme_crts, get_acme_endpoint
from schemas import ServiceConfig, Router, Service, Middleware
from utils_frontend import flash
from starlette.middleware.sessions import SessionMiddleware
from config import Config
from utils import create_htpassword
import json
from typing import Optional

import uvicorn

app = FastAPI(title="Simplest Traefik Proxy Manager", 
              description="Aplicación web para configurar servicios seguros en Traefik",
              version="1.0.0")

# Añadir SessionMiddleware para habilitar sesiones
# BASH: openssl rand -hex 32
app.add_middleware(
    SessionMiddleware, 
    secret_key=Config.middleware_key,
    max_age=14 * 24 * 60 * 60,          # 14 días
    https_only=False                    # Cambiar a True en producción
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root(request: Request):
    routers = get_routers()
    services = get_services()
    middlewares = get_middlewares()
    certificates = get_acme_crts(read_acme())
    
    return templates.TemplateResponse(
        "current_config.html", 
        {
            "request": request,
            "routers": routers,
            "services": services,
            "middlewares": middlewares,
            "certificates": certificates,
            "config": read_config()
        }
    )

@app.get("/add-service", response_class=HTMLResponse)
async def add_service_page(request: Request):
    middlewares = get_middlewares()
    
    return templates.TemplateResponse(
        "add_service_page.html", 
        {
            "request": request,
            "middlewares": middlewares,
            "config": read_config()
        }
    )
    
@app.delete("/service/{service_name}")
async def delete_service_entrypoint(request: Request, service_name: str):
    try:
        router_name = f"to-{service_name}"
        service_config = get_service_config(router_name)
        if not service_config:
            raise HTTPException(status_code=404, detail=f"Servicio {service_name} no encontrado")
        
        result = delete_service_config(router_name, service_name)
        
        if result:
            flash(request, f"Servicio {service_name} eliminado correctamente", "success")
            return {"status": "success", "message": f"Servicio {service_name} eliminado correctamente"}
        else:
            raise HTTPException(status_code=500, detail="No se pudo eliminar el servicio")
    
    except Exception as e:
        flash(request, f"Error al eliminar servicio: {str(e)}", "danger")
        raise HTTPException(status_code=500, detail=f"Error al eliminar servicio: {str(e)}")
    
#Endpoint para conocer el estado de la CA de certificados
@app.get("/ca_status")
async def get_ca_status():
    try:
        acme_content = read_acme()
        endpoint = get_acme_endpoint(acme_content)
        if "staging" in endpoint.lower():
            return {"status": "warning", "message": "La CA de certificados está en modo de pruebas", "endpoint": endpoint}
        else:
            return {"status": "success", "message": "La CA de certificados está en producción" , "endpoint": endpoint}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/certificates")
async def get_certificates():
    try:
        acme_content = read_acme()
        certificates = get_acme_crts(acme_content)
        return list(certificates.keys())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener certificados: {str(e)}")
    
@app.get("/certificates/{domain}")
async def get_certificate_info(domain: str):
    try:
        acme_content = read_acme()
        certificates = get_acme_crts(acme_content)
        return certificates.get(domain)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener información del certificado: {str(e)}")

@app.post("/add_service")
async def process_service_form(request: Request):
    try:
        form_data = await request.form()
        
        # Obtenemos el nombre del servicio
        service_name = form_data.get("service.name")
        middelwares_selected = form_data.getlist("router.middlewares")
        tls = (form_data.get("router.tls", False))
        # Crear objetos Router y Service con los datos del formulario
        router = Router(
            name=f"to-{service_name}",  # Aseguramos que siga el patrón requerido
            rule=f"Host(`{form_data.get("router.rule")}`)",
            service_name=service_name,
            middlewares=middelwares_selected,
            tls=True if tls == "on" else False
        )
        
        service = Service(
            name=service_name,
            url=form_data.get("service.url")
        )
        
        # Crear el objeto ServiceConfig
        service_config = ServiceConfig(
            router=router,
            service=service
        )
        
        # Añadir la configuración del servicio
        result = add_service_config(service_config)
        
        if result:
            flash(request, f"Servicio {service.name} añadido correctamente", "success")
        else:
            flash(request, "No se pudo añadir el servicio", "danger")
        
    except Exception as e:
        flash(request, f"Error al añadir servicio: {str(e)}", "danger")
    
    return RedirectResponse(url="/", status_code=303)

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

@app.get("/middlewares", response_class=HTMLResponse)
async def middlewares_page(request: Request):
    """Página para gestionar middlewares"""
    middlewares = get_middlewares()
    
    return templates.TemplateResponse(
        "edit_middlewares.html", 
        {
            "request": request,
            "middlewares": middlewares
        }
    )

@app.get("/add_middleware", response_class=HTMLResponse)
async def add_middleware_page(request: Request):
    """Página para añadir un nuevo middleware"""
    return templates.TemplateResponse(
        "add_middleware.html",
        {"request": request}
    )

@app.get("/update_middleware/{name}", response_class=HTMLResponse)
async def update_middleware_page(request: Request, name: str):
    """Página para editar un middleware específico"""
    # Obtener el middleware
    middleware = get_middleware(name)
    if not middleware:
        flash(request, f"Middleware '{name}' no encontrado", "danger")
        return RedirectResponse(url="/middlewares", status_code=303)
    
    # Buscar qué routers están usando este middleware
    routers_using_middleware = []
    all_routers = get_routers()
    
    for router in all_routers:
        if name in router.middlewares:
            routers_using_middleware.append(router)
    
    return templates.TemplateResponse(
        "edit_middleware.html", 
        {
            "request": request,
            "middleware": middleware,
            "routers_using_middleware": routers_using_middleware
        }
    )

@app.post("/add_middleware")
async def add_middleware_handler(request: Request):
    """Añade un nuevo middleware"""
    try:
        form_data = await request.form()
        
        # Convertimos los datos del formulario a un objeto Middleware
        middleware = parse_middleware_form(dict(form_data))
        
        # Añadimos el middleware
        result = add_middleware(middleware)
        
        if result:
            flash(request, f"Middleware {middleware.name} añadido correctamente", "success")
        else:
            flash(request, "No se pudo añadir el middleware", "danger")
        
    except HTTPException as e:
        flash(request, f"Error: {e.detail}", "danger")
    except Exception as e:
        flash(request, f"Error inesperado: {str(e)}", "danger")
    
    return RedirectResponse(url="/middlewares", status_code=303)

@app.post("/update_middleware")
async def update_middleware_handler(request: Request):
    """Actualiza un middleware existente"""
    try:
        form_data = await request.form()
        original_name = form_data.get("original_name")
        
        # Validar que el middleware existe
        existing_middleware = get_middleware(original_name)
        if not existing_middleware:
            raise HTTPException(status_code=404, detail=f"Middleware '{original_name}' no encontrado")
        
        # Procesar los datos del formulario
        # Para la edición, solo necesitamos el nombre, tipo y la configuración JSON
        try:
            config_data = json.loads(form_data.get("jsonConfig"))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="La configuración JSON proporcionada no es válida")
        
        middleware = Middleware(
            name=form_data.get("name"),
            type=form_data.get("type"),
            config=config_data
        )
        
        # Actualizar el middleware
        result = update_middleware(original_name, middleware)
        
        if result:
            flash(request, f"Middleware {middleware.name} actualizado correctamente", "success")
        else:
            flash(request, "No se pudo actualizar el middleware", "danger")
        
    except HTTPException as e:
        flash(request, f"Error: {e.detail}", "danger")
    except Exception as e:
        flash(request, f"Error inesperado: {str(e)}", "danger")
    
    return RedirectResponse(url="/middlewares", status_code=303)

@app.post("/delete_middleware")
async def delete_middleware_handler(request: Request):
    """Elimina un middleware existente"""
    try:
        form_data = await request.form()
        name = form_data.get("name")
        
        # Validar que el middleware existe
        existing_middleware = get_middleware(name)
        if not existing_middleware:
            raise HTTPException(status_code=404, detail=f"Middleware '{name}' no encontrado")
        
        # Eliminar el middleware
        result = delete_middleware(name)
        
        if result:
            flash(request, f"Middleware {name} eliminado correctamente", "success")
        else:
            flash(request, "No se pudo eliminar el middleware", "danger")
        
    except HTTPException as e:
        flash(request, f"Error: {e.detail}", "danger")
    except Exception as e:
        flash(request, f"Error inesperado: {str(e)}", "danger")
    
    return RedirectResponse(url="/middlewares", status_code=303)

@app.post("/generar_password")
async def generar_password(username: str = Form(...), password: str = Form(...)):
    """
    Genera un hash de contraseña para autenticación básica en formato htpasswd.
    
    Args:
        username (str): Nombre de usuario
        password (str): Contraseña en texto plano
        
    Returns:
        dict: Un diccionario con el hash de la contraseña
    """
    try:
        hashed_password = create_htpassword(username, password)
        return {"status": "success", "password_cifrado": hashed_password}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cifrar contraseña: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=9000, reload=True)