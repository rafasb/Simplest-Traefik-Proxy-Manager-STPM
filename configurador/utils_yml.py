from config import Config
from fastapi import HTTPException
from schemas import Router, Service, Middleware, ServiceConfig
from typing import List, Dict, Optional
import yaml

def read_config(path: str = Config.path_http) -> dict:
    file = None
    try:
        file = open(path, "r")
        config = yaml.safe_load(file) or {"http": {"routers": {}, "services": {}}}
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al leer configuración: {str(e)}")
    finally:
        if file:
            file.close()
    
def write_config(config: dict, path: str = Config.path_http):
    file = None
    try:
        file = open(path, "w")
        yaml.dump(config, file, default_flow_style=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al escribir configuración: {str(e)}")
    finally:
        if file:
            file.close()
    
# Función de backup
def backup_config(path: str = Config.path_http):
    # Leeremos la configuración actual
    current_config = read_config(path)
    backup_path = path.replace(".yml", "_backup.yml")
    write_config(current_config, backup_path)
    
# Función de restauración
def restore_backup(path: str = Config.path_http):
    backup_path = path.replace(".yml", "_backup.yml")
    backup_config = read_config(backup_path)
    write_config(backup_config, path)

# Nuevas funciones que aprovechan las clases Router, Service y Middleware

def get_routers() -> List[Router]:
    """Obtiene todos los routers como objetos Router"""
    config = read_config()
    routers = []
    
    if "http" in config and "routers" in config["http"]:
        for name, router_config in config["http"]["routers"].items():
            middlewares = router_config.get("middlewares", [])
            tls = bool(router_config.get("tls", False))
            router = Router(
                name=name,
                rule=router_config.get("rule", ""),
                service_name=router_config.get("service", ""),
                middlewares=middlewares,
                tls=tls
            )
            routers.append(router)
    
    return routers

def get_services() -> List[Service]:
    """Obtiene todos los servicios como objetos Service"""
    config = read_config()
    services = []
    
    if "http" in config and "services" in config["http"]:
        for name, service_config in config["http"]["services"].items():
            url = ""
            if "loadBalancer" in service_config and "servers" in service_config["loadBalancer"]:
                servers = service_config["loadBalancer"]["servers"]
                if servers and "url" in servers[0]:
                    url = servers[0]["url"]
            
            service = Service(name=name, url=url)
            services.append(service)
    
    return services

def get_middlewares() -> List[Middleware]:
    """Obtiene todos los middlewares como objetos Middleware"""
    config = read_config()
    middlewares = []
    
    if "http" in config and "middlewares" in config["http"]:
        for name, middleware_config in config["http"]["middlewares"].items():
            # Determinar el tipo y la configuración del middleware
            if middleware_config:
                middleware_type = next(iter(middleware_config.keys()))
                middleware_config_data = middleware_config[middleware_type]
                middleware = Middleware(
                    name=name,
                    type=middleware_type,
                    config=middleware_config_data
                )
                middlewares.append(middleware)
    
    return middlewares

def add_service_config(service_config: ServiceConfig) -> bool:
    """Añade un nuevo servicio y router completos"""
    try:
        config = read_config()
        
        # Asegurar que existen las estructuras necesarias
        if "http" not in config:
            config["http"] = {}
        if "routers" not in config["http"]:
            config["http"]["routers"] = {}
        if "services" not in config["http"]:
            config["http"]["services"] = {}
        if "middlewares" not in config["http"]:
            config["http"]["middlewares"] = {}
        
        # Añadir el router
        router = service_config.router
        config["http"]["routers"][router.name] = {
            "rule": router.rule,
            "service": router.service_name,
        }
        
        if router.middlewares:
            middleware_names = []
            for middleware in router.middlewares:
                middleware_name = middleware.split(" ")[0].split("=")[1].replace("'", "")
                middleware_names.append(middleware_name)
            
            config["http"]["routers"][router.name]["middlewares"] = middleware_names
        
        if router.tls:
            config["http"]["routers"][router.name]["tls"] = Config.tls
        
        # Añadir el servicio
        service = service_config.service
        config["http"]["services"][service.name] = {
            "loadBalancer": {
                "servers": [
                    {"url": service.url}
                ]
            }
        }
        
        # Añadir middlewares si existen
        if service_config.middleware:
            for middleware in service_config.middleware:
                middleware_dict = middleware.to_dict()
                for name, config_data in middleware_dict.items():
                    config["http"]["middlewares"][name] = config_data
        
        # Guardar la configuración
        write_config(config)
        return True
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al añadir configuración de servicio: {str(e)}")

def delete_service_config(router_name: str, service_name: str) -> bool:
    """Elimina un router y un servicio por nombre"""
    try:
        config = read_config()
        
        # Eliminar router
        if "http" in config and "routers" in config["http"] and router_name in config["http"]["routers"]:
            del config["http"]["routers"][router_name]
        
        # Eliminar servicio
        if "http" in config and "services" in config["http"] and service_name in config["http"]["services"]:
            del config["http"]["services"][service_name]
        
        # Guardar la configuración
        write_config(config)
        return True
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar configuración de servicio: {str(e)}")

def update_router(router: Router) -> bool:
    """Actualiza un router existente"""
    try:
        config = read_config()
        
        if "http" in config and "routers" in config["http"] and router.name in config["http"]["routers"]:
            router_config = {
                "rule": router.rule,
                "service": router.service_name
            }
            
            if router.middlewares:
                router_config["middlewares"] = router.middlewares
            
            if router.tls:
                router_config["tls"] = {}
            
            config["http"]["routers"][router.name] = router_config
            write_config(config)
            return True
        else:
            return False
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar router: {str(e)}")

def update_service(service: Service) -> bool:
    """Actualiza un servicio existente"""
    try:
        config = read_config()
        
        if "http" in config and "services" in config["http"] and service.name in config["http"]["services"]:
            service_config = {
                "loadBalancer": {
                    "servers": [
                        {"url": service.url}
                    ]
                }
            }
            
            config["http"]["services"][service.name] = service_config
            write_config(config)
            return True
        else:
            return False
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar servicio: {str(e)}")

def get_service_config(router_name: str) -> Optional[ServiceConfig]:
    """Obtiene la configuración completa de un servicio por el nombre del router"""
    config = read_config()
    
    if "http" not in config or "routers" not in config["http"] or router_name not in config["http"]["routers"]:
        return None
    
    router_config = config["http"]["routers"][router_name]
    service_name = router_config.get("service", "")
    
    if not service_name or "services" not in config["http"] or service_name not in config["http"]["services"]:
        return None
    
    service_config = config["http"]["services"][service_name]
    
    # Construir objetos Router y Service
    router = Router(
        name=router_name,
        rule=router_config.get("rule", ""),
        service_name=service_name,
        middlewares=router_config.get("middlewares", []),
        tls=bool(router_config.get("tls", False))
    )
    
    url = ""
    if "loadBalancer" in service_config and "servers" in service_config["loadBalancer"]:
        servers = service_config["loadBalancer"]["servers"]
        if servers and "url" in servers[0]:
            url = servers[0]["url"]
    
    service = Service(name=service_name, url=url)
    
    # Obtener middlewares asociados
    middlewares = []
    middleware_names = router_config.get("middlewares", [])
    if middleware_names and "middlewares" in config["http"]:
        for name in middleware_names:
            if name in config["http"]["middlewares"]:
                middleware_config = config["http"]["middlewares"][name]
                if middleware_config:
                    middleware_type = next(iter(middleware_config.keys()))
                    middleware_config_data = middleware_config[middleware_type]
                    middleware = Middleware(
                        name=name,
                        type=middleware_type,
                        config=middleware_config_data
                    )
                    middlewares.append(middleware)
    
    return ServiceConfig(router=router, service=service, middleware=middlewares if middlewares else None)

def get_middleware(name: str) -> Optional[Middleware]:
    """Obtiene un middleware específico por su nombre"""
    config = read_config()
    
    if ("http" in config and "middlewares" in config["http"] and 
        name in config["http"]["middlewares"]):
        middleware_config = config["http"]["middlewares"][name]
        
        # Determinar el tipo y la configuración del middleware
        if middleware_config:
            middleware_type = next(iter(middleware_config.keys()))
            middleware_config_data = middleware_config[middleware_type]
            return Middleware(
                name=name,
                type=middleware_type,
                config=middleware_config_data
            )
    
    return None

def add_middleware(middleware: Middleware) -> bool:
    """Añade un nuevo middleware a la configuración"""
    try:
        config = read_config()
        
        # Asegurar que existe la estructura necesaria
        if "http" not in config:
            config["http"] = {}
        if "middlewares" not in config["http"]:
            config["http"]["middlewares"] = {}
        
        # Comprobar si el middleware ya existe
        if middleware.name in config["http"]["middlewares"]:
            raise HTTPException(
                status_code=400, 
                detail=f"El middleware '{middleware.name}' ya existe"
            )
        
        # Añadir el middleware
        config["http"]["middlewares"][middleware.name] = {
            middleware.type: middleware.config
        }
        
        # Guardar la configuración
        write_config(config)
        return True
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error al añadir middleware: {str(e)}"
        )

def update_middleware(original_name: str, middleware: Middleware) -> bool:
    """Actualiza un middleware existente"""
    try:
        config = read_config()
        
        # Comprobar si el middleware existe
        if ("http" not in config or 
            "middlewares" not in config["http"] or 
            original_name not in config["http"]["middlewares"]):
            
            raise HTTPException(
                status_code=404, 
                detail=f"El middleware '{original_name}' no existe"
            )
        
        # Si se está cambiando el nombre, comprobar que el nuevo nombre no exista ya
        if original_name != middleware.name and middleware.name in config["http"]["middlewares"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Ya existe un middleware con el nombre '{middleware.name}'"
            )
        
        # Eliminar el middleware con el nombre original
        if original_name != middleware.name:
            del config["http"]["middlewares"][original_name]
        
        # Añadir el middleware actualizado
        config["http"]["middlewares"][middleware.name] = {
            middleware.type: middleware.config
        }
        
        # Actualizar referencias en routers
        if original_name != middleware.name:
            if "routers" in config["http"]:
                for router_name, router_config in config["http"]["routers"].items():
                    if "middlewares" in router_config and original_name in router_config["middlewares"]:
                        # Reemplazar el nombre del middleware en la lista
                        router_config["middlewares"] = [
                            middleware.name if mw == original_name else mw 
                            for mw in router_config["middlewares"]
                        ]
        
        # Guardar la configuración
        write_config(config)
        return True
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error al actualizar middleware: {str(e)}"
        )

def delete_middleware(name: str) -> bool:
    """Elimina un middleware por su nombre"""
    try:
        config = read_config()
        
        # Comprobar si el middleware existe
        if ("http" not in config or 
            "middlewares" not in config["http"] or 
            name not in config["http"]["middlewares"]):
            
            raise HTTPException(
                status_code=404, 
                detail=f"El middleware '{name}' no existe"
            )
        
        # Comprobar si el middleware está siendo utilizado por algún router
        if "routers" in config["http"]:
            routers_using_middleware = []
            
            for router_name, router_config in config["http"]["routers"].items():
                if "middlewares" in router_config and name in router_config["middlewares"]:
                    routers_using_middleware.append(router_name)
            
            if routers_using_middleware:
                # Opción 1: Impedir la eliminación
                # raise HTTPException(
                #     status_code=400,
                #     detail=f"No se puede eliminar el middleware '{name}' porque está siendo utilizado por los siguientes routers: {', '.join(routers_using_middleware)}"
                # )
                
                # Opción 2: Eliminar las referencias
                for router_name in routers_using_middleware:
                    config["http"]["routers"][router_name]["middlewares"].remove(name)
                    # Si la lista queda vacía, eliminarla
                    if not config["http"]["routers"][router_name]["middlewares"]:
                        del config["http"]["routers"][router_name]["middlewares"]
        
        # Eliminar el middleware
        del config["http"]["middlewares"][name]
        
        # Guardar la configuración
        write_config(config)
        return True
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error al eliminar middleware: {str(e)}"
        )

def parse_middleware_form(form_data: dict) -> Middleware:
    """
    Convierte los datos del formulario en un objeto Middleware
    """
    try:
        name = form_data.get("name")
        middleware_type = form_data.get("type")
        
        # Si hay una configuración JSON directa, usarla
        if "jsonConfig" in form_data and form_data.get("jsonConfig").strip():
            import json
            try:
                config_data = json.loads(form_data.get("jsonConfig"))
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400, 
                    detail="La configuración JSON proporcionada no es válida"
                )
        else:
            # Construir la configuración según el tipo de middleware
            config_data = {}
            
            if middleware_type == "basicAuth":
                users = form_data.get("users", "").strip().split("\n")
                users = [user.strip() for user in users if user.strip()]
                config_data["users"] = users
                
                realm = form_data.get("realm", "").strip()
                if realm:
                    config_data["realm"] = realm
            
            elif middleware_type == "headers":
                # Implementar según necesidades específicas
                pass
            
            # Añadir más tipos según sea necesario
        
        return Middleware(
            name=name,
            type=middleware_type,
            config=config_data
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error al procesar el formulario de middleware: {str(e)}"
        )