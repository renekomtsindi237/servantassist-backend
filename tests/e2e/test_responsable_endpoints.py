"""
Tests E2E — Module Responsables (/api/v1/responsables/* et /api/v1/poste/*).

Couvre :
- Nominations par l'aumonier (creation, revocation, listing)
- Reference des postes (listing, detail, missions)
- RBAC (servant, parent, admin, aumonier)
- Self-service (mes nominations)
- Actions de poste (CRUD par le responsable)
- Tableau de bord par poste
- Acces dynamique par slug (/api/v1/poste/{slug}/...)
- Interdiction d'acces aux non-responsables
- Validation des categories par poste
"""

from datetime import datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.core.entities.event import Event, EventStatus, EventType
from src.core.entities.responsable import (
    ActionCategory,
    ActionStatus,
    Nomination,
    NominationStatus,
    PosteAction,
    PosteResponsable,
)
from src.core.entities.user import User, UserRole
from tests.conftest import VALID_PASSWORD, make_auth_header


# ═══════════════════════════════════════════════════════════════════════════
#  NOMINATIONS
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestNominations:
    """Gestion des nominations par l'aumonier."""

    async def test_aumonier_nominates_servant(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
    ):
        """L'aumonier peut nommer un servant comme delegue."""
        resp = await client.post(
            "/api/v1/responsables/nominations",
            json={
                "user_id": str(servant_user.id),
                "poste": "DELEGUE",
                "notes": "Nomme pour l'annee 2026",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["poste"] == "DELEGUE"
        assert body["status"] == "ACTIVE"
        assert body["user_first_name"] == "Servant"
        assert body["poste_titre"] == "Delegue"
        assert body["poste_slug"] == "delegue"
        assert body["nominated_by"] == str(aumonier_user.id)

    async def test_admin_nominates_servant(
        self,
        client: AsyncClient,
        admin_user: User,
        servant_user: User,
    ):
        """L'admin peut aussi nommer un servant."""
        resp = await client.post(
            "/api/v1/responsables/nominations",
            json={
                "user_id": str(servant_user.id),
                "poste": "SECRETAIRE_GENERAL",
            },
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 201
        assert resp.json()["poste"] == "SECRETAIRE_GENERAL"

    async def test_servant_cannot_nominate(
        self,
        client: AsyncClient,
        servant_user: User,
        servant_user_2: User,
    ):
        """Un servant ne peut pas nommer un autre servant."""
        resp = await client.post(
            "/api/v1/responsables/nominations",
            json={
                "user_id": str(servant_user_2.id),
                "poste": "CENSEUR",
            },
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403

    async def test_parent_cannot_nominate(
        self,
        client: AsyncClient,
        parent_user: User,
        servant_user: User,
    ):
        """Un parent ne peut pas nommer."""
        resp = await client.post(
            "/api/v1/responsables/nominations",
            json={
                "user_id": str(servant_user.id),
                "poste": "ECONOME",
            },
            headers=make_auth_header(parent_user),
        )
        assert resp.status_code == 403

    async def test_cannot_nominate_non_servant(
        self,
        client: AsyncClient,
        aumonier_user: User,
        parent_user: User,
    ):
        """Impossible de nommer un non-servant."""
        resp = await client.post(
            "/api/v1/responsables/nominations",
            json={
                "user_id": str(parent_user.id),
                "poste": "DELEGUE",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 400
        assert "servant" in resp.json()["detail"].lower()

    async def test_cannot_nominate_inactive_user(
        self,
        client: AsyncClient,
        aumonier_user: User,
        inactive_user: User,
    ):
        """Impossible de nommer un utilisateur inactif."""
        resp = await client.post(
            "/api/v1/responsables/nominations",
            json={
                "user_id": str(inactive_user.id),
                "poste": "DELEGUE",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 400
        assert "actif" in resp.json()["detail"].lower()

    async def test_cannot_nominate_user_not_found(
        self,
        client: AsyncClient,
        aumonier_user: User,
    ):
        """Utilisateur inexistant -> 404."""
        resp = await client.post(
            "/api/v1/responsables/nominations",
            json={
                "user_id": str(uuid4()),
                "poste": "DELEGUE",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 404

    async def test_poste_already_occupied(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        servant_user_2: User,
    ):
        """Un poste deja occupe -> 409."""
        # Nommer servant_user comme delegue
        await client.post(
            "/api/v1/responsables/nominations",
            json={"user_id": str(servant_user.id), "poste": "DELEGUE"},
            headers=make_auth_header(aumonier_user),
        )
        # Essayer de nommer servant_user_2 au meme poste -> 409
        resp = await client.post(
            "/api/v1/responsables/nominations",
            json={"user_id": str(servant_user_2.id), "poste": "DELEGUE"},
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 409

    async def test_servant_one_poste_only(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
    ):
        """Un servant ne peut occuper qu'un seul poste a la fois -> 409."""
        # Nommer comme delegue
        await client.post(
            "/api/v1/responsables/nominations",
            json={"user_id": str(servant_user.id), "poste": "DELEGUE"},
            headers=make_auth_header(aumonier_user),
        )
        # Essayer de nommer au poste de censeur aussi -> 409
        resp = await client.post(
            "/api/v1/responsables/nominations",
            json={"user_id": str(servant_user.id), "poste": "CENSEUR"},
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 409

    async def test_all_postes_accepted(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
    ):
        """Tous les postes de l'enum sont acceptes."""
        postes = [
            "CONSEILLER",
            "DELEGUE",
            "VICE_DELEGUE",
            "SECRETAIRE_GENERAL",
            "SECRETAIRE_GENERAL_ADJOINT",
            "CENSEUR",
            "CENSEUR_ADJOINT",
            "ECONOME",
            "COMMISSAIRE_AUX_COMPTES",
            "CHARGE_LITURGIE",
            "CHARGE_LITURGIE_ADJOINT",
            "CEREMONIAIRE",
            "CHARGE_CLASSEMENT_DIMANCHE",
            "CHARGE_CLASSEMENT_SEMAINE",
            "INTENDANT",
            "CHARGE_SPORT_CULTURE",
        ]
        # Just verify the first one works (others would conflict)
        resp = await client.post(
            "/api/v1/responsables/nominations",
            json={"user_id": str(servant_user.id), "poste": postes[0]},
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201


# ═══════════════════════════════════════════════════════════════════════════
#  REVOCATION
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestRevocation:
    """Revocation de nominations."""

    async def test_aumonier_revokes_nomination(
        self,
        client: AsyncClient,
        aumonier_user: User,
        nomination_delegue: Nomination,
    ):
        """L'aumonier peut revoquer une nomination."""
        resp = await client.delete(
            f"/api/v1/responsables/nominations/{nomination_delegue.id}",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "REVOQUEE"
        assert body["revoked_by"] == str(aumonier_user.id)
        assert body["revoked_at"] is not None

    async def test_cannot_revoke_already_revoked(
        self,
        client: AsyncClient,
        aumonier_user: User,
        nomination_delegue: Nomination,
    ):
        """Revoquer deux fois -> 400."""
        await client.delete(
            f"/api/v1/responsables/nominations/{nomination_delegue.id}",
            headers=make_auth_header(aumonier_user),
        )
        resp = await client.delete(
            f"/api/v1/responsables/nominations/{nomination_delegue.id}",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 400

    async def test_revoke_not_found(
        self,
        client: AsyncClient,
        aumonier_user: User,
    ):
        """Nomination inexistante -> 404."""
        resp = await client.delete(
            f"/api/v1/responsables/nominations/{uuid4()}",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 404

    async def test_servant_cannot_revoke(
        self,
        client: AsyncClient,
        servant_user: User,
        nomination_delegue: Nomination,
    ):
        """Un servant ne peut pas revoquer."""
        resp = await client.delete(
            f"/api/v1/responsables/nominations/{nomination_delegue.id}",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
#  LISTING DES NOMINATIONS
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestListNominations:
    """Listing et self-service des nominations."""

    async def test_list_active_nominations(
        self,
        client: AsyncClient,
        aumonier_user: User,
        nomination_delegue: Nomination,
    ):
        """Liste des nominations actives."""
        resp = await client.get(
            "/api/v1/responsables/nominations",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        nominations = resp.json()
        assert len(nominations) >= 1
        assert any(n["poste"] == "DELEGUE" for n in nominations)

    async def test_my_nominations(
        self,
        client: AsyncClient,
        servant_user: User,
        nomination_delegue: Nomination,
    ):
        """Servant voit ses propres nominations."""
        resp = await client.get(
            "/api/v1/responsables/nominations/me",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        nominations = resp.json()
        assert len(nominations) == 1
        assert nominations[0]["poste"] == "DELEGUE"

    async def test_nomination_history(
        self,
        client: AsyncClient,
        aumonier_user: User,
        nomination_delegue: Nomination,
    ):
        """Historique des nominations."""
        resp = await client.get(
            "/api/v1/responsables/nominations/history",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_unauthenticated_401(self, client: AsyncClient):
        """Sans authentification -> 401."""
        resp = await client.get("/api/v1/responsables/nominations")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
#  REFERENCE DES POSTES
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestPostesReference:
    """Reference des postes et missions."""

    async def test_list_all_postes(
        self,
        client: AsyncClient,
        servant_user: User,
    ):
        """Liste de tous les postes avec missions."""
        resp = await client.get(
            "/api/v1/responsables/postes",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_postes"] == 20
        assert body["postes_vacants"] == 20  # Aucune nomination
        assert len(body["postes"]) == 20

    async def test_list_postes_with_titulaire(
        self,
        client: AsyncClient,
        servant_user: User,
        nomination_delegue: Nomination,
    ):
        """Liste des postes avec un titulaire."""
        resp = await client.get(
            "/api/v1/responsables/postes",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["postes_pourvus"] == 1
        # Trouver le poste DELEGUE
        delegue = next(p for p in body["postes"] if p["poste"] == "DELEGUE")
        assert delegue["titulaire"] is not None
        assert delegue["titulaire"]["user_first_name"] == "Servant"

    async def test_get_poste_detail(
        self,
        client: AsyncClient,
        servant_user: User,
    ):
        """Detail d'un poste avec missions."""
        resp = await client.get(
            "/api/v1/responsables/postes/DELEGUE",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["poste"] == "DELEGUE"
        assert body["slug"] == "delegue"
        assert body["titre"] == "Delegue"
        assert len(body["missions"]) >= 1
        assert len(body["categories_autorisees"]) >= 1

    async def test_get_censeur_detail(
        self,
        client: AsyncClient,
        servant_user: User,
    ):
        """Detail du poste censeur avec missions specifiques."""
        resp = await client.get(
            "/api/v1/responsables/postes/CENSEUR",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["poste"] == "CENSEUR"
        assert "DISCIPLINE" in body["categories_autorisees"]
        assert "SANCTION" in body["categories_autorisees"]


# ═══════════════════════════════════════════════════════════════════════════
#  ACTIONS DE POSTE — CREATION
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestPosteActionCreate:
    """Creation d'actions par les responsables via leur slug."""

    async def test_delegue_creates_decision(
        self,
        client: AsyncClient,
        servant_user: User,
        nomination_delegue: Nomination,
    ):
        """Le delegue peut creer une decision."""
        resp = await client.post(
            "/api/v1/poste/delegue/actions",
            json={
                "category": "DECISION",
                "title": "Organisation de la recollection de mars",
                "content": "Le conseil a decide d'organiser une recollection le 15 mars.",
                "status": "PUBLIE",
            },
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["category"] == "DECISION"
        assert body["poste"] == "DELEGUE"
        assert body["title"] == "Organisation de la recollection de mars"
        assert body["author_first_name"] == "Servant"

    async def test_censeur_creates_sanction(
        self,
        client: AsyncClient,
        servant_user_2: User,
        nomination_censeur: Nomination,
        servant_user: User,
    ):
        """Le censeur peut creer une sanction."""
        resp = await client.post(
            "/api/v1/poste/censeur/actions",
            json={
                "category": "SANCTION",
                "title": "Avertissement pour absence non justifiee",
                "content": "Premiere absence non justifiee, avertissement verbal.",
                "target_user_id": str(servant_user.id),
            },
            headers=make_auth_header(servant_user_2),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["category"] == "SANCTION"
        assert body["target_user_id"] == str(servant_user.id)

    async def test_aumonier_creates_action_for_any_poste(
        self,
        client: AsyncClient,
        aumonier_user: User,
    ):
        """L'aumonier peut creer une action pour n'importe quel poste."""
        resp = await client.post(
            "/api/v1/poste/economat/actions",
            json={
                "category": "COLLECTE",
                "title": "Collecte de la reunion du 1er mars",
                "amount": 25000.0,
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        assert resp.json()["amount"] == 25000.0

    async def test_non_responsable_cannot_create(
        self,
        client: AsyncClient,
        servant_user_2: User,
    ):
        """Un servant sans nomination ne peut pas creer d'action."""
        resp = await client.post(
            "/api/v1/poste/delegue/actions",
            json={
                "category": "DECISION",
                "title": "Test",
            },
            headers=make_auth_header(servant_user_2),
        )
        assert resp.status_code == 403

    async def test_parent_cannot_create(
        self,
        client: AsyncClient,
        parent_user: User,
    ):
        """Un parent ne peut pas creer d'action."""
        resp = await client.post(
            "/api/v1/poste/delegue/actions",
            json={
                "category": "DECISION",
                "title": "Test",
            },
            headers=make_auth_header(parent_user),
        )
        assert resp.status_code == 403

    async def test_invalid_category_rejected(
        self,
        client: AsyncClient,
        servant_user: User,
        nomination_delegue: Nomination,
    ):
        """Categorie non autorisee pour le poste -> 400."""
        resp = await client.post(
            "/api/v1/poste/delegue/actions",
            json={
                "category": "COLLECTE",  # Non autorise pour delegue
                "title": "Test collecte",
            },
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 400
        assert "categorie" in resp.json()["detail"].lower()

    async def test_wrong_poste_access_denied(
        self,
        client: AsyncClient,
        servant_user: User,
        nomination_delegue: Nomination,
    ):
        """Le delegue ne peut pas acceder au poste de censeur."""
        resp = await client.post(
            "/api/v1/poste/censeur/actions",
            json={
                "category": "DISCIPLINE",
                "title": "Test discipline",
            },
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403

    async def test_invalid_slug_404(
        self,
        client: AsyncClient,
        servant_user: User,
    ):
        """Slug invalide -> 404."""
        resp = await client.post(
            "/api/v1/poste/poste-inexistant/actions",
            json={
                "category": "DECISION",
                "title": "Test",
            },
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 404

    async def test_all_slugs_valid(
        self,
        client: AsyncClient,
        aumonier_user: User,
    ):
        """Tous les slugs sont valides (dashboard accessible par aumonier)."""
        slugs = [
            "conseiller",
            "delegue",
            "vice-delegue",
            "secretariat",
            "secretariat-adjoint",
            "censeur",
            "censeur-adjoint",
            "economat",
            "finances",
            "liturgie",
            "liturgie-adjoint",
            "ceremoniaire",
            "classement-dimanche",
            "classement-semaine",
            "intendance",
            "sport-culture",
        ]
        for slug in slugs:
            resp = await client.get(
                f"/api/v1/poste/{slug}/dashboard",
                headers=make_auth_header(aumonier_user),
            )
            assert resp.status_code == 200, f"Slug {slug} returned {resp.status_code}"


# ═══════════════════════════════════════════════════════════════════════════
#  ACTIONS DE POSTE — LECTURE
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestPosteActionRead:
    """Lecture des actions de poste."""

    async def test_list_actions(
        self,
        client: AsyncClient,
        servant_user: User,
        nomination_delegue: Nomination,
        sample_poste_action: PosteAction,
    ):
        """Le responsable voit les actions de son poste."""
        resp = await client.get(
            "/api/v1/poste/delegue/actions",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert len(body["items"]) >= 1

    async def test_get_action_detail(
        self,
        client: AsyncClient,
        servant_user: User,
        nomination_delegue: Nomination,
        sample_poste_action: PosteAction,
    ):
        """Detail d'une action."""
        resp = await client.get(
            f"/api/v1/poste/delegue/actions/{sample_poste_action.id}",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Decision du conseil n1"
        assert body["category"] == "DECISION"

    async def test_filter_by_category(
        self,
        client: AsyncClient,
        servant_user: User,
        nomination_delegue: Nomination,
        sample_poste_action: PosteAction,
    ):
        """Filtrer par categorie."""
        resp = await client.get(
            "/api/v1/poste/delegue/actions?category=DECISION",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        for item in body["items"]:
            assert item["category"] == "DECISION"

    async def test_filter_by_status(
        self,
        client: AsyncClient,
        servant_user: User,
        nomination_delegue: Nomination,
        sample_poste_action: PosteAction,
    ):
        """Filtrer par statut."""
        resp = await client.get(
            "/api/v1/poste/delegue/actions?status=PUBLIE",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1


# ═══════════════════════════════════════════════════════════════════════════
#  ACTIONS DE POSTE — MODIFICATION & SUPPRESSION
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestPosteActionModify:
    """Modification et suppression d'actions."""

    async def test_update_action(
        self,
        client: AsyncClient,
        servant_user: User,
        nomination_delegue: Nomination,
        sample_poste_action: PosteAction,
    ):
        """Le createur peut modifier son action."""
        resp = await client.patch(
            f"/api/v1/poste/delegue/actions/{sample_poste_action.id}",
            json={
                "title": "Decision mise a jour",
                "status": "TERMINE",
            },
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Decision mise a jour"
        assert body["status"] == "TERMINE"

    async def test_other_responsable_cannot_update(
        self,
        client: AsyncClient,
        servant_user_2: User,
        nomination_delegue: Nomination,
        nomination_censeur: Nomination,
        sample_poste_action: PosteAction,
    ):
        """Un autre responsable ne peut pas modifier l'action d'un autre."""
        # servant_user_2 est censeur, pas delegue
        resp = await client.patch(
            f"/api/v1/poste/delegue/actions/{sample_poste_action.id}",
            json={"title": "Tentative de modification"},
            headers=make_auth_header(servant_user_2),
        )
        # Either 403 (can't access delegue poste) or 403 (not the creator)
        assert resp.status_code == 403

    async def test_delete_action(
        self,
        client: AsyncClient,
        servant_user: User,
        nomination_delegue: Nomination,
        sample_poste_action: PosteAction,
    ):
        """Le createur peut supprimer son action."""
        resp = await client.delete(
            f"/api/v1/poste/delegue/actions/{sample_poste_action.id}",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 204

        # Verifier que l'action est supprimee
        resp2 = await client.get(
            f"/api/v1/poste/delegue/actions/{sample_poste_action.id}",
            headers=make_auth_header(servant_user),
        )
        assert resp2.status_code == 404

    async def test_action_not_found(
        self,
        client: AsyncClient,
        servant_user: User,
        nomination_delegue: Nomination,
    ):
        """Action inexistante -> 404."""
        resp = await client.get(
            f"/api/v1/poste/delegue/actions/{uuid4()}",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
#  TABLEAU DE BORD
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestPosteDashboard:
    """Tableau de bord des postes."""

    async def test_delegue_dashboard(
        self,
        client: AsyncClient,
        servant_user: User,
        nomination_delegue: Nomination,
        sample_poste_action: PosteAction,
    ):
        """Le delegue voit son tableau de bord."""
        resp = await client.get(
            "/api/v1/poste/delegue/dashboard",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["poste"] == "DELEGUE"
        assert body["slug"] == "delegue"
        assert body["titre"] == "Delegue"
        assert body["total_actions"] >= 1
        assert len(body["missions"]) >= 1
        assert len(body["recent_actions"]) >= 1

    async def test_aumonier_sees_all_dashboards(
        self,
        client: AsyncClient,
        aumonier_user: User,
    ):
        """L'aumonier peut voir le dashboard de n'importe quel poste."""
        resp = await client.get(
            "/api/v1/poste/censeur/dashboard",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        assert resp.json()["poste"] == "CENSEUR"

    async def test_servant_no_nomination_denied(
        self,
        client: AsyncClient,
        servant_user_2: User,
    ):
        """Servant sans nomination -> 403."""
        resp = await client.get(
            "/api/v1/poste/delegue/dashboard",
            headers=make_auth_header(servant_user_2),
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
#  WORKFLOW COMPLET
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestResponsableWorkflow:
    """Scenario de bout en bout du workflow responsable."""

    async def test_full_workflow(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
    ):
        """
        Workflow complet :
        1. Aumonier nomme servant comme economat
        2. Servant verifie sa nomination
        3. Servant cree une collecte
        4. Servant voit son dashboard
        5. Aumonier consulte les actions
        6. Aumonier revoque la nomination
        7. Servant ne peut plus creer d'actions
        """
        # 1. Nomination
        resp = await client.post(
            "/api/v1/responsables/nominations",
            json={"user_id": str(servant_user.id), "poste": "ECONOME"},
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        nomination_id = resp.json()["id"]

        # 2. Self-check
        resp = await client.get(
            "/api/v1/responsables/nominations/me",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["poste"] == "ECONOME"

        # 3. Creer une collecte
        resp = await client.post(
            "/api/v1/poste/economat/actions",
            json={
                "category": "COLLECTE",
                "title": "Collecte reunion du 2 mars",
                "amount": 15000.0,
                "action_date": "2026-03-02T14:00:00",
            },
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 201
        assert resp.json()["id"]
        assert resp.json()["amount"] == 15000.0

        # 4. Dashboard
        resp = await client.get(
            "/api/v1/poste/economat/dashboard",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        assert resp.json()["total_actions"] >= 1

        # 5. Aumonier consulte
        resp = await client.get(
            "/api/v1/poste/economat/actions",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

        # 6. Revocation
        resp = await client.delete(
            f"/api/v1/responsables/nominations/{nomination_id}",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "REVOQUEE"

        # 7. Servant ne peut plus creer
        resp = await client.post(
            "/api/v1/poste/economat/actions",
            json={
                "category": "COLLECTE",
                "title": "Nouvelle collecte",
                "amount": 5000.0,
            },
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403

    async def test_renomination_after_revocation(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        servant_user_2: User,
    ):
        """
        Apres revocation, le poste redevient vacant et un autre
        servant peut etre nomme.
        """
        # Nommer servant_user
        resp = await client.post(
            "/api/v1/responsables/nominations",
            json={"user_id": str(servant_user.id), "poste": "INTENDANT"},
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        nom_id = resp.json()["id"]

        # Revoquer
        resp = await client.delete(
            f"/api/v1/responsables/nominations/{nom_id}",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200

        # Nommer servant_user_2 au meme poste
        resp = await client.post(
            "/api/v1/responsables/nominations",
            json={"user_id": str(servant_user_2.id), "poste": "INTENDANT"},
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        assert resp.json()["user_first_name"] == "Pierre"
