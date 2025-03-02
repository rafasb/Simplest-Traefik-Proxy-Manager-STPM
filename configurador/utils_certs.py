from config import Config
from fastapi import HTTPException
import OpenSSL
import cryptography.hazmat.primitives.serialization
from datetime import datetime
from schemas import CertificateInfo, CertificateSubject

def read_acme(path: str = Config.path_acme) -> dict:
    """Lee el contenido del archivo acme.json y lo devuelve como un diccionario."""
    try:
        import json
        with open(path, "r") as file:
            content = json.load(file)
        return content
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {path}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error al decodificar el archivo JSON")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al leer el archivo: {str(e)}")

# Función auxiliar para obtener el endpoint empleado para obtener los certificados
def get_acme_endpoint(acme: dict) -> str:
    """Extrae el endpoint de la configuración acme y lo devuelve como una cadena."""
    try:
        endpoint = acme.get('myresolver', {}).get('Account', {}).get('Registration').get('uri')
        return endpoint
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener el endpoint: {str(e)}")
    
def get_acme_crts(acme: dict) -> dict:
    """Extrae los certificados del diccionario acme y los organiza por dominio principal."""
    certificates = {}
    try:
        # Accedemos a la lista de certificados
        certs_list = acme.get('myresolver', {}).get('Certificates', [])
        
        # Por cada certificado en la lista
        for cert in certs_list:
            # Extraemos el dominio principal (main) y el certificado
            domain = cert.get('domain', {}).get('main')
            certificate = cert.get('certificate')
            
            # Si ambos existen, los añadimos al diccionario
            if domain and certificate:
                subject = get_cert_info(certificate).subject
                not_after = get_cert_info(certificate).not_after
                certificates[domain] = {"subject":subject, "not_after":not_after}
                
        return certificates
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando certificados: {str(e)}")

def _parse_components(components) -> CertificateSubject:
    """Función auxiliar para parsear los componentes del certificado"""
    subject_dict = {}
    for key, value in components:
        key = key.decode('utf-8')
        value = value.decode('utf-8')
        if key == 'CN':
            subject_dict['common_name'] = value
        elif key == 'C':
            subject_dict['country'] = value
        elif key == 'ST':
            subject_dict['state'] = value
        elif key == 'L':
            subject_dict['locality'] = value
        elif key == 'O':
            subject_dict['organization'] = value
        elif key == 'OU':
            subject_dict['organizational_unit'] = value
        elif key == 'emailAddress':
            subject_dict['email'] = value
    return CertificateSubject(**subject_dict)

def get_cert_info(certificate: str) -> CertificateInfo:
    """Extrae la información de un certificado en formato PEM y la devuelve como CertificateInfo."""
    try:
        import base64
        
        cert_decoded = base64.b64decode(certificate)
        cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_decoded)
        
        return CertificateInfo(
            subject=_parse_components(cert.get_subject().get_components()),
            issuer=_parse_components(cert.get_issuer().get_components()),
            not_before=datetime.strptime(cert.get_notBefore().decode(), '%Y%m%d%H%M%SZ'),
            not_after=datetime.strptime(cert.get_notAfter().decode(), '%Y%m%d%H%M%SZ'),
            serial_number=cert.get_serial_number(),
            version=cert.get_version(),
            signature_algorithm=cert.get_signature_algorithm().decode(),
            public_key=cert.get_pubkey().to_cryptography_key().public_bytes(
                encoding=cryptography.hazmat.primitives.serialization.Encoding.PEM,
                format=cryptography.hazmat.primitives.serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode(),
            fingerprint=cert.digest("sha256").decode()
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al extraer información del certificado: {str(e)}")
    
if __name__ == "__main__":
    pass

