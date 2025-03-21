from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from utils_yml import (
    get_middlewares, get_middleware, add_middleware, 
    update_middleware, delete_middleware, parse_middleware_form, get_routers
)
from schemas import Middleware
from utils_frontend import templates, flash
from utils import create_htpassword
import json

router = APIRouter()

@router.get("/middlewares", response_class=HTMLResponse, tags=["middlewares"])
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

@router.get("/add_middleware", response_class=HTMLResponse, tags=["middlewares"])
async def add_middleware_page(request: Request):
    """Página para añadir un nuevo middleware"""
    return templates.TemplateResponse(
        "add_middleware.html",
        {"request": request}
    )

@router.get("/update_middleware/{name}", response_class=HTMLResponse, tags=["middlewares"])
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

@router.post("/add_middleware", tags=["middlewares"])
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

@router.post("/update_middleware", tags=["middlewares"])
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

@router.post("/delete_middleware", tags=["middlewares"])
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

@router.post("/generar_password", tags=["middlewares"])
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
