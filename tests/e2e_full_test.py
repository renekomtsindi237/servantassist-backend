"""
Suite de tests end-to-end complète — ServantAssist
Simule les appels Postman pour tous les modules.
Exécuter avec : python -X utf8 tests/e2e_full_test.py
"""

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

BASE = "http://localhost:8000/api/v1"
PASS = "Test1234!"

# ── Helpers HTTP ──────────────────────────────────────────────────────────────


def _req(method: str, url: str, body=None, token: str = "", content_type="application/json") -> tuple[int, Any]:
    data = None
    if body is not None:
        if content_type == "application/x-www-form-urlencoded":
            data = urllib.parse.urlencode(body).encode()
        else:
            data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", content_type)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"error": raw.decode(errors="replace")}
    except Exception as e:
        return 0, {"error": str(e), "type": type(e).__name__}


def GET(path, token=""):
    return _req("GET", f"{BASE}{path}", token=token)


def POST(path, body, token="", ct="application/json"):
    return _req("POST", f"{BASE}{path}", body, token, ct)


def PATCH(path, body, token=""):
    return _req("PATCH", f"{BASE}{path}", body, token)


def DELETE(path, token=""):
    return _req("DELETE", f"{BASE}{path}", token=token)


# ── Reporter ──────────────────────────────────────────────────────────────────


@dataclass
class TestResult:
    name: str
    passed: bool
    status: int
    detail: str = ""


results: list[TestResult] = []


def test(name: str, passed: bool, status: int, detail: str = ""):
    r = TestResult(name, passed, status, detail)
    results.append(r)
    icon = "✅" if passed else "❌"
    print(f"  {icon} [{status}] {name}" + (f" — {detail}" if detail else ""))
    return passed


def section(title: str):
    print(f"\n{'═'*60}")
    print(f"  {title}")
    print(f"{'═'*60}")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. AUTHENTIFICATION
# ═══════════════════════════════════════════════════════════════════════════════
section("1. AUTHENTIFICATION")

# Login admin
st, body = POST(
    "/auth/login",
    {"username": "renekomtsindi7@gmail.com", "password": "Mbetoumou olive77"},
    ct="application/x-www-form-urlencoded",
)
ADMIN_TOKEN = body.get("access_token", "")
test(
    "Login admin valide",
    st == 200 and bool(ADMIN_TOKEN),
    st,
    f"token={'ok' if ADMIN_TOKEN else 'absent'}",
)

# Login mauvais mot de passe (small delay to avoid rate limiting)
time.sleep(0.5)
st, _ = POST(
    "/auth/login",
    {"username": "renekomtsindi7@gmail.com", "password": "mauvais_mdp_xyz"},
    ct="application/x-www-form-urlencoded",
)
test("Login mauvais MDP → 401", st == 401, st)

# Login email inexistant
time.sleep(0.5)
st, _ = POST(
    "/auth/login",
    {"username": "inconnu_xyz@bmra.cm", "password": PASS},
    ct="application/x-www-form-urlencoded",
)
test("Login email inconnu → 401", st == 401, st)

# Forgot password
time.sleep(0.3)
st, body = POST("/auth/forgot-password", {"email": "renekomtsindi7@gmail.com"})
test("Forgot password (email existant) → 200 silencieux", st == 200, st)

st, body = POST("/auth/forgot-password", {"email": "inexistant@bmra.cm"})
test("Forgot password (email inexistant) → 200 silencieux", st == 200, st)

# Reset password mauvais token
st, _ = POST(
    "/auth/reset-password",
    {"token": "faux-token-invalide", "new_password": "Nouveau1234!"},
)
test("Reset password token invalide → 4xx", st in (400, 401, 404, 422), st)

# ═══════════════════════════════════════════════════════════════════════════════
# 2. PROFIL UTILISATEUR
# ═══════════════════════════════════════════════════════════════════════════════
section("2. PROFIL UTILISATEUR")

st, me = GET("/users/me", ADMIN_TOKEN)
test("GET /users/me", st == 200 and "email" in me, st, me.get("email", ""))

ADMIN_ID = me.get("id", "")

st, _ = PATCH(
    "/users/me",
    {"first_name": me.get("first_name", ""), "last_name": me.get("last_name", "")},
    ADMIN_TOKEN,
)
test("PATCH /users/me (mise à jour profil)", st == 200, st)

st, _ = GET("/users/me")
test("GET /users/me sans token → 401/403", st in (401, 403), st)

st, _ = PATCH(
    "/users/me/password",
    {"current_password": "Mbetoumou olive77", "new_password": "Mbetoumou olive77"},
    ADMIN_TOKEN,
)
test("PATCH /users/me/password (même MDP → 400)", st == 400, st)

# ═══════════════════════════════════════════════════════════════════════════════
# 3. GESTION DES MEMBRES (Admin)
# ═══════════════════════════════════════════════════════════════════════════════
section("3. GESTION DES MEMBRES (Admin)")

st, users = GET("/users/?page=1&page_size=10", ADMIN_TOKEN)
test(
    "GET /users/ (liste paginée)",
    st == 200 and "items" in users,
    st,
    f"total={users.get('total', 0)}",
)

st, _ = GET("/users/?role=SERVANT", ADMIN_TOKEN)
test("GET /users/ filtre role=SERVANT", st == 200, st)

st, _ = GET("/users/?is_active=true&page_size=5", ADMIN_TOKEN)
test("GET /users/ filtre is_active=true", st == 200, st)

st, _ = GET("/users/?search=Ren%C3%A9", ADMIN_TOKEN)
test("GET /users/ recherche textuelle (URL-encodé)", st == 200, st)

# Créer un servant de test (avec numéro de téléphone — login via /auth/login/phone)
servant_email = f"servant_{uuid.uuid4().hex[:8]}@bmra.cm"
servant_phone = f"+2376{uuid.uuid4().int % 90000000 + 10000000}"
st, servant = POST(
    "/auth/register",
    {
        "email": servant_email,
        "password": PASS,
        "first_name": "Test",
        "last_name": "Servant",
        "role": "SERVANT",
        "phone_number": servant_phone,
    },
    ADMIN_TOKEN,
)
SERVANT_ID = servant.get("id", "")
test(
    "POST /auth/register servant",
    st == 201 and bool(SERVANT_ID),
    st,
    f"id={'ok' if SERVANT_ID else 'absent'}",
)

# Login avec le servant créé via /auth/login/phone (réservé SERVANT/PARENT)
time.sleep(0.3)
st, srv_body = POST("/auth/login/phone", {"phone_number": servant_phone, "password": PASS})
SERVANT_TOKEN = srv_body.get("access_token", "")
test("Login servant créé (/auth/login/phone)", st == 200 and bool(SERVANT_TOKEN), st)

# Vérifier que servant ne peut pas lister les utilisateurs
st, _ = GET("/users/", SERVANT_TOKEN)
test("GET /users/ refusé pour servant → 403", st == 403, st)

# ═══════════════════════════════════════════════════════════════════════════════
# 4. CODES D'INVITATION (Admin)
# ═══════════════════════════════════════════════════════════════════════════════
section("4. CODES D'INVITATION (Admin)")

st, invites = GET("/admin/invitations", ADMIN_TOKEN)
test(
    "GET /admin/invitations",
    st == 200,
    st,
    f"count={len(invites) if isinstance(invites, list) else '?'}",
)

st, inv = POST(
    "/admin/invitations",
    {"role": "PARENT", "parent_name": "Marie Dupont", "notes": "Parent test E2E"},
    ADMIN_TOKEN,
)
INV_ID = inv.get("id", "")
INV_CODE = inv.get("code", "")
test(
    "POST /admin/invitations (créer code)",
    st == 201 and bool(INV_CODE),
    st,
    f"code={INV_CODE}",
)

st, invites2 = GET("/admin/invitations", ADMIN_TOKEN)
found = any(i.get("id") == INV_ID for i in (invites2 if isinstance(invites2, list) else []))
test("Code apparaît dans la liste", st == 200 and found, st)

# Servant ne peut pas accéder
st, _ = GET("/admin/invitations", SERVANT_TOKEN)
test("GET /admin/invitations refusé servant → 403", st == 403, st)

# Rôle ADMIN interdit
st, _ = POST("/admin/invitations", {"role": "ADMIN"}, ADMIN_TOKEN)
test("POST invitation rôle ADMIN → 400", st == 400, st)

# Toggle status
if INV_ID:
    st, _ = PATCH(f"/admin/invitations/{INV_ID}/toggle-status", {}, ADMIN_TOKEN)
    test("PATCH toggle-status invitation", st in (200, 204), st)

# Register parent avec code invitation
parent_email = f"parent_{uuid.uuid4().hex[:8]}@bmra.cm"
if INV_CODE:
    # Reactive the code first if it was toggled to REVOKED
    st_toggle, _ = PATCH(f"/admin/invitations/{INV_ID}/toggle-status", {}, ADMIN_TOKEN)

    st, parent = POST(
        "/auth/register",
        {
            "email": parent_email,
            "password": PASS,
            "first_name": "Marie",
            "last_name": "Dupont",
            "role": "PARENT",
            "invitation_code": INV_CODE,
        },
    )
    PARENT_ID = parent.get("id", "")
    test(
        "Register parent avec code invitation",
        st == 201 and bool(PARENT_ID),
        st,
        f"code={INV_CODE} id={'ok' if PARENT_ID else 'absent'}",
    )

    # Code désormais utilisé — re-register doit échouer
    st, _ = POST(
        "/auth/register",
        {
            "email": f"autre_{uuid.uuid4().hex[:6]}@bmra.cm",
            "password": PASS,
            "first_name": "Autre",
            "last_name": "Parent",
            "role": "PARENT",
            "invitation_code": INV_CODE,
        },
    )
    test("Register avec code déjà utilisé → 4xx", st >= 400, st)
else:
    test("Register parent avec code invitation", False, 0, "Pas de code disponible")
    PARENT_ID = ""
    test("Register avec code déjà utilisé → 4xx", False, 0, "Pas de code disponible")

# ═══════════════════════════════════════════════════════════════════════════════
# 5. DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
section("5. DASHBOARD")

st, summary = GET("/dashboard/summary", ADMIN_TOKEN)
test(
    "GET /dashboard/summary (admin)",
    st == 200 and "total_servants" in summary,
    st,
    f"servants={summary.get('total_servants', '?')}",
)

st, _ = GET("/dashboard/summary", SERVANT_TOKEN if SERVANT_TOKEN else ADMIN_TOKEN)
test("GET /dashboard/summary (servant → 403)", st == 403 if SERVANT_TOKEN else 200, st)

# ═══════════════════════════════════════════════════════════════════════════════
# 6. RAPPORTS
# ═══════════════════════════════════════════════════════════════════════════════
section("6. RAPPORTS")

st, reports = GET("/reports/", ADMIN_TOKEN)
test(
    "GET /reports/ (liste)",
    st == 200 and "items" in reports,
    st,
    f"items={reports.get('total', 0)}",
)

# Admin ne peut pas créer de rapport (réservé au Secrétaire)
st, _ = POST(
    "/reports/",
    {
        "type": "REUNION",
        "title": "Rapport test",
        "content": "Contenu du rapport de test",
        "report_date": "2026-06-01T10:00:00",
        "location": "Cathedrale",
        "participants": [],
    },
    ADMIN_TOKEN,
)
test("POST /reports/ admin → 403 (réservé Secrétaire)", st == 403, st)

# Servant sans nomination Secrétaire → 403
if SERVANT_TOKEN:
    st, _ = POST(
        "/reports/",
        {
            "type": "REUNION",
            "title": "Rapport test servant",
            "content": "Contenu test",
            "report_date": "2026-06-01T10:00:00",
            "location": "Cathedrale",
            "participants": [],
        },
        SERVANT_TOKEN,
    )
    test("POST /reports/ servant sans nomination → 403", st == 403, st)

# ═══════════════════════════════════════════════════════════════════════════════
# 7. ÉVÉNEMENTS LITURGIQUES
# ═══════════════════════════════════════════════════════════════════════════════
section("7. ÉVÉNEMENTS LITURGIQUES")

st, evts = GET("/events/", ADMIN_TOKEN)
test(
    "GET /events/ (liste)",
    st == 200 and "items" in evts,
    st,
    f"items={evts.get('total', 0)}",
)

st, evt = POST(
    "/events/",
    {
        "title": "Messe du dimanche E2E",
        "event_type": "MESSE_DOMINICALE",
        "start_time": "2026-06-01T09:00:00",
        "end_time": "2026-06-01T11:00:00",
        "location": "Cathedrale Notre-Dame de Yaounde",
    },
    ADMIN_TOKEN,
)
EVT_ID = evt.get("id", "")
test(
    "POST /events/ (créer événement)",
    st == 201 and bool(EVT_ID),
    st,
    f"id={'ok' if EVT_ID else 'absent'}",
)

if EVT_ID:
    st, _ = GET(f"/events/{EVT_ID}", SERVANT_TOKEN if SERVANT_TOKEN else ADMIN_TOKEN)
    test("GET /events/{id} (servant)", st == 200, st)

    st, _ = DELETE(f"/events/{EVT_ID}", ADMIN_TOKEN)
    test("DELETE /events/{id} (admin)", st in (200, 204), st)

# ═══════════════════════════════════════════════════════════════════════════════
# 8. PRÉSENCES
# ═══════════════════════════════════════════════════════════════════════════════
section("8. PRÉSENCES")

st, att = GET("/attendance/", ADMIN_TOKEN)
test("GET /attendance/ (liste)", st == 200, st)

st, sess = GET("/attendance-sessions/", ADMIN_TOKEN)
test("GET /attendance-sessions/ (liste)", st == 200, st)

# ═══════════════════════════════════════════════════════════════════════════════
# 9. MATÉRIEL LITURGIQUE
# ═══════════════════════════════════════════════════════════════════════════════
section("9. MATÉRIEL LITURGIQUE")

st, items = GET("/material/items/", ADMIN_TOKEN)
test(
    "GET /material/items/ (liste)",
    st == 200 and "items" in items,
    st,
    f"items={items.get('total', 0)}",
)

# POST sans slash final (évite le 307 redirect)
st, item = POST(
    "/material/items",
    {
        "name": "Calice test E2E",
        "category": "CALICE",
        "quantity": 1,
        "condition": "BON",
        "location": "Sacristie principale",
    },
    ADMIN_TOKEN,
)
ITEM_ID = item.get("id", "")
test(
    "POST /material/items (créer article)",
    st == 201 and bool(ITEM_ID),
    st,
    f"id={'ok' if ITEM_ID else 'absent'}",
)

if ITEM_ID:
    st, _ = GET(f"/material/items/{ITEM_ID}", SERVANT_TOKEN if SERVANT_TOKEN else ADMIN_TOKEN)
    test("GET /material/items/{id} (servant)", st == 200, st)

    st, _ = DELETE(f"/material/items/{ITEM_ID}", ADMIN_TOKEN)
    test("DELETE /material/items/{id} (admin)", st in (200, 204), st)

# ═══════════════════════════════════════════════════════════════════════════════
# 10. TRÉSORERIE
# ═══════════════════════════════════════════════════════════════════════════════
section("10. TRÉSORERIE")

st, entries = GET("/financial-entries/", ADMIN_TOKEN)
test("GET /financial-entries/ (liste)", st == 200, st)

st, periods = GET("/cotisations/periods", ADMIN_TOKEN)
test("GET /cotisations/periods (liste)", st == 200 and "items" in periods, st)

st, my_cot = GET("/cotisations/my", SERVANT_TOKEN if SERVANT_TOKEN else ADMIN_TOKEN)
test("GET /cotisations/my (self-service)", st == 200, st)

st, contribs = GET("/contributions/", ADMIN_TOKEN)
test("GET /contributions/ (liste)", st == 200, st)

# ═══════════════════════════════════════════════════════════════════════════════
# 11. FORMATION
# ═══════════════════════════════════════════════════════════════════════════════
section("11. FORMATION")

st, sessions = GET("/training/sessions", ADMIN_TOKEN)
test(
    "GET /training/sessions (liste)",
    st == 200 and "items" in sessions,
    st,
    f"items={sessions.get('total', 0)}",
)

# Admin and Aumonier can create training sessions (require_charge_liturgie allows them)
st, training = POST(
    "/training/sessions",
    {
        "title": "Formation liturgie E2E",
        "description": "Formation test end-to-end",
        "date": "2026-06-15T00:00:00",
        "start_time": "09h00",
        "end_time": "11h00",
        "duration_minutes": 120,
        "level": "DEBUTANT",
        "location": "Salle de reunion",
        "trainer_id": ADMIN_ID,
    },
    ADMIN_TOKEN,
)
TRAINING_ID = training.get("id", "")
test(
    "POST /training/sessions (admin)",
    st == 201 and bool(TRAINING_ID),
    st,
    f"id={'ok' if TRAINING_ID else 'absent'}",
)

if TRAINING_ID:
    st, _ = GET(
        f"/training/sessions/{TRAINING_ID}",
        SERVANT_TOKEN if SERVANT_TOKEN else ADMIN_TOKEN,
    )
    test("GET /training/sessions/{id} (servant)", st == 200, st)

# ═══════════════════════════════════════════════════════════════════════════════
# 12. DISCIPLINE
# ═══════════════════════════════════════════════════════════════════════════════
section("12. DISCIPLINE")

st, cases = GET("/discipline/", ADMIN_TOKEN)
test("GET /discipline/ (liste)", st == 200, st)

# Create discipline case (requires charge_discipline nomination or admin)
if SERVANT_ID:
    st, case = POST(
        "/discipline/",
        {
            "accused_user_id": SERVANT_ID,
            "offense_category": "ABSENCE_NON_JUSTIFIEE",
            "offense_description": "Absence non justifiée au service E2E test (au moins 10 caractères)",
        },
        ADMIN_TOKEN,
    )
    CASE_ID = case.get("id", "")
    test(
        "POST /discipline/ (créer cas)",
        st == 201 and bool(CASE_ID),
        st,
        f"id={'ok' if CASE_ID else 'absent'}",
    )
else:
    test("POST /discipline/", False, 0, "Pas de servant_id")
    CASE_ID = ""

# ═══════════════════════════════════════════════════════════════════════════════
# 13. SPORT & CULTURE
# ═══════════════════════════════════════════════════════════════════════════════
section("13. SPORT & CULTURE")

st, sc_evts = GET("/sport-culture/events", ADMIN_TOKEN)
test(
    "GET /sport-culture/events (liste)",
    st == 200 and "items" in sc_evts,
    st,
    f"items={sc_evts.get('total', 0)}",
)

st, sc_evt = POST(
    "/sport-culture/events",
    {
        "title": "Tournoi de foot E2E",
        "description": "Tournoi inter-groupes test",
        "event_type": "JOURNEE_SPORTIVE",
        "date": "2026-06-20T00:00:00",
        "start_time": "08h00",
        "end_time": "18h00",
        "location": "Terrain paroissial",
        "max_participants": 22,
    },
    ADMIN_TOKEN,
)
SC_EVT_ID = sc_evt.get("id", "")
test(
    "POST /sport-culture/events (créer événement)",
    st == 201 and bool(SC_EVT_ID),
    st,
    f"id={'ok' if SC_EVT_ID else 'absent'}",
)

if SC_EVT_ID:
    st, _ = DELETE(f"/sport-culture/events/{SC_EVT_ID}", ADMIN_TOKEN)
    test("DELETE /sport-culture/events/{id} (admin)", st in (200, 204), st)

# ═══════════════════════════════════════════════════════════════════════════════
# 14. COMMUNICATION
# ═══════════════════════════════════════════════════════════════════════════════
section("14. COMMUNICATION")

# GET mes notifications (endpoint self-service)
st, notifs = GET("/communication/me", ADMIN_TOKEN)
test(
    "GET /communication/me (mes notifications)",
    st == 200,
    st,
    f"count={len(notifs) if isinstance(notifs, list) else '?'}",
)

# GET stats notifications
st, stats = GET("/communication/me/stats", ADMIN_TOKEN)
test("GET /communication/me/stats", st == 200, st)

# POST notify (admin → admin lui-même)
if ADMIN_ID:
    st, notif = POST(
        "/communication/notify",
        {
            "recipient_id": ADMIN_ID,
            "notification_type": "GENERAL",
            "channel": "IN_APP",
            "priority": "NORMAL",
            "title": "Test E2E",
            "body": "Notification de test end-to-end",
        },
        ADMIN_TOKEN,
    )
    test("POST /communication/notify (envoyer notification)", st == 201, st)

# GET historique (admin)
st, hist = GET("/communication/history", ADMIN_TOKEN)
test("GET /communication/history (admin)", st == 200, st)

# ═══════════════════════════════════════════════════════════════════════════════
# 15. PLANNINGS
# ═══════════════════════════════════════════════════════════════════════════════
section("15. PLANNINGS")

st, weekly = GET("/weekly-schedule/", ADMIN_TOKEN)
test("GET /weekly-schedule/ (liste)", st == 200, st)

st, sunday = GET("/sunday-schedule/", ADMIN_TOKEN)
test("GET /sunday-schedule/ (liste)", st == 200, st)

# ═══════════════════════════════════════════════════════════════════════════════
# 16. SÉCURITÉ & CAS LIMITES
# ═══════════════════════════════════════════════════════════════════════════════
section("16. SÉCURITÉ & CAS LIMITES")

# Token invalide
st, _ = GET("/users/me", "token_invalide_xyz")
test("Token invalide → 401", st == 401, st)

# Servant ne peut pas lister les users (doit retourner 403)
if SERVANT_TOKEN:
    st, _ = GET("/users/", SERVANT_TOKEN)
    test("Liste users avec token servant → 403", st == 403, st)

# UUID inexistant
st, _ = GET(f"/users/{uuid.uuid4()}", ADMIN_TOKEN)
test("GET user inexistant → 404", st == 404, st)

# Payload invalide → 422
st, _ = POST("/events/", {"invalid_field": "bad"}, ADMIN_TOKEN)
test("POST events payload invalide → 422", st == 422, st)

# Email déjà existant → 409/422
st, _ = POST(
    "/auth/register",
    {
        "email": "renekomtsindi7@gmail.com",
        "password": PASS,
        "first_name": "Duplicate",
        "last_name": "User",
        "role": "SERVANT",
    },
    ADMIN_TOKEN,
)
test("Register email déjà existant → 409/400", st in (409, 400, 422), st)

# Admin ne peut pas se supprimer
if ADMIN_ID:
    st, _ = DELETE(f"/users/{ADMIN_ID}", ADMIN_TOKEN)
    test("Admin ne peut pas se supprimer → 400/403", st in (400, 403), st)

# ═══════════════════════════════════════════════════════════════════════════════
# 17. CLÉS API
# ═══════════════════════════════════════════════════════════════════════════════
section("17. CLÉS API")

st, keys = GET("/api-keys/", ADMIN_TOKEN)
test("GET /api-keys/ (liste)", st == 200, st)

st, new_key = POST("/api-keys/", {"name": "Test E2E Key", "scopes": []}, ADMIN_TOKEN)
KEY_ID = new_key.get("id", "")
RAW_KEY = new_key.get("raw_key", "")
test(
    "POST /api-keys/ (créer clé)",
    st == 201 and bool(RAW_KEY),
    st,
    f"raw_key={'ok' if RAW_KEY else 'absent'}",
)

if KEY_ID:
    st, _ = DELETE(f"/api-keys/{KEY_ID}", ADMIN_TOKEN)
    test("DELETE /api-keys/{id} (révoquer clé)", st in (200, 204), st)

# ═══════════════════════════════════════════════════════════════════════════════
# 18. NETTOYAGE DES DONNÉES DE TEST
# ═══════════════════════════════════════════════════════════════════════════════
section("18. NETTOYAGE DES DONNÉES DE TEST")

cleaned = []
for user_id, label in [
    (SERVANT_ID, "servant"),
    (PARENT_ID if "PARENT_ID" in dir() else "", "parent"),
]:
    if user_id:
        st, _ = DELETE(f"/users/{user_id}", ADMIN_TOKEN)
        if st in (200, 204, 404):
            cleaned.append(label)

test("Nettoyage utilisateurs de test", len(cleaned) > 0, 200, f"supprimés: {cleaned}")

# ═══════════════════════════════════════════════════════════════════════════════
# RÉSULTATS FINAUX
# ═══════════════════════════════════════════════════════════════════════════════
passed = sum(1 for r in results if r.passed)
total = len(results)

print(f"\n{'═'*60}")
print(f"  RÉSULTATS : {passed}/{total} tests passés")
print(f"{'═'*60}")

failures = [r for r in results if not r.passed]
if failures:
    print(f"\n  ❌ Échecs ({len(failures)}) :")
    for r in failures:
        print(f"     [{r.status}] {r.name}" + (f" — {r.detail}" if r.detail else ""))

rate = round(passed / total * 100, 1) if total else 0
print(f"\n  Taux de réussite : {rate}%\n")
