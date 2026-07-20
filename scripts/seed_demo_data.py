"""
Script de seed — jeu de données de démonstration complet, couvrant tous les
modules de l'app (membres, nominations, planning, présences, trésorerie,
communication, matériel, formation, discipline, sports & culture, rapports,
cotisations, conseil). Utilisé pour peupler un environnement local/dev avec
des données lisibles (chiffrées avec la clé locale), sans dépendre de la
clé de production/staging.

Certaines actions sont réservées à des postes précis (le backend vérifie le
poste réel, pas juste le rôle ADMIN) : nominations -> AUMÔNIER, présences ->
CENSEUR, trésorerie -> COMMISSAIRE_AUX_COMPTES, rapports -> SECRETAIRE.
Ce script se reconnecte donc avec le compte titulaire du poste requis pour
chaque étape, exactement comme le ferait un vrai utilisateur.

À la fin, exporte un CSV des identifiants (scripts/seed_credentials.csv)
pour se reconnecter avec n'importe quel compte créé.

Utilisation :
  python scripts/seed_users.py      # 20 servants, 8 parents, 1 aumônier
  python scripts/seed_demo_data.py  # nominations + toutes les données métier

Prérequis : le compte ADMIN existe déjà (scripts/init_db.py), le backend
tourne sur localhost:8000 (exécuté depuis l'intérieur du conteneur backend).
"""

import csv
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

BASE = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "renekomtsindi7@gmail.com"
ADMIN_PASSWORD = "Mbetoumou olive77"
SEED_PASSWORD = "ServantTest2026!"
CSV_PATH = "scripts/seed_credentials.csv"

# 13 servants nommés à un poste de responsable (sur les 20) ; les 7 autres
# restent de simples servants — mélange volontaire pour couvrir les deux cas.
POSTES_PLAN = [
    ("DELEGUE", 0), ("VICE_DELEGUE", 1), ("CENSEUR", 2), ("CENSEUR_ADJOINT", 3),
    ("SECRETAIRE_GENERAL", 4), ("SECRETAIRE_GENERAL_ADJOINT", 5),
    ("COMMISSAIRE_AUX_COMPTES", 6), ("ECONOME", 7), ("CHARGE_LITURGIE", 8),
    ("CEREMONIAIRE", 9), ("CHARGE_CLASSEMENT_DIMANCHE", 10),
    ("INTENDANT", 11), ("CHARGE_SPORT_CULTURE", 12),
]

# Grille standard d'un classement dimanche (miroir de mkStandardPostes() —
# web, planning.ts) : 9 fonctions nommées + 9 céroféraires, chacune avec un
# titulaire (col1) et un remplaçant (col2).
STANDARD_LABELS = [
    "Cérémoniaires 1", "Cérémoniaires 2", "Responsable", "Cruciféraire",
    "Acolyte 1", "Acolyte 2", "Acolyte 3", "Thuriféraire", "Portes insignes",
]
CERO_COUNT = 9


def _request(method, path, token=None, data=None, form=None, params=None):
    url = f"{BASE}{path}"
    if params:
        qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
        url = f"{url}?{qs}"
    headers = {}
    body = None
    if form is not None:
        body = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw.decode(errors="replace")


def ok(label, status, body):
    mark = "OK " if status < 300 else "ERR"
    print(f"[{mark}] {label} -> {status}" + ("" if status < 300 else f" :: {body}"))
    return status < 300


def login(identifier, password):
    """Email+mdp (ADMIN/AUMÔNIER) via /auth/login, téléphone (SERVANT/PARENT) via /auth/login/phone."""
    if identifier.startswith("+"):
        status, resp = _request("POST", "/auth/login/phone", data={"phone_number": identifier, "password": password})
    else:
        status, resp = _request("POST", "/auth/login", form={"username": identifier, "password": password})
    assert status == 200, f"Login {identifier} échoué: {resp}"
    return resp["access_token"]


def main():
    admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    print("Connecté en tant qu'admin.\n")

    status, directory = _request("GET", "/users/directory", token=admin_token, params={"page": 1, "page_size": 50})
    servants = [u for u in directory["items"] if u["role"] == "SERVANT"]
    parents = [u for u in directory["items"] if u["role"] == "PARENT"]
    aumonier = next(u for u in directory["items"] if u["role"] == "AUMÔNIER")
    print(f"{len(servants)} servants, {len(parents)} parents, 1 aumônier trouvés.\n")

    aumonier_token = login(aumonier["phone_number"] or aumonier["email"], SEED_PASSWORD)

    poste_holder = {}
    for poste, idx in POSTES_PLAN:
        if idx >= len(servants):
            continue
        sid = servants[idx]["id"]
        status, resp = _request(
            "POST", "/responsables/nominations", token=aumonier_token,
            data={"user_id": sid, "poste": poste, "notes": "Nomination de démonstration (seed)"},
        )
        if ok(f"Nominer {servants[idx]['first_name']} -> {poste}", status, resp):
            poste_holder[poste] = servants[idx]
    print()

    # ── Classement complet (grille standard, tous les rôles pourvus) ────
    next_sunday = date.today() + timedelta(days=(6 - date.today().weekday()) % 7 + 7)
    postes_grid = []
    name_cycle = [f"{s['first_name']} {s['last_name']}" for s in servants]
    cursor = 0

    def next_name():
        nonlocal cursor
        n = name_cycle[cursor % len(name_cycle)]
        cursor += 1
        return n

    for label in STANDARD_LABELS:
        postes_grid.append({"label": label, "col1": next_name(), "col2": next_name()})
    for i in range(CERO_COUNT):
        postes_grid.append({"label": "Céroféraires" if i == 0 else "", "col1": next_name(), "col2": next_name()})

    status, classement = _request(
        "POST", "/classements/", token=admin_token,
        data={
            "type": "DIMANCHE", "date": next_sunday.isoformat(), "heure": "09:00",
            "lieu": "Basilique Marie Reine des Apôtres", "solennite": "Dimanche ordinaire",
            "couleur_liturgique": "VERT", "postes": postes_grid,
        },
    )
    ok(f"Créer classement complet ({len(postes_grid)} postes pourvus)", status, classement)

    # ── Présences (CENSEUR) — appel sur TOUS les servants ────────────
    if "CENSEUR" in poste_holder:
        censeur_token = login(poste_holder["CENSEUR"]["phone_number"], SEED_PASSWORD)
        status, session = _request(
            "POST", "/attendance-sessions/", token=censeur_token,
            data={"session_date": date.today().isoformat(), "session_time": "09:00", "location": "Basilique"},
        )
        if ok("Créer session de présence", status, session):
            sid = session["id"]
            status, _ = _request("POST", f"/attendance-sessions/{sid}/init-roll-call", token=censeur_token)
            ok("Initialiser l'appel", status, None)
            status, detail = _request("GET", f"/attendance-sessions/{sid}", token=censeur_token)
            if status == 200:
                records = detail.get("records", [])
                cycle = ["PRESENT", "PRESENT", "PRESENT", "ABSENT", "LATE", "EXCUSED"]
                for i, rec in enumerate(records):
                    st, _ = _request("PATCH", f"/attendance-sessions/records/{rec['id']}", token=censeur_token, data={"status": cycle[i % len(cycle)]})
                    ok(f"  Présence {i+1}/{len(records)}", st, None) if st >= 300 else None
                print(f"  {len(records)} présences enregistrées.")

    # ── Trésorerie (COMMISSAIRE_AUX_COMPTES) ─────────────────────────
    if "COMMISSAIRE_AUX_COMPTES" in poste_holder:
        commissaire_token = login(poste_holder["COMMISSAIRE_AUX_COMPTES"]["phone_number"], SEED_PASSWORD)
        entries = [
            {"date": date.today().isoformat(), "amount": 25000, "category": "COTISATION", "source": "SERVANT", "description": "Collecte cotisations mensuelles"},
            {"date": date.today().isoformat(), "amount": 15000, "category": "DON", "source": "EXTERNE", "description": "Don d'un fidèle"},
            {"date": date.today().isoformat(), "amount": 8000, "category": "EVENEMENT", "source": "EVENEMENT", "description": "Recette tournoi sportif"},
            {"date": date.today().isoformat(), "amount": 12000, "category": "CONTRIBUTION", "source": "PAROISSE", "description": "Appui de la paroisse"},
            {"date": date.today().isoformat(), "amount": 5000, "category": "AUTRE", "source": "AUTRE", "description": "Vente de calendriers"},
        ]
        for e in entries:
            status, resp = _request("POST", "/financial-entries/", token=commissaire_token, data=e)
            ok(f"Écriture trésorerie : {e['description']}", status, resp)

    # ── Matériel ──────────────────────────────────────────────────────
    materials = [
        {"name": "Aube blanche (taille M)", "category": "AUBE", "quantity": 15, "condition": "BON", "location": "Sacristie"},
        {"name": "Encensoir en laiton", "category": "ENCENSOIR", "quantity": 2, "condition": "BON", "location": "Sacristie"},
        {"name": "Croix de procession", "category": "CROIX", "quantity": 1, "condition": "A_REPARER", "location": "Sacristie"},
        {"name": "Cierges pascals", "category": "CIERGE", "quantity": 40, "condition": "BON", "location": "Réserve"},
        {"name": "Nappe d'autel brodée", "category": "NAPPE", "quantity": 3, "condition": "A_NETTOYER", "location": "Sacristie"},
    ]
    for m in materials:
        status, resp = _request("POST", "/material/items", token=admin_token, data=m)
        ok(f"Article matériel : {m['name']}", status, resp)

    # ── Formation ──────────────────────────────────────────────────────
    trainings = [
        {"title": "Initiation au service de l'autel", "description": "Formation des nouveaux servants", "level": "DEBUTANT",
         "date": (date.today() + timedelta(days=10)).isoformat(), "start_time": "14h00", "end_time": "16h00",
         "duration_minutes": 120, "location": "Salle paroissiale", "trainer_id": aumonier["id"]},
        {"title": "Perfectionnement thuriféraire", "description": "Technique de l'encensement", "level": "AVANCE",
         "date": (date.today() + timedelta(days=17)).isoformat(), "start_time": "14h00", "end_time": "15h30",
         "duration_minutes": 90, "location": "Basilique", "trainer_id": aumonier["id"]},
    ]
    for t in trainings:
        status, resp = _request("POST", "/training/sessions", token=admin_token, data=t)
        ok(f"Session de formation : {t['title']}", status, resp)

    # ── Sports & Culture ──────────────────────────────────────────────
    events = [
        {"title": "Tournoi de football inter-délégations", "description": "Match amical annuel", "event_type": "TOURNOI",
         "date": (date.today() + timedelta(days=20)).isoformat(), "start_time": "09h00", "end_time": "17h00",
         "location": "Terrain paroissial", "max_participants": 30},
        {"title": "Sortie culturelle au musée national", "description": "Visite guidée", "event_type": "SORTIE_CULTURELLE",
         "date": (date.today() + timedelta(days=25)).isoformat(), "start_time": "08h00", "end_time": "13h00",
         "location": "Musée national", "max_participants": 25},
    ]
    for e in events:
        status, resp = _request("POST", "/sport-culture/events", token=admin_token, data=e)
        ok(f"Événement sports & culture : {e['title']}", status, resp)

    # ── Rapports (SECRETAIRE) — publiés pour être visibles par défaut ──
    if "SECRETAIRE_GENERAL" in poste_holder:
        secretaire_token = login(poste_holder["SECRETAIRE_GENERAL"]["phone_number"], SEED_PASSWORD)
        reports = [
            {"type": "REUNION", "title": "Réunion mensuelle de la délégation",
             "content": "Bilan des activités du mois, préparation des prochains événements liturgiques.",
             "report_date": date.today().isoformat(), "location": "Salle paroissiale"},
            {"type": "ACTIVITE", "title": "Compte-rendu du tournoi de football",
             "content": "Bonne participation, ambiance conviviale, à reconduire l'an prochain.",
             "report_date": (date.today() - timedelta(days=5)).isoformat(), "location": "Terrain paroissial"},
        ]
        for r in reports:
            status, report = _request("POST", "/reports/", token=secretaire_token, data=r)
            if ok(f"Rapport : {r['title']}", status, report):
                status, _ = _request("POST", f"/reports/{report['id']}/publish", token=secretaire_token)
                ok("  Publié", status, None)

    # ── Discipline ────────────────────────────────────────────────────
    if len(servants) > 15:
        status, case = _request(
            "POST", "/discipline/", token=admin_token,
            data={
                "accused_user_id": servants[15]["id"], "offense_category": "RETARD_REPETE",
                "offense_description": "Retards répétés aux répétitions du samedi (démonstration).",
                "severity": "MINEUR",
            },
        )
        ok("Créer dossier disciplinaire", status, case)

    # ── Convocations ──────────────────────────────────────────────────
    status, resp = _request(
        "POST", "/convocations/", token=admin_token,
        data={"servant_id": servants[16]["id"] if len(servants) > 16 else servants[0]["id"], "motif": "ABSENCES_REPETEES", "details": "Convocation de démonstration"},
    )
    ok("Créer convocation", status, resp)

    # ── Communication ─────────────────────────────────────────────────
    status, resp = _request(
        "POST", "/communication/broadcast", token=admin_token,
        data={"target": "all", "notification_type": "GENERAL", "channel": "IN_APP", "title": "Bienvenue", "body": "Message de test — environnement de démonstration."},
    )
    ok("Diffuser communication", status, resp)

    # ── Cotisations (500 FCFA/mois — Art. 22) — plusieurs paiements ───
    status, period = _request(
        "POST", "/cotisations/periods", token=admin_token,
        data={
            "title": "Cotisation mensuelle — mois en cours", "cotisation_type": "ORDINAIRE", "period_type": "MENSUEL",
            "amount_expected": 500, "start_date": date.today().isoformat() + "T00:00:00",
            "end_date": (date.today() + timedelta(days=30)).isoformat() + "T00:00:00",
        },
    )
    if ok("Créer période de cotisation", status, period):
        for s in servants[:8]:
            status, resp = _request(
                "POST", "/cotisations/payments", token=admin_token,
                data={"period_id": period["id"], "user_id": s["id"], "amount_paid": 500, "payment_method": "ESPECES"},
            )
            ok(f"  Paiement cotisation : {s['first_name']} {s['last_name']}", status, None) if status >= 300 else None
        print("  8 paiements de cotisation enregistrés.")

    # ── Conseil des responsables ──────────────────────────────────────
    status, resp = _request(
        "POST", "/responsables/council-meetings", token=admin_token,
        data={"meeting_date": (date.today() + timedelta(days=7)).isoformat(), "location": "Salle paroissiale", "agenda": "Point sur les activités du trimestre."},
    )
    ok("Créer réunion du conseil", status, resp)

    # ── Export CSV des identifiants ────────────────────────────────────
    poste_by_servant_id = {s["id"]: poste for poste, s in poste_holder.items()}
    rows = [{
        "nom_complet": "René Komtsindi", "role": "ADMIN", "poste": "",
        "identifiant": ADMIN_EMAIL, "mot_de_passe": ADMIN_PASSWORD,
    }, {
        "nom_complet": f"{aumonier['first_name']} {aumonier['last_name']}", "role": "AUMÔNIER", "poste": "",
        "identifiant": aumonier["email"], "mot_de_passe": SEED_PASSWORD,
    }]
    for s in servants:
        rows.append({
            "nom_complet": f"{s['first_name']} {s['last_name']}", "role": "SERVANT",
            "poste": poste_by_servant_id.get(s["id"], ""),
            "identifiant": s["phone_number"], "mot_de_passe": SEED_PASSWORD,
        })
    for p in parents:
        rows.append({
            "nom_complet": f"{p['first_name']} {p['last_name']}", "role": "PARENT", "poste": "",
            "identifiant": f"{p['phone_number']} / {p.get('email', '')}", "mot_de_passe": SEED_PASSWORD,
        })

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["nom_complet", "role", "poste", "identifiant", "mot_de_passe"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nCSV des identifiants exporté : {CSV_PATH} ({len(rows)} comptes).")

    print("\nSeed terminé.")


if __name__ == "__main__":
    main()
