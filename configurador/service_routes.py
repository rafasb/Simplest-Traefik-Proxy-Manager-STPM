from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from utils_yml import (
    read_config, get_middlewares, get_service_config, 
    delete_service_config, add_service_config,
    get_routers, get_services
)
from utils_certs import read_acme, get_acme_crts
from schemas import ServiceConfig, Router, Service
from utils_frontend import templates, flash

router = APIRouter()

@router.get("/", response_class=HTMLResponse, tags=["services"])
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

@router.get("/add-service", response_class=HTMLResponse, tags=["services"])
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
    
@router.delete("/service/{service_name}", tags=["services"])
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

@router.post("/add_service", tags=["services"])
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
            rule=f"Host(`{form_data.get('router.rule')}`)",
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

@router.get("/update_service/{service_name}", response_class=HTMLResponse, tags=["services"])
async def update_service_page(request: Request, service_name: str):
    """Página para actualizar un servicio existente"""
    try:
        router_name = f"to-{service_name}"
        service_config = get_service_config(router_name)
        
        if not service_config:
            flash(request, f"Servicio {service_name} no encontrado", "danger")
            return RedirectResponse(url="/", status_code=303)
        
        middlewares = get_middlewares()
        
        return templates.TemplateResponse(
            "update_service_page.html", 
            {
                "request": request,
                "service_config": service_config,
                "middlewares": middlewares,
                "config": read_config()
            }
        )
    except Exception as e:
        flash(request, f"Error al cargar servicio: {str(e)}", "danger")
        return RedirectResponse(url="/", status_code=303)

@router.post("/update_service", tags=["services"])
async def update_service_handler(request: Request):
    """Actualiza la configuración de un servicio existente"""
    try:
        form_data = await request.form()
        
        # Obtenemos el nombre original del servicio para la actualización
        original_service_name = form_data.get("original_service_name")
        service_name = form_data.get("service.name")
        middelwares_selected = form_data.getlist("router.middlewares")
        tls = form_data.get("router.tls", False)
        
        # Verificar que el servicio existe
        original_router_name = f"to-{original_service_name}"
        existing_config = get_service_config(original_router_name)
        if not existing_config:
            flash(request, f"Servicio {original_service_name} no encontrado", "danger")
            return RedirectResponse(url="/", status_code=303)
        
        # Crear objetos Router y Service con los datos del formulario
        router = Router(
            name=f"to-{service_name}",
            rule=f"Host(`{form_data.get('router.rule')}`)",
            service_name=service_name,
            middlewares=middelwares_selected,
            tls=True if tls == "on" else False
        )
        
        service = Service(
            name=service_name,
            url=form_data.get("service.url")
        )
        
        # Crear el objeto ServiceConfig actualizado
        service_config = ServiceConfig(
            router=router,
            service=service
        )
        
        # Si el nombre cambió, eliminamos el servicio anterior y agregamos el nuevo
        result = False
        if original_service_name != service_name:
            # Eliminamos el servicio anterior
            delete_result = delete_service_config(original_router_name, original_service_name)
            if delete_result:
                # Agregamos el nuevo servicio con los datos actualizados
                result = add_service_config(service_config)
        else:
            # Eliminamos y volvemos a crear con los mismos nombres pero datos actualizados
            delete_service_config(original_router_name, original_service_name)
            result = add_service_config(service_config)
        
        if result:
            flash(request, f"Servicio {service.name} actualizado correctamente", "success")
        else:
            flash(request, "No se pudo actualizar el servicio", "danger")
        
    except Exception as e:
        flash(request, f"Error al actualizar servicio: {str(e)}", "danger")
    
    return RedirectResponse(url="/", status_code=303)
