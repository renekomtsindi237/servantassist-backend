"""
Tests E2E pour les endpoints de gestion du matériel (INTENDANTS).
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.core.entities.material import (
    MaterialCategory,
    MaterialCondition,
    TaskStatus,
    TaskType,
)

# ══════════════════════════════════════════════════════════════════
#  TESTS - ARTICLES DE MATÉRIEL
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_material_item_success(
    client: AsyncClient,
    intendant_token: str,
):
    """Test création d'un article de matériel."""
    response = await client.post(
        "/api/v1/material/items",
        json={
            "name": "Encensoir doré",
            "category": "ENCENSOIR",
            "description": "Encensoir en laiton doré",
            "quantity": 2,
            "condition": "BON",
            "location": "Sacristie - Armoire B",
            "purchase_date": "2025-01-15T00:00:00",
        },
        headers={"Authorization": f"Bearer {intendant_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Encensoir doré"
    assert data["category"] == "ENCENSOIR"
    assert data["condition"] == "BON"


@pytest.mark.asyncio
async def test_create_material_item_forbidden(
    client: AsyncClient,
    servant_token: str,
):
    """Test création interdite pour un servant normal."""
    response = await client.post(
        "/api/v1/material/items",
        json={
            "name": "Test",
            "category": "AUTRE",
            "quantity": 1,
            "location": "Test",
        },
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_material_items(
    client: AsyncClient,
    servant_token: str,
    sample_material_item,
):
    """Test liste des articles."""
    response = await client.get(
        "/api/v1/material/items",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_get_material_item(
    client: AsyncClient,
    servant_token: str,
    sample_material_item,
):
    """Test récupération d'un article."""
    response = await client.get(
        f"/api/v1/material/items/{sample_material_item.id}",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_material_item.id)
    assert data["name"] == sample_material_item.name


@pytest.mark.asyncio
async def test_update_material_item(
    client: AsyncClient,
    intendant_token: str,
    sample_material_item,
):
    """Test modification d'un article."""
    response = await client.patch(
        f"/api/v1/material/items/{sample_material_item.id}",
        json={"condition": "A_NETTOYER"},
        headers={"Authorization": f"Bearer {intendant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["condition"] == "A_NETTOYER"


@pytest.mark.asyncio
async def test_delete_material_item(
    client: AsyncClient,
    intendant_token: str,
    sample_material_item,
):
    """Test suppression d'un article."""
    response = await client.delete(
        f"/api/v1/material/items/{sample_material_item.id}",
        headers={"Authorization": f"Bearer {intendant_token}"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_get_items_needing_maintenance(
    client: AsyncClient,
    servant_token: str,
):
    """Test liste des articles nécessitant maintenance."""
    response = await client.get(
        "/api/v1/material/items/maintenance/needed",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


# ══════════════════════════════════════════════════════════════════
#  TESTS - TÂCHES DE NETTOYAGE
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_cleaning_task_success(
    client: AsyncClient,
    intendant_token: str,
):
    """Test création d'une tâche de nettoyage."""
    response = await client.post(
        "/api/v1/material/cleaning-tasks",
        json={
            "title": "Nettoyage des calices",
            "description": "Nettoyage complet des calices",
            "task_type": "NETTOYAGE",
            "scheduled_date": "2026-03-01T10:00:00",
            "scheduled_time": "10h00",
            "location": "Sacristie",
            "items": ["Calice principal", "Calice secondaire"],
        },
        headers={"Authorization": f"Bearer {intendant_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Nettoyage des calices"
    assert data["task_type"] == "NETTOYAGE"
    assert data["status"] == "PLANIFIEE"


@pytest.mark.asyncio
async def test_list_cleaning_tasks(
    client: AsyncClient,
    servant_token: str,
    sample_cleaning_task,
):
    """Test liste des tâches."""
    response = await client.get(
        "/api/v1/material/cleaning-tasks",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_cleaning_task(
    client: AsyncClient,
    servant_token: str,
    sample_cleaning_task,
):
    """Test récupération d'une tâche."""
    response = await client.get(
        f"/api/v1/material/cleaning-tasks/{sample_cleaning_task.id}",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_cleaning_task.id)


@pytest.mark.asyncio
async def test_update_cleaning_task(
    client: AsyncClient,
    intendant_token: str,
    sample_cleaning_task,
):
    """Test modification d'une tâche."""
    response = await client.patch(
        f"/api/v1/material/cleaning-tasks/{sample_cleaning_task.id}",
        json={"title": "Tâche modifiée"},
        headers={"Authorization": f"Bearer {intendant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Tâche modifiée"


@pytest.mark.asyncio
async def test_complete_cleaning_task(
    client: AsyncClient,
    servant_token: str,
    sample_cleaning_task,
):
    """Test marquage comme terminée."""
    response = await client.post(
        f"/api/v1/material/cleaning-tasks/{sample_cleaning_task.id}/complete",
        json={
            "photos_after": ["https://storage.example.com/after1.jpg"],
            "notes": "Nettoyage effectué",
        },
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "TERMINEE"


@pytest.mark.asyncio
async def test_validate_cleaning_task(
    client: AsyncClient,
    intendant_token: str,
    sample_cleaning_task,
    servant_token: str,
):
    """Test validation d'une tâche."""
    # D'abord marquer comme terminée
    await client.post(
        f"/api/v1/material/cleaning-tasks/{sample_cleaning_task.id}/complete",
        json={},
        headers={"Authorization": f"Bearer {servant_token}"},
    )

    # Puis valider
    response = await client.post(
        f"/api/v1/material/cleaning-tasks/{sample_cleaning_task.id}/validate",
        json={"notes": "Travail bien fait"},
        headers={"Authorization": f"Bearer {intendant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "VALIDEE"


@pytest.mark.asyncio
async def test_delete_cleaning_task(
    client: AsyncClient,
    intendant_token: str,
    sample_cleaning_task,
):
    """Test suppression d'une tâche."""
    response = await client.delete(
        f"/api/v1/material/cleaning-tasks/{sample_cleaning_task.id}",
        headers={"Authorization": f"Bearer {intendant_token}"},
    )
    assert response.status_code == 204


# ══════════════════════════════════════════════════════════════════
#  TESTS - ASSIGNATIONS
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_assign_servant_to_task(
    client: AsyncClient,
    intendant_token: str,
    sample_cleaning_task,
    servant_user,
):
    """Test assignation d'un servant."""
    response = await client.post(
        f"/api/v1/material/cleaning-tasks/{sample_cleaning_task.id}/assign",
        json={"servant_id": str(servant_user.id)},
        headers={"Authorization": f"Bearer {intendant_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["task_id"] == str(sample_cleaning_task.id)
    assert data["servant_id"] == str(servant_user.id)


@pytest.mark.asyncio
async def test_assign_servants_batch(
    client: AsyncClient,
    intendant_token: str,
    sample_cleaning_task,
    servant_user,
    servant_user_2,
):
    """Test assignation par lot."""
    response = await client.post(
        f"/api/v1/material/cleaning-tasks/{sample_cleaning_task.id}/assign-batch",
        json={
            "servant_ids": [str(servant_user.id), str(servant_user_2.id)],
        },
        headers={"Authorization": f"Bearer {intendant_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_servant_assignments(
    client: AsyncClient,
    servant_token: str,
    servant_user,
    sample_task_assignment,
):
    """Test liste des assignations d'un servant."""
    response = await client.get(
        f"/api/v1/material/servants/{servant_user.id}/assignments",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_remove_assignment(
    client: AsyncClient,
    intendant_token: str,
    sample_task_assignment,
):
    """Test retrait d'une assignation."""
    response = await client.delete(
        f"/api/v1/material/assignments/{sample_task_assignment.id}",
        headers={"Authorization": f"Bearer {intendant_token}"},
    )
    assert response.status_code == 204


# ══════════════════════════════════════════════════════════════════
#  TESTS - TÂCHES D'AUBES
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_aube_task_success(
    client: AsyncClient,
    intendant_token: str,
):
    """Test création d'une tâche d'aubes."""
    response = await client.post(
        "/api/v1/material/aube-tasks",
        json={
            "title": "Lavage des aubes",
            "task_type": "LAVAGE",
            "scheduled_date": "2026-03-05T14:00:00",
            "scheduled_time": "14h00",
            "location": "Buanderie",
            "aube_count": 15,
            "aube_sizes": ["S", "M", "L", "XL"],
            "broadcast_notification": True,
        },
        headers={"Authorization": f"Bearer {intendant_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Lavage des aubes"
    assert data["task_type"] == "LAVAGE"
    assert data["aube_count"] == 15
    assert data["broadcast_notification"] is True


@pytest.mark.asyncio
async def test_list_aube_tasks(
    client: AsyncClient,
    servant_token: str,
    sample_aube_task,
):
    """Test liste des tâches d'aubes."""
    response = await client.get(
        "/api/v1/material/aube-tasks",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_aube_task(
    client: AsyncClient,
    servant_token: str,
    sample_aube_task,
):
    """Test récupération d'une tâche d'aubes."""
    response = await client.get(
        f"/api/v1/material/aube-tasks/{sample_aube_task.id}",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_aube_task.id)


@pytest.mark.asyncio
async def test_update_aube_task(
    client: AsyncClient,
    intendant_token: str,
    sample_aube_task,
):
    """Test modification d'une tâche d'aubes."""
    response = await client.patch(
        f"/api/v1/material/aube-tasks/{sample_aube_task.id}",
        json={"aube_count": 20},
        headers={"Authorization": f"Bearer {intendant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["aube_count"] == 20


@pytest.mark.asyncio
async def test_complete_aube_task(
    client: AsyncClient,
    servant_token: str,
    sample_aube_task,
):
    """Test marquage comme terminée."""
    response = await client.post(
        f"/api/v1/material/aube-tasks/{sample_aube_task.id}/complete",
        json={
            "photos_after": ["https://storage.example.com/aubes_clean.jpg"],
            "notes": "Lavage terminé",
        },
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "TERMINEE"


@pytest.mark.asyncio
async def test_validate_aube_task(
    client: AsyncClient,
    intendant_token: str,
    sample_aube_task,
    servant_token: str,
):
    """Test validation d'une tâche d'aubes."""
    # D'abord marquer comme terminée
    await client.post(
        f"/api/v1/material/aube-tasks/{sample_aube_task.id}/complete",
        json={},
        headers={"Authorization": f"Bearer {servant_token}"},
    )

    # Puis valider
    response = await client.post(
        f"/api/v1/material/aube-tasks/{sample_aube_task.id}/validate",
        json={"notes": "Excellent travail"},
        headers={"Authorization": f"Bearer {intendant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "VALIDEE"


@pytest.mark.asyncio
async def test_delete_aube_task(
    client: AsyncClient,
    intendant_token: str,
    sample_aube_task,
):
    """Test suppression d'une tâche d'aubes."""
    response = await client.delete(
        f"/api/v1/material/aube-tasks/{sample_aube_task.id}",
        headers={"Authorization": f"Bearer {intendant_token}"},
    )
    assert response.status_code == 204


# ══════════════════════════════════════════════════════════════════
#  TESTS - HISTORIQUE DE MAINTENANCE
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_add_maintenance_history(
    client: AsyncClient,
    intendant_token: str,
    sample_material_item,
):
    """Test ajout d'un historique de maintenance."""
    response = await client.post(
        f"/api/v1/material/items/{sample_material_item.id}/maintenance",
        json={
            "maintenance_type": "LAVAGE",
            "description": "Lavage et repassage",
            "performed_date": "2026-02-15T10:00:00",
            "cost": 500.0,
            "notes": "Maintenance effectuée",
        },
        headers={"Authorization": f"Bearer {intendant_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["maintenance_type"] == "LAVAGE"
    assert data["cost"] == 500.0


@pytest.mark.asyncio
async def test_get_item_maintenance_history(
    client: AsyncClient,
    servant_token: str,
    sample_material_item,
    sample_maintenance_history,
):
    """Test récupération de l'historique."""
    response = await client.get(
        f"/api/v1/material/items/{sample_material_item.id}/maintenance",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


# ══════════════════════════════════════════════════════════════════
#  TESTS - RAPPORTS ET STATISTIQUES
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_generate_material_report(
    client: AsyncClient,
    intendant_token: str,
    sample_material_item,
):
    """Test génération d'un rapport."""
    response = await client.post(
        "/api/v1/material/report",
        json={
            "start_date": "2026-01-01T00:00:00",
            "end_date": "2026-12-31T23:59:59",
            "include_maintenance_history": True,
        },
        headers={"Authorization": f"Bearer {intendant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_items" in data
    assert "total_tasks" in data
    assert data["watermark_logo"] == "logo_servant.jpeg"


@pytest.mark.asyncio
async def test_get_material_stats(
    client: AsyncClient,
    servant_token: str,
):
    """Test récupération des statistiques."""
    response = await client.get(
        "/api/v1/material/stats",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_items" in data
    assert "total_tasks" in data
    assert "completion_rate" in data
