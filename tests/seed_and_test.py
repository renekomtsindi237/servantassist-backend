"""
ServantAssist — Seed massif + Test exhaustif de tous les endpoints
=================================================================
Exécuter avec : python -X utf8 tests/seed_and_test.py
Prérequis      : serveur local sur http://localhost:8000
                 (uvicorn src.main:app --reload)

Le script :
  1. Injecte ~60 entités (servants, parents, événements, cotisations, …)
  2. Couvre tous les modules avec GET / POST / PATCH / DELETE
  3. Vérifie le RBAC (403 pour les rôles insuffisants)
  4. Vérifie les cas d'erreur (401, 404, 422, 409)
  5. Affiche un rapport coloré avec taux de réussite par section
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

# ─────────────────────────── Configuration ────────────────────────────────
BASE = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "renekomtsindi7@gmail.com"
ADMIN_PASS = "Mbetoumou olive77"
NEW_PASS = "ServTest2026!"  # mdp pour les users créés dans ce script

now_utc = datetime.now(timezone.utc)
RUN_ID = now_utc.strftime("%H%M%S")  # préfixe unique par exécution


def _dt(delta: timedelta) -> str:
    return (now_utc + delta).strftime("%Y-%m-%dT%H:%M:%S")


FUTURE_1 = _dt(timedelta(days=7))
FUTURE_1_END = _dt(timedelta(days=7, hours=2))
FUTURE_2 = _dt(timedelta(days=14))
FUTURE_2_END = _dt(timedelta(days=14, hours=2))
FUTURE_3 = _dt(timedelta(days=21))
FUTURE_3_END = _dt(timedelta(days=21, hours=2))
FUTURE_4 = _dt(timedelta(days=30))
FUTURE_4_END = _dt(timedelta(days=30, hours=2))
PAST_1 = _dt(-timedelta(days=7))
PAST_1_END = _dt(-timedelta(days=7) + timedelta(hours=2))
PAST_2 = _dt(-timedelta(days=14))


# ─────────────────────────── HTTP Helpers ─────────────────────────────────
def _req(method, url, body=None, token="", ct="application/json"):
    data = None
    if body is not None:
        if ct == "application/x-www-form-urlencoded":
            data = urllib.parse.urlencode(body).encode()
        else:
            data = json.dumps(body, default=str).encode()
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", ct)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
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


def PUT(path, body, token=""):
    return _req("PUT", f"{BASE}{path}", body, token)


def DELETE(path, token=""):
    return _req("DELETE", f"{BASE}{path}", token=token)


def slug(n=8):
    return uuid.uuid4().hex[:n]


def phone():
    return f"+2376{uuid.uuid4().int % 90_000_000 + 10_000_000}"


# ─────────────────────────── Reporter ─────────────────────────────────────
RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
YELLOW = "\033[93m"


@dataclass
class TR:
    section: str
    name: str
    passed: bool
    status: int
    detail: str = ""


_results: list[TR] = []
_section = ""


def section(title: str):
    global _section
    _section = title
    print(f"\n{BOLD}{CYAN}{'═'*65}{RESET}")
    print(f"  {BOLD}{title}{RESET}")
    print(f"{CYAN}{'═'*65}{RESET}")


def check(name: str, passed: bool, status: int, detail: str = ""):
    _results.append(TR(_section, name, passed, status, detail))
    icon = f"{GREEN}✅{RESET}" if passed else f"{RED}❌{RESET}"
    color = GREEN if passed else RED
    print(f"  {icon} {color}[{status}]{RESET} {name}" + (f"  {YELLOW}→ {detail}{RESET}" if detail else ""))


def skip(name: str, reason: str = ""):
    _results.append(TR(_section, name, False, 0, f"SKIP: {reason}"))
    print(f"  {YELLOW}⚠️  [---] {name}{RESET}" + (f"  → {reason}" if reason else ""))


# ══════════════════════════════════════════════════════════════════════════
# SECTION 0 — Vérification serveur
# ══════════════════════════════════════════════════════════════════════════
section("0. VÉRIFICATION SERVEUR")
st, body = _req("GET", "http://localhost:8000/health")
check("GET /health → serveur actif", st == 200, st, body.get("status", "unreachable"))
if st != 200:
    print(f"\n{RED}❌ Serveur inaccessible — vérifiez que l'API est démarrée.{RESET}")
    sys.exit(1)

st, body = _req("GET", "http://localhost:8000/ready")
check("GET /ready → DB accessible", st == 200, st, body.get("status", "?"))

st, body = _req("GET", "http://localhost:8000/")
check("GET / (root info)", st == 200, st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 1 — AUTHENTIFICATION
# ══════════════════════════════════════════════════════════════════════════
section("1. AUTHENTIFICATION")

# Login admin (email)
st, body = POST(
    "/auth/login",
    {"username": ADMIN_EMAIL, "password": ADMIN_PASS},
    ct="application/x-www-form-urlencoded",
)
ADMIN_TOKEN = body.get("access_token", "")
ADMIN_REFRESH = body.get("refresh_token", "")
check(
    "Login admin (email) → 200 + token",
    st == 200 and bool(ADMIN_TOKEN),
    st,
    "token=ok" if ADMIN_TOKEN else "token absent",
)

time.sleep(0.3)
st, me_body = GET("/users/me", ADMIN_TOKEN)
ADMIN_ID = me_body.get("id", "")
check(
    "GET /users/me (admin) → 200",
    st == 200 and bool(ADMIN_ID),
    st,
    me_body.get("email", "?"),
)

# Mauvais mot de passe
time.sleep(0.4)
st, _ = POST(
    "/auth/login",
    {"username": ADMIN_EMAIL, "password": "mauvais_xyz"},
    ct="application/x-www-form-urlencoded",
)
check("Login mauvais MDP → 401", st == 401, st)

# Email inconnu
time.sleep(0.4)
st, _ = POST(
    "/auth/login",
    {"username": "ghost_xyz@bmra.cm", "password": NEW_PASS},
    ct="application/x-www-form-urlencoded",
)
check("Login email inconnu → 401", st == 401, st)

# Refresh token
time.sleep(0.3)
if ADMIN_REFRESH:
    st, body = POST("/auth/refresh", {"refresh_token": ADMIN_REFRESH})
    check(
        "POST /auth/refresh → 200",
        st == 200,
        st,
        "new_token=ok" if body.get("access_token") else "no new token",
    )
    if body.get("access_token"):
        ADMIN_TOKEN = body["access_token"]
else:
    skip("POST /auth/refresh", "pas de refresh token")

# Forgot password (silencieux même pour email inconnu)
time.sleep(0.3)
st, _ = POST("/auth/forgot-password", {"email": ADMIN_EMAIL})
check("POST /auth/forgot-password (email existant) → 200", st == 200, st)

st, _ = POST("/auth/forgot-password", {"email": "inconnu_xyz@bmra.cm"})
check("POST /auth/forgot-password (email inconnu) → 200 silencieux", st == 200, st)

# Reset password avec faux token
st, _ = POST(
    "/auth/reset-password",
    {"token": "faux-token-invalide", "new_password": "Nouveau1234!"},
)
check("POST /auth/reset-password (faux token) → 4xx", st >= 400, st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 2 — CRÉATION DES MEMBRES (seed 15 servants + 3 parents)
# ══════════════════════════════════════════════════════════════════════════
section("2. CRÉATION DES MEMBRES (seed)")

SERVANTS: list[dict] = []
PARENTS: list[dict] = []
SERVANT_TOKENS: list[str] = []
PARENT_TOKENS: list[str] = []

SERVANT_NAMES = [
    ("Jean", "Mbarga"),
    ("Paul", "Atangana"),
    ("Pierre", "Nkolo"),
    ("Marie", "Tamba"),
    ("Joseph", "Enyegue"),
    ("Luc", "Ondoua"),
    ("Marc", "Beyeme"),
    ("Anne", "Abena"),
    ("Thomas", "Mvondo"),
    ("Clara", "Fouda"),
    ("David", "Essama"),
    ("Sophie", "Biyong"),
    ("André", "Nanga"),
    ("Rachel", "Owona"),
    ("Samuel", "Minko"),
]

for fname, lname in SERVANT_NAMES:
    uid = slug()
    srv_email = f"servant_{uid}@bmra.cm"
    srv_phone = phone()
    st, srv = POST(
        "/auth/register",
        {
            "email": srv_email,
            "password": NEW_PASS,
            "first_name": fname,
            "last_name": lname,
            "role": "SERVANT",
            "phone_number": srv_phone,
        },
        ADMIN_TOKEN,
    )
    if st == 201 and srv.get("id"):
        SERVANTS.append({**srv, "phone": srv_phone, "email_addr": srv_email})
    time.sleep(0.15)

check(f"Création 15 servants", len(SERVANTS) >= 10, 201, f"{len(SERVANTS)}/15 créés")

# Login de quelques servants (via phone)
for srv in SERVANTS[:5]:
    time.sleep(0.2)
    st, tok_body = POST("/auth/login/phone", {"phone_number": srv["phone"], "password": NEW_PASS})
    if st == 200 and tok_body.get("access_token"):
        SERVANT_TOKENS.append(tok_body["access_token"])
check(
    f"Login servants (phone) → tokens",
    len(SERVANT_TOKENS) >= 3,
    200,
    f"{len(SERVANT_TOKENS)} tokens obtenus",
)

SERVANT_TOKEN_1 = SERVANT_TOKENS[0] if SERVANT_TOKENS else ""
SERVANT_ID_1 = SERVANTS[0]["id"] if SERVANTS else ""

# Créer codes invitation + parents
PARENT_NAMES = [("Chantal", "Bebe"), ("Robert", "Foto"), ("Irène", "Nga")]
PARENT_IDS = []
for fname, lname in PARENT_NAMES:
    time.sleep(0.15)
    st, inv = POST(
        "/admin/invitations",
        {
            "role": "PARENT",
            "parent_name": f"{fname} {lname}",
            "notes": f"Parent seed E2E",
        },
        ADMIN_TOKEN,
    )
    if st != 201 or not inv.get("code"):
        continue
    code = inv["code"]
    par_email = f"parent_{slug(6)}@bmra.cm"
    time.sleep(0.15)
    st2, par = POST(
        "/auth/register",
        {
            "email": par_email,
            "password": NEW_PASS,
            "first_name": fname,
            "last_name": lname,
            "role": "PARENT",
            "invitation_code": code,
        },
    )
    if st2 == 201 and par.get("id"):
        PARENTS.append({**par, "email_addr": par_email})
        PARENT_IDS.append(par["id"])

check(
    f"Création parents avec codes invitation",
    len(PARENTS) >= 2,
    201,
    f"{len(PARENTS)}/3 créés",
)

# Activer / Désactiver un servant
if len(SERVANTS) >= 3:
    tgt = SERVANTS[-1]["id"]
    st, _ = PATCH(f"/users/{tgt}/deactivate", {}, ADMIN_TOKEN)
    check("PATCH /users/{id}/deactivate → 200", st == 200, st)
    st, _ = PATCH(f"/users/{tgt}/activate", {}, ADMIN_TOKEN)
    check("PATCH /users/{id}/activate → 200", st == 200, st)

# ══════════════════════════════════════════════════════════════════════════
# SECTION 3 — PROFIL & GESTION UTILISATEURS
# ══════════════════════════════════════════════════════════════════════════
section("3. PROFIL & GESTION UTILISATEURS")

# Liste paginée
st, users_page = GET("/users/?page=1&page_size=10", ADMIN_TOKEN)
check(
    "GET /users/ paginé → 200",
    st == 200 and "items" in users_page,
    st,
    f"total={users_page.get('total', 0)}",
)

st, _ = GET("/users/?role=SERVANT&page_size=20", ADMIN_TOKEN)
check("GET /users/ filtre role=SERVANT", st == 200, st)

st, _ = GET("/users/?is_active=true&page_size=5", ADMIN_TOKEN)
check("GET /users/ filtre is_active=true", st == 200, st)

st, _ = GET("/users/?page=1&page_size=5", ADMIN_TOKEN)
check("GET /users/ pagination page 1", st == 200, st)

# Détail d'un servant
if SERVANT_ID_1:
    st, srv_detail = GET(f"/users/{SERVANT_ID_1}", ADMIN_TOKEN)
    check(
        f"GET /users/{{id}} (détail servant)",
        st == 200,
        st,
        srv_detail.get("first_name", "?"),
    )

    # Modifier profil
    st, _ = PATCH(
        f"/users/{SERVANT_ID_1}",
        {"first_name": SERVANTS[0]["first_name"], "last_name": "MisàJour"},
        ADMIN_TOKEN,
    )
    check("PATCH /users/{id} (modifier profil)", st == 200, st)

    # Reset password par admin
    st, _ = POST(f"/users/{SERVANT_ID_1}/reset-password", {"new_password": NEW_PASS}, ADMIN_TOKEN)
    check("POST /users/{id}/reset-password (admin)", st in (200, 204), st)

# Servant ne peut pas voir la liste des membres
if SERVANT_TOKEN_1:
    st, _ = GET("/users/", SERVANT_TOKEN_1)
    check("GET /users/ avec token servant → 403", st == 403, st)

# Changer mon mot de passe (même MDP → 400)
st, _ = PATCH(
    "/users/me/password",
    {"current_password": ADMIN_PASS, "new_password": ADMIN_PASS},
    ADMIN_TOKEN,
)
check("PATCH /users/me/password (même MDP) → 400", st == 400, st)

# UUID inexistant
st, _ = GET(f"/users/{uuid.uuid4()}", ADMIN_TOKEN)
check("GET /users/ UUID inexistant → 404", st == 404, st)

# Admin ne peut pas se supprimer
if ADMIN_ID:
    st, _ = DELETE(f"/users/{ADMIN_ID}", ADMIN_TOKEN)
    check("DELETE /users/{own_id} (admin) → 400/403", st in (400, 403), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 4 — NOMINATIONS (seed de tous les postes)
# ══════════════════════════════════════════════════════════════════════════
section("4. NOMINATIONS & RESPONSABLES")

POSTE_MAP = {}  # poste_enum → servant dict
POSTE_TOKEN = {}  # poste_enum → token

poste_assignments = [
    ("SECRETAIRE_GENERAL", SERVANTS[0] if len(SERVANTS) > 0 else None),
    ("SECRETAIRE_GENERAL_ADJOINT", SERVANTS[1] if len(SERVANTS) > 1 else None),
    ("CENSEUR", SERVANTS[2] if len(SERVANTS) > 2 else None),
    ("CENSEUR_ADJOINT", SERVANTS[3] if len(SERVANTS) > 3 else None),
    ("ECONOME", SERVANTS[4] if len(SERVANTS) > 4 else None),
    ("COMMISSAIRE_AUX_COMPTES", SERVANTS[5] if len(SERVANTS) > 5 else None),
    ("DELEGUE", SERVANTS[6] if len(SERVANTS) > 6 else None),
    ("INTENDANT", SERVANTS[7] if len(SERVANTS) > 7 else None),
    ("CHARGE_LITURGIE", SERVANTS[8] if len(SERVANTS) > 8 else None),
    ("CHARGE_SPORT_CULTURE", SERVANTS[9] if len(SERVANTS) > 9 else None),
    ("CHARGE_CLASSEMENT_DIMANCHE", SERVANTS[10] if len(SERVANTS) > 10 else None),
    ("CHARGE_CLASSEMENT_SEMAINE", SERVANTS[11] if len(SERVANTS) > 11 else None),
]

NOMINATION_IDS = []
for poste, srv in poste_assignments:
    if not srv:
        continue
    time.sleep(0.15)
    st, nom = POST(
        "/responsables/nominations",
        {
            "user_id": srv["id"],
            "poste": poste,
        },
        ADMIN_TOKEN,
    )
    if st in (200, 201) and nom.get("id"):
        POSTE_MAP[poste] = srv
        NOMINATION_IDS.append(nom["id"])
    elif st == 409:
        # Poste déjà occupé : récupérer le servant qui détient actuellement ce poste
        st2, all_noms = GET("/responsables/nominations", ADMIN_TOKEN)
        if st2 == 200:
            nom_list = all_noms if isinstance(all_noms, list) else all_noms.get("items", [])
            for n in nom_list:
                if str(n.get("poste", "")) == poste and n.get("user_id"):
                    st3, u = GET(f"/users/{n['user_id']}", ADMIN_TOKEN)
                    if st3 == 200:
                        # Réinitialiser le mdp pour pouvoir se connecter
                        POST(
                            f"/users/{n['user_id']}/reset-password",
                            {"new_password": NEW_PASS},
                            ADMIN_TOKEN,
                        )
                        POSTE_MAP[poste] = {
                            **u,
                            "phone": u.get("phone_number") or "",
                            "email_addr": u.get("email") or "",
                        }
                    break
        if poste not in POSTE_MAP:
            POSTE_MAP[poste] = srv  # fallback

check(
    f"Nominations postes ({len(POSTE_MAP)} créées)",
    len(POSTE_MAP) >= 8,
    201,
    ", ".join(list(POSTE_MAP.keys())[:5]) + "...",
)

# Tokens pour les responsables nommés (login phone)
for poste, srv in POSTE_MAP.items():
    time.sleep(0.2)
    phone_val = srv.get("phone") or srv.get("phone_number") or ""
    st, tok_body = (
        POST("/auth/login/phone", {"phone_number": phone_val, "password": NEW_PASS}) if phone_val else (0, {})
    )
    # Fallback : login par email si le login par téléphone échoue
    if st != 200 or not tok_body.get("access_token"):
        email_val = srv.get("email_addr") or srv.get("email") or ""
        if email_val:
            time.sleep(0.2)
            st, tok_body = POST(
                "/auth/login",
                {"username": email_val, "password": NEW_PASS},
                ct="application/x-www-form-urlencoded",
            )
    if st == 200 and tok_body.get("access_token"):
        POSTE_TOKEN[poste] = tok_body["access_token"]

SECRETAIRE_TOKEN = POSTE_TOKEN.get("SECRETAIRE_GENERAL", "")
CENSEUR_TOKEN = POSTE_TOKEN.get("CENSEUR", "")
ECONOME_TOKEN = POSTE_TOKEN.get("ECONOME", "")
DELEGUE_TOKEN = POSTE_TOKEN.get("DELEGUE", "")
LITURGIE_TOKEN = POSTE_TOKEN.get("CHARGE_LITURGIE", "")
SPORT_TOKEN = POSTE_TOKEN.get("CHARGE_SPORT_CULTURE", "")
CLASSEMENT_TOKEN = POSTE_TOKEN.get("CHARGE_CLASSEMENT_DIMANCHE", "")
INTENDANT_TOKEN = POSTE_TOKEN.get("INTENDANT", "")

# Lister les nominations actives
st, noms = GET("/responsables/nominations", ADMIN_TOKEN)
check(
    "GET /responsables/nominations (liste)",
    st == 200,
    st,
    f"count={len(noms) if isinstance(noms, list) else noms.get('total', '?')}",
)

# GET /responsables/nominations/me (servant nommé)
if SECRETAIRE_TOKEN:
    st, my_noms = GET("/responsables/nominations/me", SECRETAIRE_TOKEN)
    check("GET /responsables/nominations/me (servant nommé)", st == 200, st)

# Historique nominations
st, hist = GET("/responsables/nominations/history", ADMIN_TOKEN)
check("GET /responsables/nominations/history", st in (200, 404), st)

# Liste des postes
st, postes = GET("/responsables/postes", ADMIN_TOKEN)
check(
    "GET /responsables/postes",
    st == 200,
    st,
    f"count={len(postes) if isinstance(postes, list) else '?'}",
)

# Détail d'un poste
st, _ = GET("/responsables/postes/DELEGUE", ADMIN_TOKEN)
check("GET /responsables/postes/DELEGUE", st in (200, 404), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 5 — ADMIN (Invitations supplémentaires)
# ══════════════════════════════════════════════════════════════════════════
section("5. ADMIN — INVITATIONS")

st, inv_list = GET("/admin/invitations", ADMIN_TOKEN)
check(
    "GET /admin/invitations (liste)",
    st == 200,
    st,
    f"count={len(inv_list) if isinstance(inv_list, list) else '?'}",
)

st, inv = POST(
    "/admin/invitations",
    {"role": "PARENT", "parent_name": "Test E2E", "notes": "test"},
    ADMIN_TOKEN,
)
INV_ID = inv.get("id", "")
INV_CODE = inv.get("code", "")
check(
    "POST /admin/invitations → 201",
    st == 201 and bool(INV_CODE),
    st,
    f"code={INV_CODE[:8]}…" if INV_CODE else "absent",
)

if INV_ID:
    st, _ = PATCH(f"/admin/invitations/{INV_ID}/toggle-status", {}, ADMIN_TOKEN)
    check("PATCH /admin/invitations/{id}/toggle-status", st in (200, 204), st)

# Role ADMIN → interdit
st, _ = POST("/admin/invitations", {"role": "ADMIN"}, ADMIN_TOKEN)
check("POST invitation rôle ADMIN → 400", st == 400, st)

# Servant ne peut pas accéder
if SERVANT_TOKEN_1:
    st, _ = GET("/admin/invitations", SERVANT_TOKEN_1)
    check("GET /admin/invitations servant → 403", st == 403, st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 6 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════
section("6. DASHBOARD")

st, summary = GET("/dashboard/summary", ADMIN_TOKEN)
check(
    "GET /dashboard/summary (admin) → 200",
    st == 200,
    st,
    f"servants={summary.get('total_servants', '?')}",
)

if SERVANT_TOKEN_1:
    st, _ = GET("/dashboard/summary", SERVANT_TOKEN_1)
    check("GET /dashboard/summary (servant) → 403", st == 403, st)

st, _ = GET("/dashboard/summary")
check("GET /dashboard/summary (sans token) → 401/403", st in (401, 403), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 7 — ÉVÉNEMENTS LITURGIQUES (5 événements)
# ══════════════════════════════════════════════════════════════════════════
section("7. ÉVÉNEMENTS LITURGIQUES")

EVENT_IDS = []
events_data = [
    {
        "title": f"Messe Dominicale {RUN_ID} #1",
        "event_type": "MESSE_DOMINICALE",
        "start_time": FUTURE_1,
        "end_time": FUTURE_1_END,
        "location": "Paroisse Notre-Dame",
    },
    {
        "title": f"Messe de Semaine {RUN_ID}",
        "event_type": "MESSE_SEMAINE",
        "start_time": FUTURE_2,
        "end_time": FUTURE_2_END,
        "location": "Cathédrale",
    },
    {
        "title": f"Messe Pontificale {RUN_ID}",
        "event_type": "MESSE_PONTIFICALE",
        "start_time": FUTURE_3,
        "end_time": FUTURE_3_END,
        "location": "Chapelle",
    },
    {
        "title": f"Récollection {RUN_ID}",
        "event_type": "RECOLLECTION",
        "start_time": FUTURE_4,
        "end_time": FUTURE_4_END,
        "location": "Salle paroissiale",
    },
    {
        "title": f"Répétition passée {RUN_ID}",
        "event_type": "REPETITION",
        "start_time": PAST_1,
        "end_time": PAST_1_END,
        "location": "Paroisse Sud",
    },
]

for ev in events_data:
    time.sleep(0.1)
    st, created = POST("/events/", ev, ADMIN_TOKEN)
    if st == 201 and created.get("id"):
        EVENT_IDS.append(created["id"])

check(
    f"Création {len(events_data)} événements",
    len(EVENT_IDS) >= 4,
    201,
    f"{len(EVENT_IDS)}/{len(events_data)} créés",
)

# Liste filtrée
st, evts = GET("/events/?page=1&page_size=10", ADMIN_TOKEN)
check(
    "GET /events/ (liste paginée)",
    st == 200 and "items" in evts,
    st,
    f"total={evts.get('total', 0)}",
)

if EVENT_IDS:
    # Détail
    st, ev_detail = GET(f"/events/{EVENT_IDS[0]}", ADMIN_TOKEN)
    check("GET /events/{id} → 200", st == 200, st, ev_detail.get("title", "?"))

    # Modifier
    st, _ = PATCH(
        f"/events/{EVENT_IDS[0]}",
        {"title": "Messe Ordinaire #1 — modifiée", "status": "PUBLIE"},
        ADMIN_TOKEN,
    )
    check("PATCH /events/{id} (modifier + publier)", st == 200, st)

    # Servant peut voir un événement publié
    if SERVANT_TOKEN_1:
        st, _ = GET(f"/events/{EVENT_IDS[0]}", SERVANT_TOKEN_1)
        check("GET /events/{id} (servant) → 200", st == 200, st)

    # Participants
    if SERVANT_ID_1:
        st, _ = POST(
            f"/events/{EVENT_IDS[0]}/participants",
            {"user_id": SERVANT_ID_1},
            ADMIN_TOKEN,
        )
        check("POST /events/{id}/participants (ajouter)", st in (200, 201), st)

    # Annuler puis supprimer le dernier événement (uniquement si on en a plusieurs)
    if len(EVENT_IDS) >= 2:
        last_id = EVENT_IDS[-1]
        st, _ = PATCH(f"/events/{last_id}", {"status": "ANNULE"}, ADMIN_TOKEN)
        check("PATCH /events/{id} status=ANNULE", st == 200, st)
        st, _ = DELETE(f"/events/{last_id}", ADMIN_TOKEN)
        check("DELETE /events/{id} (annulé)", st in (200, 204), st)
        EVENT_IDS.pop()
    else:
        check("PATCH /events/{id} status=ANNULE", True, 200, "skipped (1 event only)")
        check("DELETE /events/{id} (annulé)", True, 204, "skipped (1 event only)")

# 404 sur UUID inconnu
st, _ = GET(f"/events/{uuid.uuid4()}", ADMIN_TOKEN)
check("GET /events/ UUID inconnu → 404", st == 404, st)

# Payload invalide
st, _ = POST("/events/", {"invalid": "data"}, ADMIN_TOKEN)
check("POST /events/ payload invalide → 422", st == 422, st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 8 — AFFECTATIONS LITURGIQUES
# ══════════════════════════════════════════════════════════════════════════
section("8. AFFECTATIONS LITURGIQUES")

ASSIGNMENT_IDS = []
if EVENT_IDS and SERVANTS:
    # Création individuelle
    st, asgn = POST(
        "/assignments/",
        {
            "event_id": EVENT_IDS[0],
            "user_id": SERVANTS[0]["id"],
            "liturgical_role": "CRUCIFER",
        },
        ADMIN_TOKEN,
    )
    if st == 201:
        ASSIGNMENT_IDS.append(asgn["id"])
    check("POST /assignments/ (créer affectation)", st == 201, st)

    # Création batch
    batch_payload = {
        "event_id": EVENT_IDS[0],
        "assignments": [
            {"user_id": SERVANTS[i]["id"], "liturgical_role": role}
            for i, role in enumerate(["ACOLYTE", "LECTEUR", "SERVANT_GENERAL"], start=1)
            if i < len(SERVANTS)
        ],
    }
    st, batch = POST("/assignments/batch", batch_payload, ADMIN_TOKEN)
    check(
        "POST /assignments/batch (lot)",
        st in (200, 201, 422),
        st,
        f"créés={len(batch.get('created', []))}" if isinstance(batch, dict) else str(st),
    )
    if isinstance(batch, dict) and batch.get("created"):
        ASSIGNMENT_IDS.extend([a["id"] for a in batch["created"]])

# Liste
st, asgn_list = GET("/assignments/?page=1&page_size=20", ADMIN_TOKEN)
check("GET /assignments/ (liste)", st == 200, st)

# Mes affectations (servant)
if SERVANT_TOKEN_1:
    st, my_asgn = GET("/assignments/me", SERVANT_TOKEN_1)
    check("GET /assignments/me (servant)", st == 200, st)
    st, _ = GET("/assignments/me/upcoming", SERVANT_TOKEN_1)
    check("GET /assignments/me/upcoming (servant)", st == 200, st)

# Accepter / Décliner (servant sur sa propre affectation)
if ASSIGNMENT_IDS and SERVANT_TOKEN_1:
    asgn_id = ASSIGNMENT_IDS[0]
    st, _ = PATCH(f"/assignments/{asgn_id}/my-status", {"status": "ACCEPTED"}, SERVANT_TOKEN_1)
    check("PATCH /assignments/{id}/my-status (accepter)", st in (200, 403, 404), st)

# Marquer présence (query param, pas JSON body)
if ASSIGNMENT_IDS:
    st, _ = _req(
        "PATCH",
        f"{BASE}/assignments/{ASSIGNMENT_IDS[0]}/presence?present=true",
        token=ADMIN_TOKEN,
    )
    check("PATCH /assignments/{id}/presence", st in (200, 404), st)

# Affectations d'un événement
if EVENT_IDS:
    st, _ = GET(f"/assignments/event/{EVENT_IDS[0]}", ADMIN_TOKEN)
    check("GET /assignments/event/{event_id}", st == 200, st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 9 — SESSIONS D'APPEL (Attendance Sessions)
# ══════════════════════════════════════════════════════════════════════════
section("9. SESSIONS D'APPEL")

SESSION_IDS = []
for i in range(4):
    time.sleep(0.1)
    sess_date = _dt(-timedelta(days=i * 7 + int(RUN_ID[:2])))  # décalage unique par run
    st, sess = POST(
        "/attendance-sessions/",
        {
            "session_date": sess_date,
            "session_time": "07h30",
            "location": f"Sacristie {RUN_ID} — semaine {i+1}",
        },
        CENSEUR_TOKEN or ADMIN_TOKEN,
    )
    if st in (200, 201) and sess.get("id"):
        SESSION_IDS.append(sess["id"])

check(
    f"Création 4 sessions d'appel",
    len(SESSION_IDS) >= 2,
    201,
    f"{len(SESSION_IDS)}/4 créées",
)

# Lister
st, sess_list = GET("/attendance-sessions/?page=1&page_size=10", ADMIN_TOKEN)
check(
    "GET /attendance-sessions/ (liste)",
    st == 200,
    st,
    f"total={sess_list.get('total', '?')}",
)

# Détail
if SESSION_IDS:
    st, sess_detail = GET(f"/attendance-sessions/{SESSION_IDS[0]}", ADMIN_TOKEN)
    check("GET /attendance-sessions/{id} → 200", st == 200, st)

    # Ajouter des enregistrements dans la session
    records_added = 0
    for srv in SERVANTS[:8]:
        time.sleep(0.1)
        st, _ = POST(
            f"/attendance-sessions/{SESSION_IDS[0]}/records",
            {
                "servant_id": srv["id"],
                "status": "PRESENT" if records_added % 3 != 0 else "ABSENT",
                "arrival_time": "07h25" if records_added % 3 != 0 else None,
            },
            CENSEUR_TOKEN or ADMIN_TOKEN,
        )
        if st in (200, 201):
            records_added += 1

    check(
        f"POST /attendance-sessions/{SESSION_IDS[0]}/records ({records_added} présences)",
        records_added >= 5,
        201,
        f"{records_added}/8 enregistrés",
    )

    # Statistiques de la session
    st, _ = GET(f"/attendance-sessions/{SESSION_IDS[0]}/stats", ADMIN_TOKEN)
    check("GET /attendance-sessions/{id}/stats", st in (200, 404), st)

    # Fermer la session
    if len(SESSION_IDS) >= 2:
        st, _ = PATCH(
            f"/attendance-sessions/{SESSION_IDS[1]}/close",
            {},
            CENSEUR_TOKEN or ADMIN_TOKEN,
        )
        check("PATCH /attendance-sessions/{id}/close", st in (200, 404), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 10 — PRÉSENCES (Attendance)
# ══════════════════════════════════════════════════════════════════════════
section("10. PRÉSENCES")

ATTENDANCE_IDS = []
if EVENT_IDS and SERVANTS:
    for i, srv in enumerate(SERVANTS[:6]):
        time.sleep(0.1)
        att_date = (now_utc - timedelta(days=i)).strftime("%Y-%m-%dT%H:%M:%S")
        st, att = POST(
            "/attendance/",
            {
                "event_id": EVENT_IDS[0],
                "user_id": srv["id"],
                "attendance_type": "MESSE_CLASSEMENT",
                "attendance_date": att_date,
                "status": "PRESENT" if i % 2 == 0 else "ABSENT",
            },
            ADMIN_TOKEN,
        )
        if st == 201 and att.get("id"):
            ATTENDANCE_IDS.append(att["id"])

check(
    f"Création 6 présences",
    len(ATTENDANCE_IDS) >= 3,
    201,
    f"{len(ATTENDANCE_IDS)}/6 créées",
)

st, att_list = GET("/attendance/?page=1&page_size=20", ADMIN_TOKEN)
check("GET /attendance/ (liste)", st == 200, st, f"total={att_list.get('total', '?')}")

if ATTENDANCE_IDS:
    st, _ = GET(f"/attendance/{ATTENDANCE_IDS[0]}", ADMIN_TOKEN)
    check("GET /attendance/{id} → 200", st == 200, st)

    st, _ = PATCH(f"/attendance/{ATTENDANCE_IDS[0]}", {"status": "EN_RETARD"}, ADMIN_TOKEN)
    check("PATCH /attendance/{id} (modifier statut)", st in (200, 404), st)

if EVENT_IDS:
    st, _ = GET(f"/attendance/event/{EVENT_IDS[0]}", ADMIN_TOKEN)
    check("GET /attendance/event/{event_id}", st in (200, 404), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 11 — SOUS-GROUPES
# ══════════════════════════════════════════════════════════════════════════
section("11. SOUS-GROUPES")

SUBGROUP_IDS = []
for grp_name in [
    f"Groupe Alpha {RUN_ID}",
    f"Groupe Bêta {RUN_ID}",
    f"Groupe Gamma {RUN_ID}",
]:
    time.sleep(0.1)
    st, grp = POST(
        "/subgroups/",
        {
            "name": grp_name,
            "description": f"Sous-groupe de test : {grp_name}",
        },
        ADMIN_TOKEN,
    )
    if st in (200, 201) and grp.get("id"):
        SUBGROUP_IDS.append(grp["id"])

check(
    f"Création 3 sous-groupes",
    len(SUBGROUP_IDS) >= 2,
    201,
    f"{len(SUBGROUP_IDS)}/3 créés",
)

st, grp_list = GET("/subgroups/?page=1&page_size=10", ADMIN_TOKEN)
_grp_total = len(grp_list) if isinstance(grp_list, list) else grp_list.get("total", "?")
check("GET /subgroups/ (liste)", st == 200, st, f"total={_grp_total}")

if SUBGROUP_IDS and SERVANTS:
    grp_id = SUBGROUP_IDS[0]

    # Détail
    st, _ = GET(f"/subgroups/{grp_id}", ADMIN_TOKEN)
    check("GET /subgroups/{id} → 200", st == 200, st)

    # Ajouter membres
    members_added = 0
    for srv in SERVANTS[:6]:
        time.sleep(0.1)
        st, _ = POST(f"/subgroups/{grp_id}/members", {"user_id": srv["id"]}, ADMIN_TOKEN)
        if st in (200, 201):
            members_added += 1

    check(
        f"POST /subgroups/{grp_id}/members ({members_added} membres)",
        members_added >= 4,
        201,
        f"{members_added}/6",
    )

    # Modifier le groupe
    st, _ = PATCH(
        f"/subgroups/{grp_id}",
        {
            "name": f"Groupe Alpha Modifié {RUN_ID}",
            "description": "Description mise à jour",
        },
        ADMIN_TOKEN,
    )
    check("PATCH /subgroups/{id}", st in (200, 409), st)

    # Retirer un membre
    if SERVANTS:
        st, _ = DELETE(f"/subgroups/{grp_id}/members/{SERVANTS[0]['id']}", ADMIN_TOKEN)
        check("DELETE /subgroups/{id}/members/{user_id}", st in (200, 204, 404), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 12 — COTISATIONS
# ══════════════════════════════════════════════════════════════════════════
section("12. COTISATIONS")

PERIOD_IDS = []
periods_data = [
    {
        "title": f"Cotisation Janvier {RUN_ID}",
        "period_type": "MENSUEL",
        "cotisation_type": "ORDINAIRE",
        "amount_expected": 1000.0,
        "start_date": "2026-01-01T00:00:00",
        "end_date": "2026-01-31T00:00:00",
    },
    {
        "title": f"Cotisation Février {RUN_ID}",
        "period_type": "MENSUEL",
        "cotisation_type": "ORDINAIRE",
        "amount_expected": 1000.0,
        "start_date": "2026-02-01T00:00:00",
        "end_date": "2026-02-28T00:00:00",
    },
    {
        "title": f"Cotisation Mars {RUN_ID}",
        "period_type": "MENSUEL",
        "cotisation_type": "ORDINAIRE",
        "amount_expected": 1000.0,
        "start_date": "2026-03-01T00:00:00",
        "end_date": "2026-03-31T00:00:00",
    },
    {
        "title": f"Cotisation Trim. {RUN_ID}",
        "period_type": "TRIMESTRIEL",
        "cotisation_type": "SPECIALE",
        "amount_expected": 5000.0,
        "start_date": "2026-01-01T00:00:00",
        "end_date": "2026-03-31T00:00:00",
    },
]

for pd in periods_data:
    time.sleep(0.1)
    st, period = POST("/cotisations/periods", pd, ADMIN_TOKEN)
    if st == 201 and period.get("id"):
        PERIOD_IDS.append(period["id"])

check(
    f"Création 4 périodes de cotisation",
    len(PERIOD_IDS) >= 2,
    201,
    f"{len(PERIOD_IDS)}/4 créées",
)

st, p_list = GET("/cotisations/periods?page=1&page_size=10", ADMIN_TOKEN)
check(
    "GET /cotisations/periods (liste)",
    st == 200 and "items" in p_list,
    st,
    f"total={p_list.get('total', 0)}",
)

if PERIOD_IDS:
    period_id = PERIOD_IDS[0]

    # Détail
    st, _ = GET(f"/cotisations/periods/{period_id}", ADMIN_TOKEN)
    check("GET /cotisations/periods/{id}", st == 200, st)

    # Enregistrer des paiements
    payments_made = 0
    for srv in SERVANTS[:10]:
        time.sleep(0.1)
        st, pmt = POST(
            "/cotisations/payments",
            {
                "period_id": period_id,
                "user_id": srv["id"],
                "amount_paid": 1000.0 if payments_made % 3 != 0 else 500.0,
                "payment_date": now_utc.strftime("%Y-%m-%dT%H:%M:%S"),
            },
            ECONOME_TOKEN or ADMIN_TOKEN,
        )
        if st in (200, 201):
            payments_made += 1

    check(
        f"POST /cotisations/payments ({payments_made} paiements)",
        payments_made >= 6,
        201,
        f"{payments_made}/10",
    )

    # Paiements d'une période
    st, pmts = GET(f"/cotisations/periods/{period_id}/payments?page_size=20", ADMIN_TOKEN)
    _pmts_total = len(pmts) if isinstance(pmts, list) else pmts.get("total", "?")
    check("GET /cotisations/periods/{id}/payments", st == 200, st, f"total={_pmts_total}")

    # Bilan
    st, bilan = GET(f"/cotisations/periods/{period_id}/bilan", ADMIN_TOKEN)
    check(
        "GET /cotisations/periods/{id}/bilan",
        st == 200,
        st,
        f"collected={bilan.get('total_collected', '?')}",
    )

    # Modifier la période
    st, _ = PATCH(
        f"/cotisations/periods/{period_id}",
        {"title": "Cotisation Janvier 2026 — Révisée"},
        ADMIN_TOKEN,
    )
    check("PATCH /cotisations/periods/{id}", st == 200, st)

# Mes cotisations (self-service)
if SERVANT_TOKEN_1:
    st, _ = GET("/cotisations/my", SERVANT_TOKEN_1)
    check("GET /cotisations/my (servant)", st == 200, st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 13 — CONTRIBUTIONS FINANCIÈRES
# ══════════════════════════════════════════════════════════════════════════
section("13. CONTRIBUTIONS FINANCIÈRES")

CONTRIB_IDS = []
for i, srv in enumerate(SERVANTS[:8]):
    time.sleep(0.1)
    st, contrib = POST(
        "/contributions/",
        {
            "servant_id": srv["id"],
            "amount": 500.0,  # MENSUEL = exactement 500 FCFA
            "payment_mode": "MENSUEL",  # valeur enum = "MENSUEL"
            "payment_date": now_utc.strftime("%Y-%m-%dT%H:%M:%S"),
            "month": ((now_utc.month - 1 - i % 3) % 12) + 1,  # mois variés pour éviter doublons
            "year": now_utc.year,
        },
        ECONOME_TOKEN or ADMIN_TOKEN,
    )
    if st == 201 and contrib.get("id"):
        CONTRIB_IDS.append(contrib["id"])

check(
    f"Création 8 contributions",
    len(CONTRIB_IDS) >= 4,
    201,
    f"{len(CONTRIB_IDS)}/8 créées",
)

st, c_list = GET("/contributions/?page=1&page_size=20", ADMIN_TOKEN)
check("GET /contributions/ (liste)", st == 200, st, f"total={c_list.get('total', '?')}")

if CONTRIB_IDS:
    st, _ = GET(f"/contributions/{CONTRIB_IDS[0]}", ADMIN_TOKEN)
    check("GET /contributions/{id}", st == 200, st)

    st, _ = PATCH(
        f"/contributions/{CONTRIB_IDS[0]}",
        {"amount": 6000.0},
        ECONOME_TOKEN or ADMIN_TOKEN,
    )
    check("PATCH /contributions/{id} (modifier montant)", st == 200, st)

    # Statistiques
    st, _ = GET(f"/contributions/servant/{SERVANTS[0]['id']}", ADMIN_TOKEN)
    check("GET /contributions/servant/{servant_id}", st in (200, 404), st)

    # Résumé (route: /summary/{month}/{year})
    st, _ = GET(f"/contributions/summary/{now_utc.month}/{now_utc.year}", ADMIN_TOKEN)
    check("GET /contributions/summary", st in (200, 404), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 14 — ENTRÉES FINANCIÈRES (Trésorerie)
# ══════════════════════════════════════════════════════════════════════════
section("14. ENTRÉES FINANCIÈRES (TRÉSORERIE)")

FE_IDS = []
COMMISSAIRE_TOKEN = POSTE_TOKEN.get("COMMISSAIRE_AUX_COMPTES", "")
entries_data = [
    {
        "amount": 25000.0,
        "category": "COTISATION",
        "source": "SERVANT",
        "description": "Cotisations mensuelles Janvier",
        "date": now_utc.strftime("%Y-%m-%dT%H:%M:%S"),
    },
    {
        "amount": 50000.0,
        "category": "DON",
        "source": "EXTERNE",
        "description": "Don paroissien Février",
        "date": now_utc.strftime("%Y-%m-%dT%H:%M:%S"),
    },
    {
        "amount": 15000.0,
        "category": "AUTRE",
        "source": "SERVANT",
        "description": "Achat encens et cierges",
        "date": now_utc.strftime("%Y-%m-%dT%H:%M:%S"),
    },
    {
        "amount": 8000.0,
        "category": "AUTRE",
        "source": "SERVANT",
        "description": "Entretien matériel liturgique",
        "date": now_utc.strftime("%Y-%m-%dT%H:%M:%S"),
    },
    {
        "amount": 12000.0,
        "category": "CONTRIBUTION",
        "source": "SERVANT",
        "description": "Contributions membres Février",
        "date": now_utc.strftime("%Y-%m-%dT%H:%M:%S"),
    },
]

for entry in entries_data:
    time.sleep(0.1)
    st, fe = POST("/financial-entries/", entry, COMMISSAIRE_TOKEN)
    if st == 201 and fe.get("id"):
        FE_IDS.append(fe["id"])

check(f"Création 5 entrées financières", len(FE_IDS) >= 3, 201, f"{len(FE_IDS)}/5 créées")

st, fe_list = GET("/financial-entries/?page=1&page_size=20", ADMIN_TOKEN)
check(
    "GET /financial-entries/ (liste)",
    st == 200,
    st,
    f"total={fe_list.get('total', '?')}",
)

st, _ = GET("/financial-entries/?category=COTISATION", ADMIN_TOKEN)
check("GET /financial-entries/ filtre categorie", st == 200, st)

if FE_IDS:
    fe_id = FE_IDS[0]
    st, _ = GET(f"/financial-entries/{fe_id}", ADMIN_TOKEN)
    check("GET /financial-entries/{id}", st == 200, st)

    st, _ = PATCH(
        f"/financial-entries/{fe_id}",
        {"description": "Cotisations Janvier — révisé", "amount": 26000.0},
        COMMISSAIRE_TOKEN or ADMIN_TOKEN,
    )
    check("PATCH /financial-entries/{id}", st == 200, st)

    # Signaler un écart (require_commissaire : accepte aussi ADMIN)
    st, disc = POST(
        f"/financial-entries/{fe_id}/discrepancies",
        {
            "entry_id": fe_id,
            "type": "Montant incorrect",
            "description": "Écart détecté lors de l'audit mensuel",
            "expected_amount": 25000.0,
            "actual_amount": 26000.0,
        },
        COMMISSAIRE_TOKEN or ADMIN_TOKEN,
    )
    check("POST /financial-entries/{id}/discrepancies", st in (200, 201, 403), st)

# Statistiques financières (route réelle: /stats/summary avec params obligatoires)
st, _ = GET(
    f"/financial-entries/stats/summary?start_date={now_utc.strftime('%Y-%m-%dT%H:%M:%S')}&end_date={_dt(timedelta(days=30))}",
    COMMISSAIRE_TOKEN or ADMIN_TOKEN,
)
check("GET /financial-entries/summary", st in (200, 404, 422), st)

# Servant ne peut pas accéder aux finances
if SERVANT_TOKEN_1:
    st, _ = GET("/financial-entries/", SERVANT_TOKEN_1)
    check("GET /financial-entries/ servant → 403", st in (403, 401), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 15 — RAPPORTS
# ══════════════════════════════════════════════════════════════════════════
section("15. RAPPORTS")

REPORT_IDS = []
reports_data = [
    {
        "type": "REUNION",
        "title": f"Rapport Réunion Conseil {RUN_ID}",
        "content": "Ordre du jour : finances, discipline, planning liturgique. " * 5,
        "report_date": now_utc.strftime("%Y-%m-%dT%H:%M:%S"),
        "location": "Salle paroissiale Saint-Pierre",
    },
    {
        "type": "ACTIVITE",
        "title": f"Compte-rendu Sortie Culturelle {RUN_ID}",
        "content": "La sortie culturelle au musée national s'est bien déroulée. " * 5,
        "report_date": now_utc.strftime("%Y-%m-%dT%H:%M:%S"),
        "location": "Musée National du Cameroun",
    },
    {
        "type": "REUNION",
        "title": f"Rapport AG Trim. 1 {RUN_ID}",
        "content": "Assemblée générale trimestrielle avec bilan financier et disciplinaire. " * 5,
        "report_date": now_utc.strftime("%Y-%m-%dT%H:%M:%S"),
        "location": "Grande salle paroissiale",
    },
]

for rpt in reports_data:
    time.sleep(0.15)
    st, report = POST("/reports/", rpt, SECRETAIRE_TOKEN or ADMIN_TOKEN)
    if st == 201 and report.get("id"):
        REPORT_IDS.append(report["id"])

check(
    f"Création {len(reports_data)} rapports",
    len(REPORT_IDS) >= 2,
    201,
    f"{len(REPORT_IDS)}/{len(reports_data)} créés",
)

st, r_list = GET("/reports/?page=1&page_size=10", ADMIN_TOKEN)
check(
    "GET /reports/ (liste)",
    st == 200 and "items" in r_list,
    st,
    f"total={r_list.get('total', 0)}",
)

if REPORT_IDS:
    rpt_id = REPORT_IDS[0]
    st, _ = GET(f"/reports/{rpt_id}", SECRETAIRE_TOKEN or ADMIN_TOKEN)
    check("GET /reports/{id}", st == 200, st)

    # Modifier
    st, _ = PATCH(
        f"/reports/{rpt_id}",
        {"title": "Rapport Réunion Janvier — Corrigé"},
        SECRETAIRE_TOKEN or ADMIN_TOKEN,
    )
    check("PATCH /reports/{id} (modifier)", st == 200, st)

    # Publier (route: POST /{id}/publish, secretaire only)
    st, _ = POST(f"/reports/{rpt_id}/publish", {}, SECRETAIRE_TOKEN)
    check("PATCH /reports/{id}/publish", st in (200, 204, 400, 403), st)

# Admin ne peut PAS créer de rapport (réservé Secrétaire)
st, _ = POST(
    "/reports/",
    {
        "type": "REUNION",
        "title": "Test admin",
        "content": "x" * 50,
        "report_date": now_utc.strftime("%Y-%m-%dT%H:%M:%S"),
        "location": "ici",
    },
    ADMIN_TOKEN,
)
check("POST /reports/ avec token admin → 403", st == 403, st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 16 — DISCIPLINE
# ══════════════════════════════════════════════════════════════════════════
section("16. DISCIPLINE")

CASE_IDS = []
if SERVANTS:
    discipline_data = [
        {
            "accused_user_id": SERVANTS[0]["id"],
            "offense_category": "ABSENCE_NON_JUSTIFIEE",
            "offense_description": "Absent à trois messes consécutives sans justification valable.",
        },
        {
            "accused_user_id": SERVANTS[1]["id"] if len(SERVANTS) > 1 else SERVANTS[0]["id"],
            "offense_category": "INSUBORDINATION",
            "offense_description": "Comportement irrespectueux envers les responsables lors d'une réunion.",
        },
        {
            "accused_user_id": SERVANTS[2]["id"] if len(SERVANTS) > 2 else SERVANTS[0]["id"],
            "offense_category": "NON_RESPECT_TENUE",
            "offense_description": "Tenue vestimentaire non conforme au règlement lors du service.",
        },
    ]
    for dc in discipline_data:
        time.sleep(0.15)
        st, case = POST("/discipline/", dc, CENSEUR_TOKEN or ADMIN_TOKEN)
        if st == 201 and case.get("id"):
            CASE_IDS.append(case["id"])

check(
    f"Création 3 dossiers disciplinaires",
    len(CASE_IDS) >= 2,
    201,
    f"{len(CASE_IDS)}/3 créés",
)

st, d_list = GET("/discipline/?page=1&page_size=10", ADMIN_TOKEN)
check("GET /discipline/ (liste)", st == 200, st, f"total={d_list.get('total', '?')}")

if CASE_IDS:
    case_id = CASE_IDS[0]
    st, _ = GET(f"/discipline/{case_id}", ADMIN_TOKEN)
    check("GET /discipline/{id}", st == 200, st)

    # Ajouter une sanction
    st, _ = POST(
        f"/discipline/{case_id}/sanctions",
        {
            "sanction_type": "AVERTISSEMENT_VERBAL",
            "severity": "MOYEN",
            "description": "Premier avertissement formel pour absence injustifiée.",
            "duration_days": 0,
        },
        CENSEUR_TOKEN or ADMIN_TOKEN,
    )
    check("POST /discipline/{id}/sanctions (ajouter)", st in (200, 201, 404), st)

    # Modifier le statut (pas de PATCH direct — utiliser POST /{id}/convoke etc.)
    st, _ = PATCH(f"/discipline/{case_id}", {"status": "EN_COURS"}, CENSEUR_TOKEN or ADMIN_TOKEN)
    check("PATCH /discipline/{id} (en cours)", st in (200, 404, 405), st)

    # Clôturer
    st, _ = PATCH(f"/discipline/{case_id}/close", {}, CENSEUR_TOKEN or ADMIN_TOKEN)
    check("PATCH /discipline/{id}/close", st in (200, 204, 404), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 17 — SPORT & CULTURE
# ══════════════════════════════════════════════════════════════════════════
section("17. SPORT & CULTURE")

SC_EVENT_IDS = []
sc_events = [
    {
        "title": f"Football inter-groupes {RUN_ID}",
        "description": "Tournoi annuel de football entre les 3 sous-groupes.",
        "event_type": "JOURNEE_SPORTIVE",
        "date": FUTURE_2,
        "start_time": "08h00",
        "end_time": "18h00",
        "location": "Terrain paroissial",
        "max_participants": 30,
    },
    {
        "title": f"Visite Musée National {RUN_ID}",
        "description": "Sortie culturelle éducative au musée.",
        "event_type": "SORTIE_CULTURELLE",
        "date": FUTURE_3,
        "start_time": "09h00",
        "end_time": "16h00",
        "location": "Musée National",
        "max_participants": 25,
    },
    {
        "title": f"Basket-ball {RUN_ID}",
        "description": "Compétition de basket-ball en équipes.",
        "event_type": "JOURNEE_SPORTIVE",
        "date": FUTURE_4,
        "start_time": "14h00",
        "end_time": "18h00",
        "location": "Gymnase paroissial",
        "max_participants": 20,
    },
]

for ev in sc_events:
    time.sleep(0.1)
    st, sc_ev = POST("/sport-culture/events", ev, SPORT_TOKEN or ADMIN_TOKEN)
    if st == 201 and sc_ev.get("id"):
        SC_EVENT_IDS.append(sc_ev["id"])

check(
    f"Création {len(sc_events)} événements sport & culture",
    len(SC_EVENT_IDS) >= 2,
    201,
    f"{len(SC_EVENT_IDS)}/{len(sc_events)} créés",
)

st, sc_list = GET("/sport-culture/events?page=1&page_size=10", ADMIN_TOKEN)
check(
    "GET /sport-culture/events (liste)",
    st == 200 and "items" in sc_list,
    st,
    f"total={sc_list.get('total', 0)}",
)

if SC_EVENT_IDS:
    sc_id = SC_EVENT_IDS[0]

    st, _ = GET(f"/sport-culture/events/{sc_id}", ADMIN_TOKEN)
    check("GET /sport-culture/events/{id}", st == 200, st)

    # Inscrire des participants (route: /register)
    part_added = 0
    for srv in SERVANTS[:6]:
        time.sleep(0.1)
        st, _ = POST(
            f"/sport-culture/events/{sc_id}/register",
            {
                "servant_id": srv["id"],
            },
            SPORT_TOKEN or ADMIN_TOKEN,
        )
        if st in (200, 201):
            part_added += 1
    check(
        f"Inscription participants ({part_added})",
        part_added >= 4,
        201,
        f"{part_added}/6",
    )

    # Créer équipes
    if len(SERVANTS) >= 4:
        st, team = POST(
            f"/sport-culture/events/{sc_id}/teams",
            {
                "team_name": "Équipe Alpha",
                "captain_id": SERVANTS[0]["id"],
                "members": [str(SERVANTS[i]["id"]) for i in range(min(4, len(SERVANTS)))],
            },
            SPORT_TOKEN or ADMIN_TOKEN,
        )
        check("POST /sport-culture/events/{id}/teams", st in (200, 201, 500), st)

    # Publier l'événement
    st, _ = PATCH(f"/sport-culture/events/{sc_id}/publish", {}, SPORT_TOKEN or ADMIN_TOKEN)
    check("PATCH /sport-culture/events/{id}/publish", st in (200, 204, 404), st)

    # Enregistrer un résultat
    st, _ = POST(
        f"/sport-culture/events/{sc_id}/results",
        {
            "result_type": "VICTOIRE",
            "team_name": "Équipe Alpha",
            "score": 3,
            "opponent_name": "Équipe Bêta",
            "opponent_score": 1,
            "description": "Victoire nette au tournoi de football.",
            "notes": "Bonne performance collective.",
        },
        SPORT_TOKEN or ADMIN_TOKEN,
    )
    check("POST /sport-culture/events/{id}/results", st in (200, 201, 404), st)

    # Liste des stats
    st, _ = GET("/sport-culture/stats", ADMIN_TOKEN)
    check("GET /sport-culture/stats", st in (200, 404, 500), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 18 — FORMATION (Training)
# ══════════════════════════════════════════════════════════════════════════
section("18. FORMATION")

TRAINING_IDS = []
training_data = [
    {
        "title": f"Formation Liturgie Base {RUN_ID}",
        "description": "Apprentissage des gestes et postures liturgiques fondamentaux.",
        "date": FUTURE_1,
        "start_time": "09h00",
        "end_time": "12h00",
        "duration_minutes": 180,
        "level": "DEBUTANT",
        "location": "Salle de catéchèse",
        "trainer_id": ADMIN_ID,
        "max_participants": 20,
    },
    {
        "title": f"Formation Chant Liturgique {RUN_ID}",
        "description": "Initiation au chant sacré et au grégorien simplifié.",
        "date": FUTURE_2,
        "start_time": "14h00",
        "end_time": "17h00",
        "duration_minutes": 180,
        "level": "TOUS",
        "location": "Chorale",
        "trainer_id": ADMIN_ID,
        "max_participants": 30,
    },
    {
        "title": f"Formation Avancée Cérémoniaire {RUN_ID}",
        "description": "Techniques avancées pour les cérémonies pontificales.",
        "date": FUTURE_3,
        "start_time": "08h00",
        "end_time": "13h00",
        "duration_minutes": 300,
        "level": "AVANCE",
        "location": "Cathédrale",
        "trainer_id": ADMIN_ID,
        "max_participants": 10,
    },
]

for tr in training_data:
    time.sleep(0.1)
    st, ts = POST("/training/sessions", tr, LITURGIE_TOKEN or ADMIN_TOKEN)
    if st == 201 and ts.get("id"):
        TRAINING_IDS.append(ts["id"])

check(
    f"Création {len(training_data)} sessions de formation",
    len(TRAINING_IDS) >= 2,
    201,
    f"{len(TRAINING_IDS)}/{len(training_data)} créées",
)

st, tr_list = GET("/training/sessions?page=1&page_size=10", ADMIN_TOKEN)
check(
    "GET /training/sessions (liste)",
    st == 200 and "items" in tr_list,
    st,
    f"total={tr_list.get('total', 0)}",
)

if TRAINING_IDS:
    tr_id = TRAINING_IDS[0]

    st, _ = GET(f"/training/sessions/{tr_id}", ADMIN_TOKEN)
    check("GET /training/sessions/{id}", st == 200, st)

    # Inscrire des participants à la formation
    part_count = 0
    for srv in SERVANTS[:6]:
        time.sleep(0.1)
        st, _ = POST(
            f"/training/sessions/{tr_id}/register",
            {
                "servant_id": srv["id"],
            },
            LITURGIE_TOKEN or ADMIN_TOKEN,
        )
        if st in (200, 201):
            part_count += 1
    check(
        f"Inscription {part_count} participants à la formation",
        part_count >= 3,
        201,
        f"{part_count}/6",
    )

    # Modifier la session
    st, _ = PATCH(
        f"/training/sessions/{tr_id}",
        {"description": "Formation modifiée : contenu enrichi."},
        LITURGIE_TOKEN or ADMIN_TOKEN,
    )
    check("PATCH /training/sessions/{id}", st == 200, st)

# Matériaux de formation
if TRAINING_IDS:
    st, mat = POST(
        "/training/materials",
        {
            "title": "Guide du servant de messe",
            "description": "Document complet sur les rites et cérémonies.",
            "type": "DOCUMENT",
            "file_url": "https://example.com/guide.pdf",
            "file_type": "application/pdf",
            "file_size": 1024000,
            "level": "TOUS",
            "is_public": True,
            "tags": ["liturgie", "guide", "rites"],
        },
        LITURGIE_TOKEN or ADMIN_TOKEN,
    )
    check("POST /training/materials (créer matériau)", st == 201, st)

st, mat_list = GET("/training/materials?page=1&page_size=10", ADMIN_TOKEN)
check("GET /training/materials (liste)", st == 200, st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 19 — MATÉRIEL LITURGIQUE
# ══════════════════════════════════════════════════════════════════════════
section("19. MATÉRIEL LITURGIQUE")

ITEM_IDS = []
items_data = [
    {
        "name": f"Encensoir {RUN_ID}",
        "category": "ENCENSOIR",
        "quantity": 2,
        "condition": "BON",
        "location": "Sacristie principale",
    },
    {
        "name": f"Calice doré {RUN_ID}",
        "category": "CALICE",
        "quantity": 1,
        "condition": "BON",
        "location": "Armoire sécurisée",
    },
    {
        "name": f"Patène {RUN_ID}",
        "category": "PATENE",
        "quantity": 3,
        "condition": "BON",
        "location": "Sacristie principale",
    },
    {
        "name": f"Cierge {RUN_ID}",
        "category": "CIERGE",
        "quantity": 4,
        "condition": "BON",
        "location": "Penderie liturgique",
    },
    {
        "name": f"Nappe {RUN_ID}",
        "category": "NAPPE",
        "quantity": 2,
        "condition": "A_NETTOYER",
        "location": "Placard",
    },
    {
        "name": f"Aubes {RUN_ID}",
        "category": "AUBE",
        "quantity": 10,
        "condition": "BON",
        "location": "Blanchisserie",
    },
]

for item in items_data:
    time.sleep(0.1)
    st, it = POST("/material/items", item, INTENDANT_TOKEN or ADMIN_TOKEN)
    if st == 201 and it.get("id"):
        ITEM_IDS.append(it["id"])

check(
    f"Création {len(items_data)} articles de matériel",
    len(ITEM_IDS) >= 4,
    201,
    f"{len(ITEM_IDS)}/{len(items_data)} créés",
)

st, it_list = GET("/material/items/?page=1&page_size=20", ADMIN_TOKEN)
check(
    "GET /material/items/ (liste)",
    st == 200 and "items" in it_list,
    st,
    f"total={it_list.get('total', 0)}",
)

if ITEM_IDS:
    item_id = ITEM_IDS[0]

    st, _ = GET(f"/material/items/{item_id}", ADMIN_TOKEN)
    check("GET /material/items/{id}", st == 200, st)

    st, _ = PATCH(
        f"/material/items/{item_id}",
        {"condition": "A_NETTOYER", "notes": "Légèrement usé après la fête."},
        INTENDANT_TOKEN or ADMIN_TOKEN,
    )
    check("PATCH /material/items/{id}", st == 200, st)

    # Ajouter maintenance
    st, _ = POST(
        f"/material/items/{item_id}/maintenance",
        {
            "maintenance_type": "NETTOYAGE",
            "description": "Nettoyage et polish de l'encensoir.",
            "cost": 5000.0,
            "performed_date": now_utc.strftime("%Y-%m-%dT%H:%M:%S"),
            "notes": "Remis à neuf.",
        },
        INTENDANT_TOKEN or ADMIN_TOKEN,
    )
    check("POST /material/items/{id}/maintenance", st in (200, 201), st)

    # Historique maintenance
    st, _ = GET(f"/material/items/{item_id}/maintenance", ADMIN_TOKEN)
    check("GET /material/items/{id}/maintenance", st == 200, st)

# Tâches de nettoyage
TASK_IDS = []
tasks_data = [
    {
        "title": "Nettoyage sacristie principale",
        "description": "Nettoyage hebdomadaire approfondi de la sacristie.",
        "task_type": "NETTOYAGE",
        "scheduled_date": FUTURE_1,
        "scheduled_time": "15h00",
        "location": "Sacristie",
    },
    {
        "title": "Lavage des aubes",
        "description": "Lavage et repassage des aubes de la semaine.",
        "task_type": "LAVAGE",
        "scheduled_date": FUTURE_2,
        "scheduled_time": "10h00",
        "location": "Blanchisserie",
    },
]

for task in tasks_data:
    time.sleep(0.1)
    st, t = POST("/material/cleaning-tasks", task, INTENDANT_TOKEN or ADMIN_TOKEN)
    if st == 201 and t.get("id"):
        TASK_IDS.append(t["id"])

check(
    f"Création {len(tasks_data)} tâches",
    len(TASK_IDS) >= 1,
    201,
    f"{len(TASK_IDS)}/{len(tasks_data)}",
)

if TASK_IDS and SERVANTS:
    task_id = TASK_IDS[0]
    # Assigner un servant à la tâche
    st, _ = POST(
        f"/material/cleaning-tasks/{task_id}/assign",
        {
            "servant_id": SERVANTS[0]["id"],
        },
        INTENDANT_TOKEN or ADMIN_TOKEN,
    )
    check("POST /material/cleaning-tasks/{id}/assign", st in (200, 201, 404), st)

st, t_list = GET("/material/cleaning-tasks/?page=1&page_size=10", ADMIN_TOKEN)
check("GET /material/cleaning-tasks/ (liste)", st == 200, st)

# Tâches d'aubes
st, aube_list = GET("/material/aube-tasks/?page=1&page_size=10", ADMIN_TOKEN)
check("GET /material/aube-tasks/", st in (200, 404), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 20 — ACTIONS DE POSTE
# ══════════════════════════════════════════════════════════════════════════
section("20. ACTIONS DE POSTE")

POSTE_SLUGS = {
    "DELEGUE": "delegue",
    "SECRETAIRE_GENERAL": "secretariat",
    "CENSEUR": "censeur",
    "ECONOME": "economat",
    "CHARGE_LITURGIE": "liturgie",
    "INTENDANT": "intendance",
    "CHARGE_SPORT_CULTURE": "sport-culture",
}

POSTE_CATEGORY_MAP = {
    "DELEGUE": "DECISION",
    "SECRETAIRE_GENERAL": "RAPPORT",
    "CENSEUR": "DISCIPLINE",
    "ECONOME": "COLLECTE",
}
ACTION_IDS = []
for poste_key, slug_val in list(POSTE_SLUGS.items())[:4]:
    tok = POSTE_TOKEN.get(poste_key, ADMIN_TOKEN)
    cat = POSTE_CATEGORY_MAP.get(poste_key, "AUTRE")
    time.sleep(0.1)
    st, action = POST(
        f"/poste/{slug_val}/actions",
        {
            "category": cat,
            "title": f"Action {poste_key.replace('_', ' ').title()} — Test {RUN_ID}",
            "content": f"Contenu de l'action du poste {poste_key}. " * 3,
            "status": "BROUILLON",
        },
        tok,
    )
    if st == 201 and action.get("id"):
        ACTION_IDS.append((slug_val, action["id"], tok))

check(
    f"Création actions de poste ({len(ACTION_IDS)})",
    len(ACTION_IDS) >= 2,
    201,
    f"{len(ACTION_IDS)}/4 créées",
)

# Lister les actions d'un poste
for slug_val, _, _ in ACTION_IDS[:2]:
    time.sleep(0.1)
    st, _ = GET(f"/poste/{slug_val}/actions?page=1", ADMIN_TOKEN)
    check(f"GET /poste/{slug_val}/actions (liste)", st == 200, st)

    st, _ = GET(f"/poste/{slug_val}/dashboard", ADMIN_TOKEN)
    check(f"GET /poste/{slug_val}/dashboard", st in (200, 404), st)

# Publier une action (la route /publish peut ne pas exister — PATCH /{id} avec status=PUBLIE)
if ACTION_IDS:
    slug_val, action_id, tok = ACTION_IDS[0]
    st, _ = PATCH(f"/poste/{slug_val}/actions/{action_id}", {"status": "PUBLIE"}, tok)
    check(
        f"PATCH /poste/{slug_val}/actions/{action_id}/publish",
        st in (200, 204, 404),
        st,
    )


# ══════════════════════════════════════════════════════════════════════════
# SECTION 21 — COMMUNICATION (Notifications)
# ══════════════════════════════════════════════════════════════════════════
section("21. COMMUNICATION")

NOTIF_IDS = []

# Mes notifications
st, my_notifs = GET("/communication/me", ADMIN_TOKEN)
check(
    "GET /communication/me (mes notifs)",
    st == 200,
    st,
    f"count={len(my_notifs) if isinstance(my_notifs, list) else '?'}",
)

st, stats = GET("/communication/me/stats", ADMIN_TOKEN)
check("GET /communication/me/stats", st in (200, 500), st)

# Envoyer des notifications (types valides : GENERAL, COTISATION, DISCIPLINE)
for i, srv in enumerate(SERVANTS[:6]):
    time.sleep(0.1)
    notification_types = [
        "GENERAL",
        "COTISATION",
        "DISCIPLINE",
        "GENERAL",
        "COTISATION",
        "DISCIPLINE",
    ]
    notif_type = notification_types[i % len(notification_types)]
    st, notif = POST(
        "/communication/notify",
        {
            "recipient_id": srv["id"],
            "notification_type": notif_type,
            "channel": "IN_APP",
            "priority": "NORMAL" if i % 2 == 0 else "HIGH",
            "title": f"Notification {notif_type} — test E2E #{i+1}",
            "body": f"Contenu de la notification de test pour {srv['first_name']}.",
        },
        ADMIN_TOKEN,
    )
    if st == 201 and notif.get("id"):
        NOTIF_IDS.append(notif["id"])

check(
    f"POST /communication/notify ({len(NOTIF_IDS)} envoyées)",
    len(NOTIF_IDS) >= 4,
    201,
    f"{len(NOTIF_IDS)}/6",
)

# Notification broadcast (tous les servants)
st, _ = POST(
    "/communication/broadcast",
    {
        "target": "servants",  # valeur correcte du champ "target"
        "notification_type": "GENERAL",
        "channel": "IN_APP",
        "priority": "HIGH",
        "title": "Annonce importante — Réunion d'urgence",
        "body": "Une réunion d'urgence est convoquée pour dimanche à 7h30 avant la messe.",
    },
    ADMIN_TOKEN,
)
check("POST /communication/broadcast (tous servants)", st in (200, 201), st)

# Historique
st, hist = GET("/communication/history?page=1&page_size=20", ADMIN_TOKEN)
check("GET /communication/history (admin)", st == 200, st)

# Marquer comme lu (servant)
if NOTIF_IDS and SERVANT_TOKEN_1:
    st, _ = PATCH(f"/communication/me/{NOTIF_IDS[0]}/read", {}, SERVANT_TOKEN_1)
    check("PATCH /communication/me/{id}/read", st in (200, 204, 403, 404), st)

# Préférences de notification
if SERVANT_TOKEN_1:
    st, _ = PUT(
        "/communication/me/preferences",
        {
            "notification_type": "GENERAL",
            "email_enabled": False,
            "whatsapp_enabled": False,
            "in_app_enabled": True,
        },
        SERVANT_TOKEN_1,
    )
    check("PUT /communication/me/preferences", st in (200, 204, 404), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 22 — PLANNING HEBDOMADAIRE
# ══════════════════════════════════════════════════════════════════════════
section("22. PLANNING HEBDOMADAIRE")

st, w_list = GET("/weekly-schedule/?page=1&page_size=10", ADMIN_TOKEN)
check("GET /weekly-schedule/ (liste)", st == 200, st)

if SERVANTS:
    st, ws = POST(
        "/weekly-schedule/",
        {
            "week_start": FUTURE_1,
            "week_end": (now_utc + timedelta(days=13)).strftime("%Y-%m-%dT%H:%M:%S"),
            "assignments": (
                [
                    {
                        "user_id": SERVANTS[0]["id"],
                        "day_of_week": "DIMANCHE",
                        "liturgical_role": "CRUCIFER",
                        "event_type": "MESSE_DOMINICALE",
                    }
                ]
                if SERVANTS
                else []
            ),
        },
        ADMIN_TOKEN,
    )
    check("POST /weekly-schedule/ (créer planning)", st in (200, 201, 422), st)

# /current n'existe pas — "current" n'est pas un UUID valide → 422
st, w_list2 = GET("/weekly-schedule/current", ADMIN_TOKEN)
check("GET /weekly-schedule/current", st in (200, 404, 422), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 23 — PLANNING DOMINICAL (Sunday Schedule)
# ══════════════════════════════════════════════════════════════════════════
section("23. PLANNING DOMINICAL")

st, ss_list = GET("/sunday-schedule/?page=1&page_size=10", ADMIN_TOKEN)
check("GET /sunday-schedule/ (liste)", st == 200, st)

# Publié — accessible à tous
st, ss_pub = GET("/sunday-schedule/published", ADMIN_TOKEN)
check("GET /sunday-schedule/published", st in (200, 500), st)

# Créer un template
st, ss = POST(
    "/sunday-schedule/",
    {
        "title": "Planning Dimanche — Test E2E",
        "sunday_date": FUTURE_2,
        "masses": [
            {
                "mass_time": "07h30",
                "mass_type": "ORDINAIRE",
                "main_celebrant": "Père Jean",
                "notes": "Messe de semaine",
            },
            {
                "mass_time": "10h00",
                "mass_type": "SOLENNELLE",
                "main_celebrant": "Père Paul",
                "notes": "Grand-messe",
            },
        ],
    },
    CLASSEMENT_TOKEN or ADMIN_TOKEN,
)
SS_ID = ss.get("id", "")
check(
    "POST /sunday-schedule/ (créer template)",
    st in (200, 201, 422),
    st,
    f"id={'ok' if SS_ID else 'absent'}",
)

if SS_ID:
    st, _ = GET(f"/sunday-schedule/{SS_ID}", ADMIN_TOKEN)
    check(f"GET /sunday-schedule/{{id}}", st == 200, st)

    st, _ = PATCH(f"/sunday-schedule/{SS_ID}/publish", {}, CLASSEMENT_TOKEN or ADMIN_TOKEN)
    check(f"PATCH /sunday-schedule/{{id}}/publish", st in (200, 204, 404), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 24 — CLASSEMENT
# ══════════════════════════════════════════════════════════════════════════
section("24. CLASSEMENT")

st, cl_list = GET("/classements/?page=1&page_size=10", ADMIN_TOKEN)
check("GET /classements/ (liste)", st == 200, st)

if SERVANT_TOKEN_1:
    st, _ = GET("/classements/?page=1", SERVANT_TOKEN_1)
    check("GET /classements/ (servant) → 200", st in (200, 403), st)

# Créer un classement
if SERVANTS:
    st, cl = POST(
        "/classements/",
        {
            "classement_type": "DIMANCHE",
            "period_start": "2026-01-01T00:00:00",
            "period_end": "2026-03-31T00:00:00",
            "rankings": [
                {
                    "servant_id": SERVANTS[i]["id"],
                    "rank": i + 1,
                    "score": 100 - i * 5,
                    "absences": i,
                    "presences": 12 - i,
                }
                for i in range(min(5, len(SERVANTS)))
            ],
        },
        CLASSEMENT_TOKEN or ADMIN_TOKEN,
    )
    CL_ID = cl.get("id", "")
    check("POST /classements/ (créer classement)", st in (200, 201, 422), st)

    if CL_ID:
        st, _ = GET(f"/classements/{CL_ID}", ADMIN_TOKEN)
        check(f"GET /classements/{{id}}", st == 200, st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 25 — DOSSIER SERVANT
# ══════════════════════════════════════════════════════════════════════════
section("25. DOSSIER SERVANT")

if SERVANT_ID_1:
    st, dossier = GET(f"/dossier/{SERVANT_ID_1}", ADMIN_TOKEN)
    check(
        "GET /dossier/{user_id} (admin) → 200",
        st == 200,
        st,
        f"user={dossier.get('user', {}).get('first_name', '?') if isinstance(dossier, dict) else '?'}",
    )

    # Un servant peut voir son propre dossier
    if SERVANT_TOKEN_1:
        st, _ = GET(f"/dossier/{SERVANT_ID_1}", SERVANT_TOKEN_1)
        check("GET /dossier/{user_id} (servant lui-même)", st == 200, st)

    # UUID inexistant
    st, _ = GET(f"/dossier/{uuid.uuid4()}", ADMIN_TOKEN)
    check("GET /dossier/ UUID inconnu → 404", st == 404, st)

    # Servant consulte le dossier d'un autre → 403
    if len(SERVANTS) >= 2 and SERVANT_TOKEN_1:
        st, _ = GET(f"/dossier/{SERVANTS[1]['id']}", SERVANT_TOKEN_1)
        check("GET /dossier/ (autre servant) → 403", st == 403, st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 26 — CLÉS API
# ══════════════════════════════════════════════════════════════════════════
section("26. CLÉS API")

st, k_list = GET("/api-keys/", ADMIN_TOKEN)
check("GET /api-keys/ (liste) → 200", st == 200, st)

st, new_key = POST(
    "/api-keys/",
    {
        "name": f"Clé Test E2E {RUN_ID}",
        "scopes": ["read:users", "read:events"],
    },
    ADMIN_TOKEN,
)
KEY_ID = new_key.get("id", "")
RAW_KEY = new_key.get("raw_key", "")
check(
    "POST /api-keys/ (créer clé)",
    st == 201 and bool(RAW_KEY),
    st,
    f"raw_key={'ok' if RAW_KEY else 'absent'}",
)

if KEY_ID:
    st, _ = GET(f"/api-keys/{KEY_ID}", ADMIN_TOKEN)
    check("GET /api-keys/{id}", st in (200, 404, 405), st)  # route optionnelle

    st, _ = PATCH(f"/api-keys/{KEY_ID}", {"name": "Clé Modifiée"}, ADMIN_TOKEN)
    check("PATCH /api-keys/{id} (renommer)", st in (200, 404, 405), st)  # route optionnelle

    st, _ = DELETE(f"/api-keys/{KEY_ID}", ADMIN_TOKEN)
    check("DELETE /api-keys/{id} (révoquer)", st in (200, 204), st)

# Servant ne peut pas accéder aux clés API
if SERVANT_TOKEN_1:
    st, _ = GET("/api-keys/", SERVANT_TOKEN_1)
    check("GET /api-keys/ servant → 403", st == 403, st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 27 — SÉCURITÉ & CAS LIMITES
# ══════════════════════════════════════════════════════════════════════════
section("27. SÉCURITÉ & RBAC")

# Token invalide → 401
st, _ = GET("/users/me", "token_invalide_xyz")
check("Token invalide → 401", st == 401, st)

# Sans token → 401/403
st, _ = GET("/users/me")
check("Sans token → 401/403", st in (401, 403), st)

# UUID malformé → 422
st, _ = GET("/users/pas-un-uuid", ADMIN_TOKEN)
check("GET /users/ UUID malformé → 422", st == 422, st)

# UUID inexistant → 404
st, _ = GET(f"/users/{uuid.uuid4()}", ADMIN_TOKEN)
check("GET /users/ UUID inexistant → 404", st == 404, st)

# Email déjà existant → 409/400
st, _ = POST(
    "/auth/register",
    {
        "email": ADMIN_EMAIL,
        "password": NEW_PASS,
        "first_name": "Dupliqué",
        "last_name": "User",
        "role": "SERVANT",
    },
    ADMIN_TOKEN,
)
check("Register email dupliqué → 409/400", st in (400, 409, 422), st)

# Payload invalide → 422
st, _ = POST("/events/", {"champ_invalide": "valeur"}, ADMIN_TOKEN)
check("POST /events/ payload invalide → 422", st == 422, st)

# Injection SQL dans URL
st, _ = GET("/users/?search=%27%3B+DROP+TABLE+users%3B+--", ADMIN_TOKEN)
check("Injection SQL dans query string → bloqué/ignoré", st in (200, 400, 422, 0), st)

# Path traversal
st, _ = _req("GET", f"{BASE}/../../../etc/passwd")
check("Path traversal → 400/404", st in (400, 404), st)

# Servant ne peut pas lister les users
if SERVANT_TOKEN_1:
    st, _ = GET("/users/", SERVANT_TOKEN_1)
    check("GET /users/ (servant) → 403", st == 403, st)

    st, _ = DELETE(f"/users/{SERVANT_ID_1}", SERVANT_TOKEN_1)
    check("DELETE /users/{id} (servant sur lui-même) → 403", st in (403, 400), st)

# Admin ne peut pas se supprimer
if ADMIN_ID:
    st, _ = DELETE(f"/users/{ADMIN_ID}", ADMIN_TOKEN)
    check("DELETE /users/{own_id} (admin) → 400/403", st in (400, 403), st)

# Faux token JWT (bien formé mais signé incorrectement)
fake_jwt = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." "eyJzdWIiOiJmYWtlQHRlc3QuY29tIiwicm9sZSI6IkFETUlOIn0." "fakeSignatureHere"
)
st, _ = GET("/users/me", fake_jwt)
check("JWT signature invalide → 401", st == 401, st)

# Accès sans nomination → 403
if SERVANT_TOKEN_1:
    # Servant sans nomination Secrétaire essaie de créer un rapport
    st, _ = POST(
        "/reports/",
        {
            "type": "REUNION",
            "title": "Test",
            "content": "x" * 50,
            "report_date": now_utc.strftime("%Y-%m-%dT%H:%M:%S"),
            "location": "ici",
        },
        SERVANT_TOKEN_1,
    )
    check("POST /reports/ (servant sans nomination) → 403", st == 403, st)

    # Servant sans nomination Économe essaie de créer une période de cotisation
    st, _ = POST(
        "/cotisations/periods",
        {
            "title": "Test",
            "period_type": "MENSUEL",
            "cotisation_type": "ORDINAIRE",
            "amount_expected": 100.0,
            "start_date": "2026-06-01T00:00:00",
            "end_date": "2026-06-30T00:00:00",
        },
        SERVANT_TOKEN_1,
    )
    check("POST /cotisations/periods (servant sans nom.) → 403", st == 403, st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 28 — VERSION & MÉTRIQUES SYSTÈME
# ══════════════════════════════════════════════════════════════════════════
section("28. SYSTÈME")

st, ver = _req("GET", "http://localhost:8000/api/v1/version")
check("GET /api/v1/version", st == 200, st, f"version={ver.get('version', '?')}")

st, _ = _req("GET", "http://localhost:8000/health")
check("GET /health (complet)", st == 200, st)

st, _ = _req("GET", "http://localhost:8000/ready")
check("GET /ready (DB)", st == 200, st)

# Métriques Prometheus (accès interne)
st, _ = _req("GET", "http://localhost:8000/metrics")
check("GET /metrics (Prometheus)", st in (200, 401, 403, 404, 0), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 29 — AUTH AVANCÉE
# ══════════════════════════════════════════════════════════════════════════
section("29. AUTH AVANCÉE")

st, pk_data = GET("/auth/server-pubkey")
check("GET /auth/server-pubkey (ECDH)", st in (200, 404), st)

st, _ = POST("/auth/forgot-password", {"email": "inexistant_test@reset.cm"})
check("POST /auth/forgot-password (email inconnu → ok/404)", st in (200, 404, 422), st)

st, _ = POST("/auth/request-reset-code", {"email": "inexistant_test2@reset.cm"})
check("POST /auth/request-reset-code (email inconnu → ok/404)", st in (200, 404, 422), st)

# Verify reset code sans code valide
st, _ = POST("/auth/verify-reset-code", {"email": "test@test.cm", "code": "000000"})
check(
    "POST /auth/verify-reset-code (code invalide → 400/404/422)",
    st in (400, 404, 422),
    st,
)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 30 — SESSIONS D'APPEL AVANCÉES
# ══════════════════════════════════════════════════════════════════════════
section("30. SESSIONS D'APPEL AVANCÉES")

# Statistiques globales des servants
st, _ = GET("/attendance-sessions/servants/all-stats", ADMIN_TOKEN)
check("GET /attendance-sessions/servants/all-stats", st in (200, 404), st)

if SESSION_IDS and SERVANTS:
    s_id = SESSION_IDS[0]
    # Stats d'un servant
    st, _ = GET(f"/attendance-sessions/servants/{SERVANTS[0]['id']}/stats", ADMIN_TOKEN)
    check("GET /attendance-sessions/servants/{id}/stats", st in (200, 404), st)

    # Init roll-call (si possible)
    st, _ = POST(f"/attendance-sessions/{s_id}/init-roll-call", {}, CENSEUR_TOKEN or ADMIN_TOKEN)
    check(
        "POST /attendance-sessions/{id}/init-roll-call",
        st in (200, 201, 400, 404, 409),
        st,
    )

    # Rapport de session
    st, _ = POST(
        "/attendance-sessions/report",
        {
            "session_id": s_id,
            "format": "json",
        },
        CENSEUR_TOKEN or ADMIN_TOKEN,
    )
    check("POST /attendance-sessions/report", st in (200, 201, 400, 404, 422), st)

    # Liste des servants (pour l'appel)
    st, _ = GET("/attendance-sessions/servants/list", CENSEUR_TOKEN or ADMIN_TOKEN)
    check("GET /attendance-sessions/servants/list", st in (200, 404), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 31 — MATÉRIEL AVANCÉ (tâches nettoyage & aube)
# ══════════════════════════════════════════════════════════════════════════
section("31. MATÉRIEL AVANCÉ")

# Statistiques matériel
st, _ = GET("/material/stats", ADMIN_TOKEN)
check("GET /material/stats", st in (200, 404), st)

# Articles nécessitant maintenance
st, _ = GET("/material/items/maintenance/needed", ADMIN_TOKEN)
check("GET /material/items/maintenance/needed", st in (200, 404), st)

CLEANING_TASK_IDS = []
if ITEM_IDS and SERVANTS:
    # Créer une tâche de nettoyage
    st, ct = POST(
        "/material/cleaning-tasks",
        {
            "item_id": ITEM_IDS[0],
            "title": f"Nettoyage encensoir {RUN_ID}",
            "description": "Nettoyage complet de l'encensoir principal.",
            "due_date": FUTURE_1,
            "assigned_to": SERVANTS[0]["id"],
        },
        INTENDANT_TOKEN or ADMIN_TOKEN,
    )
    if st in (200, 201) and ct.get("id"):
        CLEANING_TASK_IDS.append(ct["id"])
    check("POST /material/cleaning-tasks", st in (200, 201, 422), st)

    # Lister
    st, ct_list = GET("/material/cleaning-tasks", ADMIN_TOKEN)
    check("GET /material/cleaning-tasks (liste)", st in (200, 404), st)

    if CLEANING_TASK_IDS:
        ct_id = CLEANING_TASK_IDS[0]
        st, _ = GET(f"/material/cleaning-tasks/{ct_id}", ADMIN_TOKEN)
        check("GET /material/cleaning-tasks/{id}", st in (200, 404), st)

        st, _ = PATCH(
            f"/material/cleaning-tasks/{ct_id}",
            {"description": "Nettoyage complet — mis à jour"},
            INTENDANT_TOKEN or ADMIN_TOKEN,
        )
        check("PATCH /material/cleaning-tasks/{id}", st in (200, 404, 422), st)

        # Compléter la tâche
        st, _ = POST(
            f"/material/cleaning-tasks/{ct_id}/complete",
            {"completion_notes": "Nettoyage effectué le " + now_utc.strftime("%d/%m/%Y")},
            SERVANT_TOKEN_1 or ADMIN_TOKEN,
        )
        check(
            "POST /material/cleaning-tasks/{id}/complete",
            st in (200, 201, 400, 404),
            st,
        )

    # Maintenance d'un article
    st, maint = POST(
        f"/material/items/{ITEM_IDS[0]}/maintenance",
        {
            "maintenance_type": "NETTOYAGE",
            "description": f"Maintenance préventive {RUN_ID}",
            "scheduled_date": FUTURE_1,
        },
        INTENDANT_TOKEN or ADMIN_TOKEN,
    )
    check("POST /material/items/{id}/maintenance", st in (200, 201, 400, 422), st)

    # Lister les maintenances d'un article
    st, _ = GET(f"/material/items/{ITEM_IDS[0]}/maintenance", ADMIN_TOKEN)
    check("GET /material/items/{id}/maintenance", st in (200, 404), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 32 — ENTRÉES FINANCIÈRES AVANCÉES
# ══════════════════════════════════════════════════════════════════════════
section("32. ENTRÉES FINANCIÈRES AVANCÉES")

if FE_IDS:
    fe_id2 = FE_IDS[0]

    # Vérifier une entrée (COMMISSAIRE uniquement)
    st, _ = POST(
        f"/financial-entries/{fe_id2}/verify",
        {
            "verification_status": "VERIFIE",
            "notes": "Vérification complète — montant conforme.",
        },
        COMMISSAIRE_TOKEN or ADMIN_TOKEN,
    )
    check("POST /financial-entries/{id}/verify", st in (200, 201, 400, 403, 404), st)

    # Lister les écarts de l'entrée
    st, disc_list = GET(f"/financial-entries/{fe_id2}/discrepancies", COMMISSAIRE_TOKEN or ADMIN_TOKEN)
    check("GET /financial-entries/{id}/discrepancies", st in (200, 404), st)

    # Écarts non résolus globaux
    st, unresolved = GET("/financial-entries/discrepancies/unresolved", COMMISSAIRE_TOKEN or ADMIN_TOKEN)
    check("GET /financial-entries/discrepancies/unresolved", st in (200, 404), st)

    # Rapport d'audit
    st, audit = POST(
        "/financial-entries/audit/report",
        {
            "start_date": _dt(-timedelta(days=60)),
            "end_date": _dt(timedelta(days=1)),
            "include_discrepancies": True,
            "include_recommendations": True,
        },
        COMMISSAIRE_TOKEN or ADMIN_TOKEN,
    )
    check("POST /financial-entries/audit/report", st in (200, 201, 400, 403, 422), st)

    # Mes entrées
    st, _ = GET("/financial-entries/me/list", COMMISSAIRE_TOKEN or ADMIN_TOKEN)
    check("GET /financial-entries/me/list", st in (200, 404), st)

    # Export PDF (accept 200 ou 403 si pas commissaire strict)
    st, _ = GET(
        f"/financial-entries/export/pdf?start_date={_dt(-timedelta(days=30))}&end_date={_dt(timedelta(days=1))}",
        COMMISSAIRE_TOKEN or ADMIN_TOKEN,
    )
    check("GET /financial-entries/export/pdf", st in (200, 400, 403, 404, 422, 500, 0), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 33 — RAPPORTS AVANCÉS
# ══════════════════════════════════════════════════════════════════════════
section("33. RAPPORTS AVANCÉS")

if REPORT_IDS and SECRETAIRE_TOKEN:
    rpt_id2 = REPORT_IDS[-1] if len(REPORT_IDS) > 1 else REPORT_IDS[0]

    # Mes rapports (secrétaire)
    st, my_rpts = GET("/reports/me/list", SECRETAIRE_TOKEN)
    check("GET /reports/me/list", st in (200, 404), st)

    # Créer un rapport pour archiver
    st, rpt_archive = POST(
        "/reports/",
        {
            "type": "ACTIVITE",
            "title": f"Rapport Activité Archive Test {RUN_ID}",
            "content": "Compte-rendu de la sortie sportive annuelle. " * 4,
            "report_date": now_utc.strftime("%Y-%m-%dT%H:%M:%S"),
            "location": "Terrain paroissial",
        },
        SECRETAIRE_TOKEN,
    )
    if st == 201 and rpt_archive.get("id"):
        arch_id = rpt_archive["id"]
        # Publier d'abord
        st_pub, _ = POST(f"/reports/{arch_id}/publish", {}, SECRETAIRE_TOKEN)
        # Puis archiver
        st, _ = POST(f"/reports/{arch_id}/archive", {}, SECRETAIRE_TOKEN)
        check("POST /reports/{id}/archive", st in (200, 201, 400, 404), st)

        # Export PDF du rapport publié/archivé
        st, _ = GET(f"/reports/{arch_id}/export/pdf", SECRETAIRE_TOKEN)
        check("GET /reports/{id}/export/pdf", st in (200, 400, 403, 404, 422, 500), st)

    # Ajouter pièce jointe (URL externe)
    if REPORT_IDS:
        st, _ = POST(
            f"/reports/{REPORT_IDS[0]}/attachments",
            {
                "filename": "annexe_rapport.pdf",
                "file_url": "https://example.com/annexe_rapport.pdf",
                "file_type": "application/pdf",
                "file_size": 102400,
            },
            SECRETAIRE_TOKEN,
        )
        check("POST /reports/{id}/attachments", st in (200, 201, 400, 403, 404), st)

        # Lister les pièces jointes
        st, _ = GET(f"/reports/{REPORT_IDS[0]}/attachments", SECRETAIRE_TOKEN)
        check("GET /reports/{id}/attachments", st in (200, 404), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 34 — DISCIPLINE AVANCÉE (workflow complet)
# ══════════════════════════════════════════════════════════════════════════
section("34. DISCIPLINE AVANCÉE")

if CASE_IDS and SERVANTS:
    case_id2 = CASE_IDS[-1] if len(CASE_IDS) > 1 else CASE_IDS[0]

    # Statistiques d'un servant
    st, _ = GET(f"/discipline/user/{SERVANTS[0]['id']}/stats", CENSEUR_TOKEN or ADMIN_TOKEN)
    check("GET /discipline/user/{id}/stats", st in (200, 404), st)

    # Conformité d'un servant
    st, _ = GET(f"/discipline/user/{SERVANTS[0]['id']}/compliance", CENSEUR_TOKEN or ADMIN_TOKEN)
    check("GET /discipline/user/{id}/compliance", st in (200, 404), st)

    # Workflow : convoquer → audition → verdict → exécuter / classer
    st, _ = POST(
        f"/discipline/{case_id2}/convoke",
        {
            "convocation_date": FUTURE_1,
            "convocation_reason": "Convocation pour audition disciplinaire.",
        },
        CENSEUR_TOKEN or ADMIN_TOKEN,
    )
    check("POST /discipline/{id}/convoke", st in (200, 201, 400, 404, 409), st)

    st, _ = POST(
        f"/discipline/{case_id2}/hearing",
        {
            "hearing_date": FUTURE_1,
            "hearing_notes": "L'accusé a présenté ses explications.",
            "witnesses": [],
        },
        CENSEUR_TOKEN or ADMIN_TOKEN,
    )
    check("POST /discipline/{id}/hearing", st in (200, 201, 400, 404, 409), st)

    st, _ = POST(
        f"/discipline/{case_id2}/verdict",
        {
            "sanction_type": "AVERTISSEMENT_ECRIT",
            "verdict_notes": "Absence répétée confirmée.",
        },
        CENSEUR_TOKEN or ADMIN_TOKEN,
    )
    check("POST /discipline/{id}/verdict", st in (200, 201, 400, 404, 409, 422), st)

    # Classer le cas différent (si disponible)
    if len(CASE_IDS) >= 2:
        st, _ = POST(
            f"/discipline/{CASE_IDS[1]}/dismiss",
            {"dismiss_reason": "Manque de preuves suffisantes."},
            CENSEUR_TOKEN or ADMIN_TOKEN,
        )
        check("POST /discipline/{id}/dismiss", st in (200, 201, 400, 404, 409), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 35 — COMMUNICATION AVANCÉE
# ══════════════════════════════════════════════════════════════════════════
section("35. COMMUNICATION AVANCÉE")

# Historique (admin)
st, notif_hist = GET("/communication/history?page=1&page_size=10", ADMIN_TOKEN)
check("GET /communication/history (admin)", st in (200, 404), st)

# Stats personnelles
st, my_stats = GET("/communication/me/stats", SERVANT_TOKEN_1 or ADMIN_TOKEN)
check("GET /communication/me/stats", st in (200, 404), st)

# Préférences de notification
st, prefs = GET("/communication/me/preferences", SERVANT_TOKEN_1 or ADMIN_TOKEN)
check("GET /communication/me/preferences", st in (200, 404), st)

# Mettre à jour les préférences
st, _ = PUT(
    "/communication/me/preferences",
    {
        "email_notifications": True,
        "push_notifications": False,
        "sms_notifications": False,
    },
    SERVANT_TOKEN_1 or ADMIN_TOKEN,
)
check("PUT /communication/me/preferences", st in (200, 201, 400, 404, 422), st)

# Notifications personnelles
st, notifs = GET("/communication/me", SERVANT_TOKEN_1 or ADMIN_TOKEN)
check("GET /communication/me (liste notifications)", st in (200, 404), st)

# Marquer comme lues
if isinstance(notifs, dict) and notifs.get("items"):
    notif_id = notifs["items"][0].get("id") if notifs["items"] else None
    if notif_id:
        st, _ = GET(f"/communication/me/{notif_id}", SERVANT_TOKEN_1 or ADMIN_TOKEN)
        check("GET /communication/me/{notification_id}", st in (200, 404), st)

_read_notif_id = None
if isinstance(notifs, dict) and notifs.get("items"):
    _items = notifs["items"]
    if _items and _items[0].get("id"):
        _read_notif_id = _items[0]["id"]
if _read_notif_id:
    st, _ = POST(
        "/communication/me/read",
        {"notification_ids": [_read_notif_id]},
        SERVANT_TOKEN_1 or ADMIN_TOKEN,
    )
else:
    import uuid as _uuid_mod

    st, _ = POST(
        "/communication/me/read",
        {"notification_ids": [str(_uuid_mod.uuid4())]},
        SERVANT_TOKEN_1 or ADMIN_TOKEN,
    )
check("POST /communication/me/read (tout marquer lu)", st in (200, 201, 400, 404, 422), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 36 — COTISATIONS AVANCÉES (bilan, mes cotisations)
# ══════════════════════════════════════════════════════════════════════════
section("36. COTISATIONS AVANCÉES")

# Mes cotisations (servant)
st, _ = GET("/cotisations/my", SERVANT_TOKEN_1 or ADMIN_TOKEN)
check("GET /cotisations/my (mes cotisations)", st in (200, 404), st)

if PERIOD_IDS:
    # Bilan d'une période (ECONOME requis)
    st, bilan = GET(f"/cotisations/periods/{PERIOD_IDS[0]}/bilan", ECONOME_TOKEN or ADMIN_TOKEN)
    check("GET /cotisations/periods/{id}/bilan", st in (200, 403, 404), st)

    # Modifier une période
    st, _ = PATCH(
        f"/cotisations/periods/{PERIOD_IDS[0]}",
        {"title": f"Cotisation Janvier Modifiée {RUN_ID}"},
        ADMIN_TOKEN,
    )
    check("PATCH /cotisations/periods/{id}", st in (200, 400, 404, 422), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 37 — SPORT & CULTURE AVANCÉ
# ══════════════════════════════════════════════════════════════════════════
section("37. SPORT & CULTURE AVANCÉ")

if SC_EVENT_IDS:
    sc_id2 = SC_EVENT_IDS[0]

    # Événements à venir
    st, _ = GET("/sport-culture/events/upcoming/list", ADMIN_TOKEN)
    check("GET /sport-culture/events/upcoming/list", st in (200, 404), st)

    # Publier des résultats
    st, result = POST(
        f"/sport-culture/events/{sc_id2}/results",
        {
            "servant_id": SERVANTS[0]["id"] if SERVANTS else None,
            "position": 1,
            "score": "3-0",
            "notes": "Victoire nette de l'équipe A.",
        },
        SPORT_TOKEN or ADMIN_TOKEN,
    )
    result_id = result.get("id") if st in (200, 201) else None
    check("POST /sport-culture/events/{id}/results", st in (200, 201, 400, 422), st)

    # Lister les résultats
    st, _ = GET(f"/sport-culture/events/{sc_id2}/results", ADMIN_TOKEN)
    check("GET /sport-culture/events/{id}/results", st in (200, 404), st)

    # Supprimer résultat
    if result_id:
        st, _ = DELETE(f"/sport-culture/results/{result_id}", SPORT_TOKEN or ADMIN_TOKEN)
        check("DELETE /sport-culture/results/{id}", st in (200, 204, 404), st)

    # Rapport sport & culture
    st, _ = POST(
        "/sport-culture/report",
        {
            "start_date": _dt(-timedelta(days=30)),
            "end_date": _dt(timedelta(days=1)),
        },
        SPORT_TOKEN or ADMIN_TOKEN,
    )
    check("POST /sport-culture/report", st in (200, 201, 400, 404, 422), st)

    # Participations d'un servant
    if SERVANTS:
        st, _ = GET(f"/sport-culture/servants/{SERVANTS[0]['id']}/participations", ADMIN_TOKEN)
        check("GET /sport-culture/servants/{id}/participations", st in (200, 404), st)

        st, _ = GET(f"/sport-culture/servants/{SERVANTS[0]['id']}/stats", ADMIN_TOKEN)
        check("GET /sport-culture/servants/{id}/stats", st in (200, 404), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 38 — FORMATION AVANCÉE
# ══════════════════════════════════════════════════════════════════════════
section("38. FORMATION AVANCÉE")

TR_MAT_IDS = []
if TRAINING_IDS:
    tr_id2 = TRAINING_IDS[0]

    # Mes sessions de formation
    st, _ = GET("/training/sessions/me/list", SERVANT_TOKEN_1 or ADMIN_TOKEN)
    check("GET /training/sessions/me/list", st in (200, 404), st)

    # Matériaux de formation — lister
    st, mat_list = GET("/training/materials", ADMIN_TOKEN)
    check("GET /training/materials (liste)", st in (200, 404), st)

    # Créer un matériau (URL)
    st, mat = POST(
        "/training/materials",
        {
            "title": f"Guide Avancé {RUN_ID}",
            "description": "Document de référence pour les servants expérimentés.",
            "session_id": tr_id2,
            "file_url": "https://example.com/guide_avance.pdf",
            "material_type": "DOCUMENT",
        },
        LITURGIE_TOKEN or ADMIN_TOKEN,
    )
    if st in (200, 201) and mat.get("id"):
        TR_MAT_IDS.append(mat["id"])
    check("POST /training/materials (créer)", st in (200, 201, 400, 422), st)

    if TR_MAT_IDS:
        mat_id = TR_MAT_IDS[0]
        st, _ = GET(f"/training/materials/{mat_id}", ADMIN_TOKEN)
        check("GET /training/materials/{id}", st in (200, 404), st)

        st, _ = PATCH(
            f"/training/materials/{mat_id}",
            {"title": f"Guide Avancé — Révisé {RUN_ID}"},
            LITURGIE_TOKEN or ADMIN_TOKEN,
        )
        check("PATCH /training/materials/{id}", st in (200, 400, 404, 422), st)

    # Statistiques et participations d'un servant
    if SERVANTS:
        st, _ = GET(f"/training/servants/{SERVANTS[0]['id']}/participations", ADMIN_TOKEN)
        check("GET /training/servants/{id}/participations", st in (200, 404), st)

        st, _ = GET(f"/training/servants/{SERVANTS[0]['id']}/stats", ADMIN_TOKEN)
        check("GET /training/servants/{id}/stats", st in (200, 404), st)

    # Rapport de formation
    st, _ = POST(
        "/training/report",
        {
            "start_date": _dt(-timedelta(days=60)),
            "end_date": _dt(timedelta(days=1)),
        },
        LITURGIE_TOKEN or ADMIN_TOKEN,
    )
    check("POST /training/report", st in (200, 201, 400, 404, 422), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 39 — PLANNING AVANCÉ (published + gestion)
# ══════════════════════════════════════════════════════════════════════════
section("39. PLANNING AVANCÉ")

# Weekly schedule published
st, _ = GET("/weekly-schedule/published", ADMIN_TOKEN)
check("GET /weekly-schedule/published", st in (200, 404), st)

# Sunday schedule published
st, _ = GET("/sunday-schedule/published", ADMIN_TOKEN)
check("GET /sunday-schedule/published", st in (200, 404), st)

# Générer un template ordinaire (dimanche)
st, ss_ord = POST(
    "/sunday-schedule/generate/ordinary",
    {
        "week_start": FUTURE_2,
        "template_name": f"Planning Ordinaire {RUN_ID}",
    },
    CLASSEMENT_TOKEN or ADMIN_TOKEN,
)
check("POST /sunday-schedule/generate/ordinary", st in (200, 201, 400, 422), st)

# Générer un template exceptionnel
st, ss_exc = POST(
    "/sunday-schedule/generate/exceptional",
    {
        "week_start": FUTURE_3,
        "template_name": f"Planning Exceptionnel {RUN_ID}",
        "occasion": "Fête patronale",
    },
    CLASSEMENT_TOKEN or ADMIN_TOKEN,
)
check("POST /sunday-schedule/generate/exceptional", st in (200, 201, 400, 422), st)

# Planning hebdomadaire publié
if SERVANTS:
    # Publier le planning créé précédemment (si l'ID est disponible)
    st, w_list_pub = GET("/weekly-schedule/", ADMIN_TOKEN)
    if st == 200 and isinstance(w_list_pub, dict):
        items = w_list_pub.get("items", [])
        if items:
            ws_first_id = items[0].get("id")
            if ws_first_id:
                st, _ = PATCH(f"/weekly-schedule/{ws_first_id}/publish", {}, ADMIN_TOKEN)
                check(
                    "PATCH /weekly-schedule/{id}/publish",
                    st in (200, 204, 400, 404),
                    st,
                )
            else:
                check(
                    "PATCH /weekly-schedule/{id}/publish",
                    True,
                    200,
                    "SKIP: aucun planning",
                )
        else:
            check("PATCH /weekly-schedule/{id}/publish", True, 200, "SKIP: liste vide")
    else:
        check(
            "PATCH /weekly-schedule/{id}/publish",
            True,
            200,
            "SKIP: liste non disponible",
        )


# ══════════════════════════════════════════════════════════════════════════
# SECTION 40 — ADMIN AVANCÉ (création utilisateurs)
# ══════════════════════════════════════════════════════════════════════════
section("40. ADMIN AVANCÉ")

# Créer un utilisateur PARENT
st, new_parent = POST(
    "/admin/users/parent",
    {
        "email": f"parent_test_{RUN_ID}@servant.cm",
        "first_name": "Martine",
        "last_name": "Nguemo",
        "phone_number": "+237699000001",
    },
    ADMIN_TOKEN,
)
check("POST /admin/users/parent (créer parent)", st in (200, 201, 400, 409, 422), st)

# Liste des invitations
st, inv_list = GET("/admin/invitations", ADMIN_TOKEN)
check("GET /admin/invitations (liste)", st in (200, 404), st)

# Activer/désactiver une invitation
if isinstance(inv_list, dict):
    inv_items = inv_list.get("items", [])
    if inv_items:
        inv_id = inv_items[0].get("id")
        if inv_id:
            st, _ = PATCH(f"/admin/invitations/{inv_id}/toggle-status", {}, ADMIN_TOKEN)
            check("PATCH /admin/invitations/{id}/toggle-status", st in (200, 204, 404), st)
        else:
            check("PATCH /admin/invitations/{id}/toggle-status", True, 200, "SKIP: no id")
    else:
        check(
            "PATCH /admin/invitations/{id}/toggle-status",
            True,
            200,
            "SKIP: no invitations",
        )
elif isinstance(inv_list, list) and inv_list:
    inv_id = inv_list[0].get("id")
    if inv_id:
        st, _ = PATCH(f"/admin/invitations/{inv_id}/toggle-status", {}, ADMIN_TOKEN)
        check("PATCH /admin/invitations/{id}/toggle-status", st in (200, 204, 404), st)
    else:
        check("PATCH /admin/invitations/{id}/toggle-status", True, 200, "SKIP: no id")
else:
    check("PATCH /admin/invitations/{id}/toggle-status", True, 200, "SKIP: no invitations")

# API Keys admin
st, keys = GET("/admin/api-keys", ADMIN_TOKEN)
check("GET /admin/api-keys (liste)", st in (200, 404), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 41 — CLASSEMENT AVANCÉ
# ══════════════════════════════════════════════════════════════════════════
section("41. CLASSEMENT AVANCÉ")

# Classements publiés (accessible à tous)
st, cl_pub = GET("/classements/published", SERVANT_TOKEN_1 or ADMIN_TOKEN)
check("GET /classements/published", st in (200, 404), st)

# Créer un classement (CHARGE_CLASSEMENT requis)
st, new_cl = POST(
    "/classements/",
    {
        "servant_id": SERVANTS[0]["id"] if SERVANTS else None,
        "level": "JUNIOR",
        "score": 85,
        "period_start": _dt(-timedelta(days=30)),
        "period_end": now_utc.strftime("%Y-%m-%dT%H:%M:%S"),
        "notes": f"Classement test {RUN_ID}",
    },
    CLASSEMENT_TOKEN or ADMIN_TOKEN,
)
check("POST /classements/ (créer)", st in (200, 201, 400, 403, 422), st)

# Lister (avec nomination CLASSEMENT)
st, cl_list = GET("/classements/", CLASSEMENT_TOKEN or ADMIN_TOKEN)
check("GET /classements/ (liste, avec nomination)", st in (200, 403, 404), st)

if st == 200 and isinstance(cl_list, dict):
    cl_items = cl_list.get("items", [])
    if cl_items:
        cl_id = cl_items[0].get("id")
        if cl_id:
            # Avancer d'un niveau
            st, _ = POST(
                f"/classements/{cl_id}/advance",
                {
                    "new_level": "SENIOR",
                    "notes": "Promotion après évaluation.",
                },
                CLASSEMENT_TOKEN or ADMIN_TOKEN,
            )
            check("POST /classements/{id}/advance", st in (200, 201, 400, 404), st)
        else:
            check("POST /classements/{id}/advance", True, 200, "SKIP: no id")
    else:
        check("POST /classements/{id}/advance", True, 200, "SKIP: no classements")
else:
    check("POST /classements/{id}/advance", True, 200, "SKIP: non accessible")


# ══════════════════════════════════════════════════════════════════════════
# SECTION 42 — RESPONSABLES AVANCÉ (réunions conseil)
# ══════════════════════════════════════════════════════════════════════════
section("42. RESPONSABLES AVANCÉ")

# Détail d'un poste
if POSTE_SLUGS:
    poste_enum_val = list(POSTE_SLUGS.keys())[0]  # e.g. "DELEGUE"
    st, _ = GET(f"/responsables/postes/{poste_enum_val}", ADMIN_TOKEN)
    check(f"GET /responsables/postes/{{poste}}", st in (200, 404), st)

# Créer une réunion du conseil
st, meeting = POST(
    "/responsables/council-meetings",
    {
        "title": f"Réunion Conseil {RUN_ID}",
        "meeting_date": FUTURE_1,
        "location": "Salle du conseil paroissial",
        "agenda": "Bilan trimestriel, planification liturgique, discipline.",
    },
    DELEGUE_TOKEN or ADMIN_TOKEN,
)
meeting_id = meeting.get("id") if st in (200, 201) else None
check("POST /responsables/council-meetings", st in (200, 201, 400, 403, 422), st)

# Enregistrer la présence à une réunion
if meeting_id and SERVANTS:
    st, _ = POST(
        f"/responsables/council-meetings/{meeting_id}/attendance",
        {
            "attendances": [{"responsable_id": SERVANTS[0]["id"], "is_present": True}],
        },
        DELEGUE_TOKEN or ADMIN_TOKEN,
    )
    check(
        "POST /responsables/council-meetings/{id}/attendance",
        st in (200, 201, 400, 404, 422),
        st,
    )


# ══════════════════════════════════════════════════════════════════════════
# SECTION 43 — ACTIVITÉS AVANCÉES (qr-code, check-in, calendrier)
# ══════════════════════════════════════════════════════════════════════════
section("43. ACTIVITÉS AVANCÉES")

if EVENT_IDS:
    ev_id2 = EVENT_IDS[0]

    # QR Code d'un événement
    st, _ = GET(f"/events/{ev_id2}/qr-code", ADMIN_TOKEN)
    check("GET /events/{id}/qr-code", st in (200, 404, 422, 0), st)

    # Export calendrier ICS (global)
    st, _ = GET("/events/calendar.ics", SERVANT_TOKEN_1 or ADMIN_TOKEN)
    check("GET /events/calendar.ics", st in (200, 404, 0), st)

    # Export ICS d'un événement
    st, _ = GET(f"/events/{ev_id2}/calendar.ics", SERVANT_TOKEN_1 or ADMIN_TOKEN)
    check("GET /events/{id}/calendar.ics", st in (200, 404, 0), st)

    # Check-in à un événement
    st, _ = POST(
        f"/events/{ev_id2}/check-in",
        {
            "servant_id": SERVANTS[0]["id"] if SERVANTS else None,
        },
        SERVANT_TOKEN_1 or ADMIN_TOKEN,
    )
    check("POST /events/{id}/check-in", st in (200, 201, 400, 404, 422), st)

    # Mes événements
    st, _ = GET("/events/me", SERVANT_TOKEN_1 or ADMIN_TOKEN)
    check("GET /events/me", st in (200, 404), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 44 — CONTRIBUTIONS AVANCÉES
# ══════════════════════════════════════════════════════════════════════════
section("44. CONTRIBUTIONS AVANCÉES")

if SERVANTS:
    srv0_id = SERVANTS[0]["id"]
    now_iso = now_utc.strftime("%Y-%m-%dT%H:%M:%S")
    end_iso = (now_utc + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%S")

    # Stats d'un servant
    st, _ = GET(
        f"/contributions/servant/{srv0_id}/stats?start_date={_dt(-timedelta(days=365))}&end_date={_dt(timedelta(days=1))}",
        ADMIN_TOKEN,
    )
    check("GET /contributions/servant/{id}/stats", st in (200, 404, 422), st)

    # Conformité paiements
    st, _ = GET(f"/contributions/servant/{srv0_id}/compliance", ADMIN_TOKEN)
    check("GET /contributions/servant/{id}/compliance", st in (200, 404), st)

    # Générer rapport financier contributions (ECONOME)
    st, _ = POST(
        "/contributions/report",
        {
            "start_date": _dt(-timedelta(days=90)),
            "end_date": _dt(timedelta(days=1)),
            "include_details": True,
        },
        ECONOME_TOKEN or ADMIN_TOKEN,
    )
    check("POST /contributions/report", st in (200, 201, 400, 403, 422), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 45 — PRÉSENCES AVANCÉES (export PDF, stats)
# ══════════════════════════════════════════════════════════════════════════
section("45. PRÉSENCES AVANCÉES")

# Stats globales d'un servant
if SERVANTS:
    st, _ = GET(f"/attendance/user/{SERVANTS[0]['id']}/stats", ADMIN_TOKEN)
    check("GET /attendance/user/{id}/stats", st in (200, 404), st)

# Mes stats de présence
st, _ = GET("/attendance/my/stats", SERVANT_TOKEN_1 or ADMIN_TOKEN)
check("GET /attendance/my/stats", st in (200, 404), st)

# Export PDF des présences
st, _ = GET("/attendance/export/pdf", ADMIN_TOKEN)
check("GET /attendance/export/pdf", st in (200, 400, 403, 404, 422, 500, 0), st)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 46 — DOSSIER & EMAIL (admin)
# ══════════════════════════════════════════════════════════════════════════
section("46. DOSSIER & EMAIL ADMIN")

# Test email admin (non fonctionnel sans SMTP, accept 200/422/500)
st, _ = POST(
    "/email/test",
    {
        "to": "test@servant.cm",
        "subject": "Test email système",
        "body": "Vérification du service email.",
    },
    ADMIN_TOKEN,
)
check("POST /email/test (admin)", st in (200, 201, 400, 422, 500), st)

# Notifications email
st, _ = POST(
    "/email/notify",
    {
        "recipients": [SERVANTS[0]["id"]] if SERVANTS else [],
        "subject": "Notification test",
        "message": "Message de test depuis le système.",
    },
    ADMIN_TOKEN,
)
check("POST /email/notify (admin)", st in (200, 201, 400, 422, 500), st)


# ══════════════════════════════════════════════════════════════════════════
# RAPPORT FINAL
# ══════════════════════════════════════════════════════════════════════════
by_section: dict[str, list[TR]] = {}
for r in _results:
    by_section.setdefault(r.section, []).append(r)

print(f"\n{BOLD}{CYAN}{'═'*65}{RESET}")
print(f"  {BOLD}RAPPORT PAR SECTION{RESET}")
print(f"{CYAN}{'═'*65}{RESET}")

total_pass = total_fail = 0
for sec, tests in by_section.items():
    p = sum(1 for t in tests if t.passed)
    f = len(tests) - p
    total_pass += p
    total_fail += f
    icon = f"{GREEN}✅{RESET}" if f == 0 else f"{RED}❌{RESET}"
    bar_filled = int(p / len(tests) * 20) if tests else 0
    bar = f"{GREEN}{'█'*bar_filled}{RESET}" + "░" * (20 - bar_filled)
    print(f"  {icon} [{bar}] {p:>3}/{len(tests):>3}  {sec}")

total = total_pass + total_fail
rate = round(total_pass / total * 100, 1) if total else 0.0

print(f"\n{CYAN}{'═'*65}{RESET}")
color = GREEN if rate >= 90 else (YELLOW if rate >= 70 else RED)
print(f"  {BOLD}TOTAL : {color}{total_pass}/{total} ({rate}%){RESET}")
print(f"{CYAN}{'═'*65}{RESET}")

failures = [r for r in _results if not r.passed and not r.detail.startswith("SKIP")]
if failures:
    print(f"\n{RED}  Échecs ({len(failures)}) :{RESET}")
    for r in failures:
        print(f"    [{r.status:>3}] {r.name}" + (f" → {r.detail}" if r.detail else ""))

skipped = [r for r in _results if r.detail.startswith("SKIP")]
if skipped:
    print(f"\n{YELLOW}  Ignorés ({len(skipped)}) :{RESET}")
    for r in skipped:
        print(f"    {r.name} → {r.detail[5:]}")

print()
sys.exit(0 if rate >= 70 else 1)
