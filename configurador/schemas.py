from pydantic import BaseModel, validator, Field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from urllib.parse import urlparse

class Service(BaseModel):
    name: str
    url: str
    
    @property
    def tls(self) -> bool:
        """Determina si el servicio usa TLS basándose en el esquema de la URL"""
        parsed_url = urlparse(self.url)
        return parsed_url.scheme.lower() == 'https'
    
    @property
    def host(self) -> str:
        """Extrae el host de la URL"""
        parsed_url = urlparse(self.url)
        return parsed_url.hostname or ""
    
    @property
    def port(self) -> int:
        """Extrae el puerto de la URL o devuelve el puerto por defecto según el esquema"""
        parsed_url = urlparse(self.url)
        if parsed_url.port:
            return parsed_url.port
        # Puerto por defecto según el esquema
        return 443 if self.tls else 80

class Router(BaseModel):
    name: str
    rule: str
    service_name: str
    middlewares: Optional[List[str]] = []
    tls: bool = True
    
    @validator('name')
    def validate_router_name(cls, v, values):
        """Valida que el nombre del router siga el patrón to-{service_name}"""
        service_name = values.get('service_name')
        if service_name and v != f"to-{service_name}":
            v = f"to-{service_name}"
        return v
    
    class Config:
        validate_assignment = True  # Para validar también al modificar atributos
    
    @property
    def fqdn(self) -> str:
        """Extrae el nombre de dominio completo (FQDN) de la regla"""
        import re
        match = re.search(r'Host\(`([^`]+)`\)', self.rule)
        if match:
            return match.group(1)
        return ""  # Retorna cadena vacía si no se encuentra un dominio

# Clase para gestionar middlewares
class Middleware(BaseModel):
    name: str
    type: str
    config: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """
        Convierte el middleware al formato esperado por Traefik
        Ejemplo:
        {
            "nombre-middleware": {
                "tipo-middleware": {
                    "param1": valor1,
                    "param2": valor2
                }
            }
        }
        """
        return {
            self.name: {
                self.type: self.config
            }
        }

# Modelo para crear un servicio completo (router + service)
class ServiceConfig(BaseModel):
    router: Router
    service: Service
    middleware: Optional[List[Middleware]] = None

class CertificateSubject(BaseModel):
    common_name: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    locality: Optional[str] = None
    organization: Optional[str] = None
    organizational_unit: Optional[str] = None
    email: Optional[str] = None

class CertificateInfo(BaseModel):
    subject: CertificateSubject
    issuer: CertificateSubject
    not_before: datetime
    not_after: datetime
    serial_number: int
    version: int
    signature_algorithm: str
    public_key: str
    fingerprint: str
