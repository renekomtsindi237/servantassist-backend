"""
Géolocalisation d'adresse IP via ip-api.com (gratuit, sans clé).
Retourne lat/lng/city/country ou None pour les IPs privées/inconnues.
"""

import ipaddress
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]

_FIELDS = "status,country,countryCode,city,lat,lon"


def _is_private(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
        return any(addr in net for net in _PRIVATE_NETWORKS)
    except ValueError:
        return True


async def geolocate_ip(ip: str) -> Optional[dict]:
    """Résout une IP en coordonnées géographiques. Retourne None si privée ou échec."""
    if _is_private(ip):
        return None
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"http://ip-api.com/json/{ip}?fields={_FIELDS}")
            data = r.json()
            if data.get("status") == "success":
                return {
                    "country": data.get("country"),
                    "country_code": data.get("countryCode"),
                    "city": data.get("city"),
                    "lat": data.get("lat"),
                    "lng": data.get("lon"),
                }
    except Exception as exc:  # noqa: BLE001
        logger.debug("Geolocation failed for %s: %s", ip, exc)
    return None


def extract_client_ip(request) -> str:  # type: ignore[no-untyped-def]
    """Extrait la vraie IP cliente depuis les headers (Cloudflare → nginx → direct)."""
    headers = request.headers
    cf_ip = headers.get("cf-connecting-ip", "").strip()
    if cf_ip:
        return cf_ip
    forwarded = headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = headers.get("x-real-ip", "").strip()
    if real_ip:
        return real_ip
    return request.client.host if request.client else "unknown"
