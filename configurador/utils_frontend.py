from fastapi.templating import Jinja2Templates
import typing
from fastapi.requests import Request
from datetime import datetime

templates = Jinja2Templates(directory="templates")

def flash(request: Request, message: typing.Any, category: str = "primary") -> None:
    if "_messages" not in request.session:
        request.session["_messages"] = []
    request.session["_messages"].append({"message": message, "category": category})

def get_flashed_messages(request: Request):
   return request.session.pop("_messages") if "_messages" in request.session else []
 
templates.env.globals["get_flashed_messages"] = get_flashed_messages

def format_default(value, default=""):
    return value if value else default

def format_date(value, format="%d-%m-%Y"):
    date = datetime.fromisoformat(value)
    return date.strftime(format)

templates.env.filters["format_date"] = format_date
templates.env.filters["format_default"] = format_default

def is_ssl_proxy(request: Request) -> bool:
    """Detecta si la petición viene a través de un proxy SSL"""
    # Cabeceras comunes que indican proxy SSL
    ssl_headers = {
        'X-Forwarded-Proto': 'https',
        'X-Forwarded-Ssl': 'on',
        'X-Url-Scheme': 'https'
    }
    
    for header, value in ssl_headers.items():
        if request.headers.get(header) == value:
            return True
    
    return False

def get_url_for(request: Request):
    """Wrapper para url_for que maneja SSL proxy"""
    def custom_url_for(*args, **kwargs):
        url = str(request.url_for(*args, **kwargs))
        if is_ssl_proxy(request):
            return url.replace('http://', 'https://')
        return url
    return custom_url_for

def is_mobile(request: Request) -> bool:
    # Comprobar User-Agent
    user_agent = request.headers.get("user-agent", "").lower()
    mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'ipod']
    is_mobile_device = any(keyword in user_agent for keyword in mobile_keywords)
    
    # Comprobar ancho de ventana
    cookies = request.cookies
    is_mobile_width = cookies.get('isMobileWidth') == 'true'
    
    return is_mobile_device or is_mobile_width