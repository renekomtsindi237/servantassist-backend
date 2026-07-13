@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul

echo.
echo ══════════════════════════════════════════════════════════════
echo   ServantAssist — Démarrage local + Seed + Tests E2E
echo ══════════════════════════════════════════════════════════════
echo.

set COMPOSE_FILE=docker-compose.sim.yml
set BACKEND_URL=http://localhost:8000/health

REM ── 1. Arrêter et nettoyer les conteneurs précédents ──────────────────────
echo [1/6] Nettoyage des conteneurs précédents...
docker compose -f %COMPOSE_FILE% down --remove-orphans 2>nul
echo      ✓ Nettoyage effectué

REM ── 2. Construire et démarrer (backend + db + redis) ─────────────────────
echo.
echo [2/6] Construction et démarrage des services...
echo      (première fois = 2-5 min pour le build Docker)
docker compose -f %COMPOSE_FILE% up -d sa-db backend
if %ERRORLEVEL% NEQ 0 (
    echo ✗ Erreur au démarrage. Vérifiez Docker Desktop.
    exit /b 1
)
echo      ✓ Services démarrés

REM ── 3. Attendre que le backend réponde ────────────────────────────────────
echo.
echo [3/6] Attente du démarrage du backend...
set MAX_WAIT=120
set ELAPSED=0
:wait_loop
    timeout /t 3 /nobreak >nul
    set /a ELAPSED+=3
    curl -s -o nul -w "%%{http_code}" %BACKEND_URL% 2>nul | findstr "200" >nul
    if !ERRORLEVEL! == 0 goto backend_ready
    if !ELAPSED! GEQ !MAX_WAIT! (
        echo ✗ Timeout : le backend ne répond pas après %MAX_WAIT%s
        echo   Logs du backend :
        docker compose -f %COMPOSE_FILE% logs --tail=30 backend
        exit /b 1
    )
    echo      Attente... (%ELAPSED%/%MAX_WAIT%s)
    goto wait_loop

:backend_ready
echo      ✓ Backend opérationnel (%ELAPSED%s)

REM ── 4. Migrations Alembic ─────────────────────────────────────────────────
echo.
echo [4/6] Application des migrations Alembic...
docker compose -f %COMPOSE_FILE% exec -T backend alembic upgrade head
if %ERRORLEVEL% NEQ 0 (
    echo ✗ Erreur lors des migrations.
    docker compose -f %COMPOSE_FILE% logs --tail=20 backend
    exit /b 1
)
echo      ✓ Migrations appliquées

REM ── 5. Initialisation de l'admin ─────────────────────────────────────────
echo.
echo [5/6] Initialisation du compte administrateur...
docker compose -f %COMPOSE_FILE% exec -T backend python scripts/init_db.py
if %ERRORLEVEL% NEQ 0 (
    echo      (compte admin déjà existant — OK)
)
echo      ✓ Admin prêt

REM ── 6. Lancer les tests E2E ───────────────────────────────────────────────
echo.
echo [6/6] Exécution de la suite de tests E2E (seed + assertions)...
echo ══════════════════════════════════════════════════════════════
python -X utf8 tests/seed_and_test.py
set TEST_EXIT=%ERRORLEVEL%

echo.
echo ══════════════════════════════════════════════════════════════
if %TEST_EXIT% == 0 (
    echo   ✅  Tous les tests passent — backend opérationnel
) else (
    echo   ⚠️   Des tests ont échoué — voir le rapport ci-dessus
)
echo ══════════════════════════════════════════════════════════════

echo.
echo Résumé des services :
docker compose -f %COMPOSE_FILE% ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

echo.
echo Pour explorer l'API : http://localhost:8000/api/docs
echo Pour arrêter       : docker compose -f docker-compose.dev.yml down
echo.

exit /b %TEST_EXIT%
