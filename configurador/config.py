import os

MIDDLEWARE_KEY = os.getenv("MIDDLEWARE_KEY", "98190290bb6c9f902a2f7d78f2159d5672a0fdb3c76210dc54ad516420a4da1d")
PATH_HTTP = os.getenv("PATH_HTTP")
PATH_ACME = os.getenv("PATH_ACME")
TLS = os.getenv("TLS", '{"certResolver": "myresolver"}')

class Config():
    path_http: str = PATH_HTTP
    path_acme: str = PATH_ACME
    tls: dict = {"certResolver": "myresolver"}
    middleware_key: str = MIDDLEWARE_KEY