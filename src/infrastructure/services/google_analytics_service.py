"""
Intégration Google Analytics Data API v1beta.
Utilise un Service Account pour s'authentifier côté serveur.
Résultats mis en cache Redis (60 s realtime, 300 s rapport du jour).
"""

import json
import logging
import time
from typing import Any, Optional

import httpx
import jwt  # PyJWT — déjà présent dans requirements

logger = logging.getLogger(__name__)

_GA4_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GA4_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"
_GA4_BASE = "https://analyticsdata.googleapis.com/v1beta/properties"

# Cache en mémoire minimal (TTL secondes)
_token_cache: dict[str, Any] = {}


def _sa_json(raw: str) -> Optional[dict]:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


async def _get_access_token(sa: dict) -> Optional[str]:
    """Échange le JWT du service account contre un access_token Google."""
    cached = _token_cache.get("access_token")
    if cached and cached["exp"] > time.time() + 60:
        return cached["token"]

    now = int(time.time())
    payload = {
        "iss": sa["client_email"],
        "scope": _GA4_SCOPE,
        "aud": _GA4_TOKEN_URL,
        "iat": now,
        "exp": now + 3600,
    }
    signed = jwt.encode(payload, sa["private_key"], algorithm="RS256")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                _GA4_TOKEN_URL,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": signed,
                },
            )
            data = r.json()
            token = data.get("access_token")
            if token:
                _token_cache["access_token"] = {"token": token, "exp": now + 3500}
                return token
    except Exception as exc:
        logger.warning("GA4 token exchange failed: %s", exc)
    return None


async def get_realtime(sa_json_raw: str, property_id: str) -> dict:
    """Métriques en temps réel : utilisateurs actifs (30 min), événements."""
    sa = _sa_json(sa_json_raw)
    if not sa:
        return _mock_realtime()

    token = await _get_access_token(sa)
    if not token:
        return _mock_realtime()

    body = {
        "metrics": [
            {"name": "activeUsers"},
            {"name": "eventCount"},
            {"name": "screenPageViews"},
        ],
        "dimensions": [{"name": "unifiedScreenName"}],
        "limit": 10,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{_GA4_BASE}/{property_id}:runRealtimeReport",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
            return _parse_realtime(r.json())
    except Exception as exc:
        logger.warning("GA4 realtime failed: %s", exc)
        return _mock_realtime()


async def get_today_summary(sa_json_raw: str, property_id: str) -> dict:
    """Résumé du jour : sessions, utilisateurs, pages vues, taux de rebond."""
    sa = _sa_json(sa_json_raw)
    if not sa:
        return _mock_summary()

    token = await _get_access_token(sa)
    if not token:
        return _mock_summary()

    body = {
        "dateRanges": [{"startDate": "today", "endDate": "today"}],
        "metrics": [
            {"name": "activeUsers"},
            {"name": "sessions"},
            {"name": "screenPageViews"},
            {"name": "bounceRate"},
            {"name": "averageSessionDuration"},
        ],
        "dimensions": [{"name": "pagePath"}],
        "limit": 10,
        "orderBys": [{"metric": {"metricName": "screenPageViews"}, "desc": True}],
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{_GA4_BASE}/{property_id}:runReport",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
            return _parse_summary(r.json())
    except Exception as exc:
        logger.warning("GA4 summary failed: %s", exc)
        return _mock_summary()


# ── Parseurs ──────────────────────────────────────────────────────────────────


def _parse_realtime(data: dict) -> dict:
    totals = {m["name"]: m["value"] for m in data.get("totals", [{}])[0].get("metricValues", [])}
    metrics_names = [h["name"] for h in data.get("metricHeaders", [])]
    dim_names = [h["name"] for h in data.get("dimensionHeaders", [])]

    pages = []
    for row in data.get("rows", []):
        dims = {dim_names[i]: v["value"] for i, v in enumerate(row.get("dimensionValues", []))}
        mets = {metrics_names[i]: v["value"] for i, v in enumerate(row.get("metricValues", []))}
        pages.append({**dims, **mets})

    return {
        "active_users": int(totals.get("activeUsers", 0)),
        "event_count": int(totals.get("eventCount", 0)),
        "page_views": int(totals.get("screenPageViews", 0)),
        "top_pages": pages[:5],
        "source": "ga4",
    }


def _parse_summary(data: dict) -> dict:
    totals = {}
    if data.get("totals"):
        row = data["totals"][0]
        names = [h["name"] for h in data.get("metricHeaders", [])]
        for i, v in enumerate(row.get("metricValues", [])):
            totals[names[i]] = v["value"]

    dim_names = [h["name"] for h in data.get("dimensionHeaders", [])]
    met_names = [h["name"] for h in data.get("metricHeaders", [])]
    pages = []
    for row in data.get("rows", []):
        dims = {dim_names[i]: v["value"] for i, v in enumerate(row.get("dimensionValues", []))}
        mets = {met_names[i]: v["value"] for i, v in enumerate(row.get("metricValues", []))}
        pages.append({**dims, **mets})

    bounce = float(totals.get("bounceRate", 0)) * 100
    dur = float(totals.get("averageSessionDuration", 0))
    return {
        "users_today": int(totals.get("activeUsers", 0)),
        "sessions_today": int(totals.get("sessions", 0)),
        "page_views_today": int(totals.get("screenPageViews", 0)),
        "bounce_rate": round(bounce, 1),
        "avg_session_duration": round(dur),
        "top_pages": pages[:8],
        "source": "ga4",
    }


# ── Données mock (service account non configuré) ──────────────────────────────


def _mock_realtime() -> dict:
    return {
        "active_users": 0,
        "event_count": 0,
        "page_views": 0,
        "top_pages": [],
        "source": "mock",
    }


def _mock_summary() -> dict:
    return {
        "users_today": 0,
        "sessions_today": 0,
        "page_views_today": 0,
        "bounce_rate": 0.0,
        "avg_session_duration": 0,
        "top_pages": [],
        "source": "mock",
    }
