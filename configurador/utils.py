from config import Config
from fastapi import HTTPException
from passlib.apache import HtpasswdFile

def configure_router(config: dict, router_name: str, host: str, service_name: str, middlewares: list = None, tls: bool = False) -> dict:
    """Configura un router en la configuración de Traefik."""
    new_config = config.copy()
    new_config["http"]["routers"][router_name] = {
        "rule": f"Host(`{host}`)",
        "service": service_name
    }
    
    if middlewares:
        new_config["http"]["routers"][router_name]["middlewares"] = middlewares
    
    if tls:
        new_config["http"]["routers"][router_name]["tls"] = {
            "certResolver": "myresolver"
        }
    
    return new_config

def configure_service(config: dict, service_name: str, url: str) -> dict:
    """Configura un service en la configuración de Traefik."""
    new_config = config.copy()
    new_config["http"]["services"][service_name] = {
        "loadBalancer": {
            "servers": [
                {"url": url}
            ]
        }
    }
    return new_config

def delete_service(config: dict, name: str) -> dict:
    """Elimina un servicio y su router asociado de la configuración de Traefik."""
    new_config = config.copy()
    router_name = f"to-{name}"
    
    if router_name in new_config["http"]["routers"]:
        del new_config["http"]["routers"][router_name]
    
    if name in new_config["http"]["services"]:
        del new_config["http"]["services"][name]
        
    return new_config

def get_middlewares_config(config: dict) -> dict:
    """Obtiene la configuración de todos los middlewares.
    
    Args:
        config (dict): Configuración global de Traefik
        
    Returns:
        dict: Diccionario con todos los middlewares configurados
        
    Raises:
        HTTPException: Si no hay middlewares configurados
    """
    try:
        middlewares = config["http"]["middlewares"]
        if not middlewares:
            raise HTTPException(
                status_code=404,
                detail="No middlewares configured"
            )
        return middlewares
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Middlewares configuration not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting middlewares configuration: {str(e)}"
        )

def create_htpassword(username: str, password: str) -> str:
    htpasswd = HtpasswdFile()
    htpasswd.set_password(username, password)
    return htpasswd.to_string()