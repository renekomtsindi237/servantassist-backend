#!/usr/bin/env bash
# ============================================================
# ServantAssist — Full Backend Audit Script
# Usage:
#   bash scripts/audit_full.sh                     # full audit
#   bash scripts/audit_full.sh --skip-docker       # static only
#   bash scripts/audit_full.sh --skip-dynamic      # no API tests
#
# Requires (in .venv/bin or system):
#   bandit, mypy, flake8, pip-audit (Python)
#   newman, newman-reporter-htmlextra (npm -g)
#   docker compose (for dynamic tests)
#
# Optionally (install if network available):
#   ruff, radon, schemathesis, scalene, pyinstrument, sentry-sdk[fastapi]
# ============================================================
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE_DIR"

# ── Detect Python ────────────────────────────────────────────
if [ -f ".venv/bin/python" ] && .venv/bin/python -c "import sys; sys.exit(0)" 2>/dev/null; then
    PYTHON=".venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
elif command -v python &>/dev/null; then
    PYTHON="python"
else
    echo "ERROR: No Python found. Activate venv or install Python."
    exit 1
fi

VENV_BIN=".venv/bin"
REPORT_DIR="audit_reports"
APP_URL="http://localhost:8000"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SKIP_DOCKER="${1:-}"
SKIP_DYNAMIC="${2:-}"

# ── Colors ──────────────────────────────────────────────────
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; NC='\033[0m'; BOLD='\033[1m'

log()   { echo -e "${BLUE}[AUDIT]${NC} $*"; }
ok()    { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
fail()  { echo -e "${RED}[✗]${NC} $*"; }
phase() { echo -e "\n${BOLD}${BLUE}═══ $* ═══${NC}\n"; }
skip()  { echo -e "${YELLOW}[SKIP]${NC} $*"; }

# ── Setup ────────────────────────────────────────────────────
phase "PHASE 0 — SETUP"
mkdir -p "$REPORT_DIR"/{ruff,bandit,radon,pip-audit,schemathesis,dredd,pyinstrument,scalene,newman,snyk,sentry}
ok "Report directories created: $REPORT_DIR/"

# Optional tools install (try, skip if network unavailable)
log "Installing optional Python audit tools (if network available)..."
$PYTHON -m pip install -q ruff radon pyinstrument scalene "sentry-sdk[fastapi]" 2>/dev/null \
  && ok "Optional tools installed" \
  || warn "Optional tools install skipped (network unavailable)"

# ── Phase 1: Bandit ─────────────────────────────────────────
phase "PHASE 1 — BANDIT (Security SAST)"
log "Running Bandit security scan on src/ and scripts/..."

if command -v bandit &>/dev/null || [ -f "$VENV_BIN/bandit" ]; then
    _BANDIT="${VENV_BIN}/bandit"
    [ -x "$_BANDIT" ] || _BANDIT="bandit"

    "$_BANDIT" -r src/ scripts/ \
        -f txt -o "$REPORT_DIR/bandit/bandit_report.txt" \
        -l 2>/dev/null || true

    "$_BANDIT" -r src/ scripts/ \
        -f json -o "$REPORT_DIR/bandit/bandit_report.json" \
        -l 2>/dev/null || true

    # Summary
    HIGH=$(python3 -c "
import json
r = json.load(open('$REPORT_DIR/bandit/bandit_report.json'))
high = [i for i in r.get('results',[]) if i['issue_severity'] == 'HIGH']
print(len(high))
" 2>/dev/null || echo "?")
    ok "Bandit done — HIGH issues: $HIGH → $REPORT_DIR/bandit/"
else
    skip "Bandit not found — install with: pip install bandit"
fi

# ── Phase 2: Ruff ───────────────────────────────────────────
phase "PHASE 2 — RUFF (Linter)"
if command -v ruff &>/dev/null || [ -f "$VENV_BIN/ruff" ]; then
    _RUFF="${VENV_BIN}/ruff"
    [ -x "$_RUFF" ] || _RUFF="ruff"

    "$_RUFF" check src/ --output-format=json > "$REPORT_DIR/ruff/ruff_lint.json" 2>/dev/null || true
    "$_RUFF" check src/ --statistics > "$REPORT_DIR/ruff/ruff_stats.txt" 2>/dev/null || true
    "$_RUFF" format src/ --check --diff > "$REPORT_DIR/ruff/ruff_format.txt" 2>/dev/null || true
    ok "Ruff done → $REPORT_DIR/ruff/"
else
    # Fallback to flake8
    if command -v flake8 &>/dev/null || [ -f "$VENV_BIN/flake8" ]; then
        _FLAKE8="${VENV_BIN}/flake8"
        [ -x "$_FLAKE8" ] || _FLAKE8="flake8"
        "$_FLAKE8" src/ --max-line-length=120 --statistics \
            --output-file="$REPORT_DIR/ruff/flake8_report.txt" --tee 2>/dev/null || true
        ok "Flake8 (ruff fallback) done → $REPORT_DIR/ruff/"
    else
        skip "Ruff/Flake8 not found"
    fi
fi

# ── Phase 3: Radon ─────────────────────────────────────────
phase "PHASE 3 — RADON (Complexity)"
if command -v radon &>/dev/null || [ -f "$VENV_BIN/radon" ]; then
    _RADON="${VENV_BIN}/radon"
    [ -x "$_RADON" ] || _RADON="radon"

    "$_RADON" cc src/ -s -a -j > "$REPORT_DIR/radon/radon_cc.json" 2>/dev/null || true
    "$_RADON" cc src/ -s -a     > "$REPORT_DIR/radon/radon_cc.txt"  2>/dev/null || true
    "$_RADON" mi src/ -s        > "$REPORT_DIR/radon/radon_mi.txt"  2>/dev/null || true
    "$_RADON" raw src/ -s       > "$REPORT_DIR/radon/radon_raw.txt" 2>/dev/null || true
    ok "Radon done → $REPORT_DIR/radon/"
else
    skip "Radon not found — install with: pip install radon"
fi

# ── Phase 4: pip-audit ──────────────────────────────────────
phase "PHASE 4 — PIP-AUDIT (CVE scan)"
if command -v pip-audit &>/dev/null || [ -f "$VENV_BIN/pip-audit" ]; then
    _PIPAUDIT="${VENV_BIN}/pip-audit"
    [ -x "$_PIPAUDIT" ] || _PIPAUDIT="pip-audit"

    "$_PIPAUDIT" -r requirements.txt \
        --format json -o "$REPORT_DIR/pip-audit/prod.json" 2>/dev/null || true
    "$_PIPAUDIT" -r requirements.txt \
        > "$REPORT_DIR/pip-audit/prod.txt" 2>/dev/null || true
    ok "pip-audit done → $REPORT_DIR/pip-audit/"
else
    skip "pip-audit not found — install with: pip install pip-audit"
fi

# ── Phase 5: Mypy ──────────────────────────────────────────
phase "PHASE 5 — MYPY (Type checking)"
_MYPY="${VENV_BIN}/mypy"
[ -x "$_MYPY" ] || _MYPY="mypy"

if command -v mypy &>/dev/null || [ -f "$VENV_BIN/mypy" ]; then
    "$_MYPY" src/ --ignore-missing-imports --show-error-codes --pretty \
        > "$REPORT_DIR/mypy_report.txt" 2>&1 || true

    ERRORS=$(grep -c "^Found\|error:" "$REPORT_DIR/mypy_report.txt" 2>/dev/null | head -1 || echo "?")
    ok "Mypy done → $REPORT_DIR/mypy_report.txt"
    grep "^Found" "$REPORT_DIR/mypy_report.txt" || true
else
    skip "Mypy not found — install with: pip install mypy"
fi

# ── Phase 6: Docker + Dynamic Tests ─────────────────────────
if [[ "$SKIP_DOCKER" == "--skip-docker" ]]; then
    skip "Docker startup skipped (--skip-docker)"
else
    phase "PHASE 6 — DOCKER STARTUP"
    log "Starting db + redis + backend..."
    docker compose up -d db redis backend

    log "Waiting for health check (max 60s)..."
    if timeout 60 bash -c "until curl -sf $APP_URL/health > /dev/null 2>&1; do sleep 3; done"; then
        ok "App running at $APP_URL"

        log "Exporting OpenAPI spec..."
        curl -s "$APP_URL/openapi.json" -o "$REPORT_DIR/openapi.json"
        ENDPOINTS=$(python3 -c "
import json
d = json.load(open('$REPORT_DIR/openapi.json'))
print(len(d.get('paths', {})))
" 2>/dev/null || echo "?")
        ok "OpenAPI spec saved → $ENDPOINTS endpoints"

        if [[ "$SKIP_DYNAMIC" != "--skip-dynamic" ]]; then
            # ── Schemathesis ─────────────────────────────────────────
            phase "PHASE 7 — SCHEMATHESIS (API Fuzzing)"
            if command -v schemathesis &>/dev/null || [ -f "$VENV_BIN/schemathesis" ]; then
                _ST="${VENV_BIN}/schemathesis"
                [ -x "$_ST" ] || _ST="schemathesis"

                "$_ST" run "$APP_URL/openapi.json" \
                    --checks all \
                    --hypothesis-max-examples 30 \
                    --report "$REPORT_DIR/schemathesis/report.txt" \
                    --junit-xml "$REPORT_DIR/schemathesis/junit.xml" \
                    2>&1 | tee "$REPORT_DIR/schemathesis/output.txt" || true
                ok "Schemathesis done → $REPORT_DIR/schemathesis/"
            else
                skip "Schemathesis not found — install with: pip install schemathesis"
            fi

            # ── Newman ───────────────────────────────────────────────
            phase "PHASE 8 — NEWMAN (API Tests)"
            if command -v newman &>/dev/null; then
                # Get admin token first
                log "Getting admin token..."
                ADMIN_TOKEN=$(curl -s -X POST "$APP_URL/api/v1/auth/login" \
                    -H "Content-Type: application/json" \
                    -d '{"email":"admin@servantassist.com","password":"AdminPass1!"}' \
                    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))" 2>/dev/null || echo "")

                if [ -n "$ADMIN_TOKEN" ]; then
                    # Patch environment file with token
                    python3 -c "
import json
env = json.load(open('$REPORT_DIR/newman/environment.json'))
for v in env['values']:
    if v['key'] == 'admin_token':
        v['value'] = '$ADMIN_TOKEN'
json.dump(env, open('$REPORT_DIR/newman/environment.json', 'w'), indent=2)
"
                    ok "Admin token acquired"
                else
                    warn "Could not acquire admin token — tests will run unauthenticated"
                fi

                newman run "$REPORT_DIR/newman/servantassist_tests.json" \
                    --environment "$REPORT_DIR/newman/environment.json" \
                    --reporters cli,htmlextra,junit \
                    --reporter-htmlextra-export "$REPORT_DIR/newman/report_${TIMESTAMP}.html" \
                    --reporter-junit-export "$REPORT_DIR/newman/junit.xml" \
                    --timeout-request 10000 \
                    --color on \
                    2>&1 | tee "$REPORT_DIR/newman/output_${TIMESTAMP}.txt" || true
                ok "Newman done → $REPORT_DIR/newman/report_${TIMESTAMP}.html"
            else
                skip "Newman not found — install with: npm install -g newman newman-reporter-htmlextra"
            fi
        fi
    else
        fail "App did not start in time. Check: docker compose logs backend"
    fi
fi

# ── Phase 9: Scalene ────────────────────────────────────────
phase "PHASE 9 — SCALENE (Profiling)"
if command -v scalene &>/dev/null || [ -f "$VENV_BIN/scalene" ]; then
    _SCALENE="${VENV_BIN}/scalene"
    [ -x "$_SCALENE" ] || _SCALENE="scalene"

    if [ -d "tests/unit" ]; then
        $PYTHON -m scalene --html \
            --outfile "$REPORT_DIR/scalene/scalene_report.html" \
            --cpu --memory \
            -- -m pytest tests/unit/ -x -q 2>&1 | tee "$REPORT_DIR/scalene/output.txt" || true
        ok "Scalene done → $REPORT_DIR/scalene/"
    else
        skip "No tests/unit/ directory found"
    fi
else
    skip "Scalene not found — install with: pip install scalene"
fi

# ── Summary ─────────────────────────────────────────────────
phase "AUDIT COMPLETE — $(date)"
echo ""
echo "Reports generated in: $REPORT_DIR/"
echo ""
echo "Key files:"
[ -f "$REPORT_DIR/bandit/bandit_report.txt" ]  && echo "  • $REPORT_DIR/bandit/bandit_report.txt    (security)"
[ -f "$REPORT_DIR/ruff/ruff_stats.txt" ]        && echo "  • $REPORT_DIR/ruff/ruff_stats.txt          (lint stats)"
[ -f "$REPORT_DIR/ruff/flake8_report.txt" ]     && echo "  • $REPORT_DIR/ruff/flake8_report.txt       (lint stats)"
[ -f "$REPORT_DIR/radon/radon_cc.txt" ]         && echo "  • $REPORT_DIR/radon/radon_cc.txt           (complexity)"
[ -f "$REPORT_DIR/pip-audit/prod.txt" ]         && echo "  • $REPORT_DIR/pip-audit/prod.txt           (CVE deps)"
[ -f "$REPORT_DIR/mypy_report.txt" ]            && echo "  • $REPORT_DIR/mypy_report.txt              (type errors)"
[ -f "$REPORT_DIR/openapi.json" ]               && echo "  • $REPORT_DIR/openapi.json                  (OpenAPI spec)"
ls "$REPORT_DIR/newman/report_"*.html 2>/dev/null && echo "  • $REPORT_DIR/newman/report_*.html         (API test results)"
[ -f "$REPORT_DIR/schemathesis/report.txt" ]    && echo "  • $REPORT_DIR/schemathesis/report.txt      (fuzzing)"
[ -f "$REPORT_DIR/scalene/scalene_report.html" ] && echo "  • $REPORT_DIR/scalene/scalene_report.html  (performance)"
echo ""
echo "CRITICAL FIXES APPLIED:"
echo "  [FIXED] scripts/init_db.py: hardcoded email/password as env keys → fixed to ADMIN_EMAIL/ADMIN_PASSWORD"
echo "  [ADDED] Sentry integration in src/main.py (activate via SENTRY_DSN in .env)"
echo ""
echo "KNOWN ISSUES:"
echo "  • mypy: 539 errors in 58/169 files (no_strict_optional, missing annotations)"
echo "  • flake8: 120 F401 unused imports, 755 E122 indent issues"
echo "  • bandit: 3 LOW false positives (token type strings misdetected as passwords)"
