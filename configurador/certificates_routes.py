from fastapi import APIRouter, HTTPException
from utils_certs import read_acme, get_acme_crts, get_acme_endpoint

router = APIRouter()

#Endpoint para conocer el estado de la CA de certificados
@router.get("/ca_status", tags=["certificates"])
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

@router.get("/certificates", tags=["certificates"])
async def get_certificates():
    try:
        acme_content = read_acme()
        certificates = get_acme_crts(acme_content)
        return list(certificates.keys())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener certificados: {str(e)}")
    
@router.get("/certificates/{domain}", tags=["certificates"])
async def get_certificate_info(domain: str):
    try:
        acme_content = read_acme()
        certificates = get_acme_crts(acme_content)
        return certificates.get(domain)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener información del certificado: {str(e)}")
