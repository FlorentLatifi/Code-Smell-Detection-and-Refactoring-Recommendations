#!/usr/bin/env bash
# Nis imazhin Docker dhe provon që ai punon, jo vetëm që ndërtohet (VD-156).
#
#   bash tools/prova-imazhit.sh <imazhi> [versioni-i-pritur]
#
# Ndërtimi i suksesshëm nuk provon që serveri niset, që modelet ngarkohen apo që
# javac-u gjendet brenda imazhit: v1.0.0 u provua me dorë pikërisht për këtë. Këtu
# kontrollohet që çdo pjesë përgjigjet, jo numrat e saktë: ata u përkasin testeve
# të njësive, me vlera të nxjerra me dorë.
#
# Me versionin e dytë (p.sh. `v1.0.1`), `/api/health` duhet ta raportojë atë. Pa
# këtë kontroll, v1.0.0 doli duke thënë "0.1.0".
set -euo pipefail

image="$1"
expected="${2:-}"
expected="${expected#v}"
python="${PYTHON:-python3}"

# `pwd -W` jep shtegun e Windows-it te Git Bash, që Docker Desktop e kupton;
# në Linux nuk ekziston dhe përdoret `pwd`.
fixtures="$(cd "$(dirname "$0")/../backend/tests/fixtures" && (pwd -W 2>/dev/null || pwd))"
name="javasmell-prova-$$"
base="http://127.0.0.1:8000"
work="$(mktemp -d)"

cleanup() {
    docker rm -f "$name" >/dev/null 2>&1 || true
    rm -rf "$work"
}
trap cleanup EXIT

fail() {
    echo "DËSHTOI: $*" >&2
    docker logs "$name" >&2 || true
    exit 1
}

# Shprehja vlerësohet mbi përgjigjen JSON si `d`. Vjen vetëm nga ky skedar.
check() {
    local file="$1" expression="$2" message="$3"
    "$python" -c 'import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
sys.exit(0 if eval(sys.argv[2]) else 1)' "$file" "$expression" || fail "$message"
    echo "ok: $message"
}

status_of() {
    curl -s -o /dev/null -w "%{http_code}" "$@"
}

# `:ro`: prova analizon dhe ndërton patch-in, por nuk shkruan asgjë.
docker run -d --name "$name" -p 127.0.0.1:8000:8000 \
    -v "$fixtures:/projekte/fixtures:ro" "$image" >/dev/null

for _ in $(seq 60); do
    curl -fsS "$base/api/health" -o "$work/health.json" 2>/dev/null && break
    sleep 1
done
[ -s "$work/health.json" ] || fail "serveri nuk u përgjigj brenda 60 sekondash"

check "$work/health.json" 'd["status"] == "ok"' "/api/health raporton ok"
if [ -n "$expected" ]; then
    check "$work/health.json" "d['version'] == '$expected'" "/api/health raporton versionin $expected"
fi

# Atribuimi i MLCQ-së është detyrim i licencës CC BY 4.0, jo zbukurim (VD-157).
docker exec "$name" test -s NOTICE || fail "NOTICE mungon në imazh"
docker exec "$name" test -s LICENSE || fail "LICENSE mungon në imazh"
echo "ok: LICENSE dhe NOTICE janë në imazh"

[ "$(status_of "$base/")" = 200 ] || fail "faqja nuk u hap"
echo "ok: faqja hapet"

curl -fsS -X POST "$base/api/analyze" -H "Content-Type: application/json" \
    -d '{"path": "/projekte/fixtures", "include_model": true}' -o "$work/analyze.json" \
    || fail "/api/analyze ktheu gabim"
check "$work/analyze.json" 'd["summary"]["unparsed"] == 0' "çdo skedar u parsua"
check "$work/analyze.json" 'd["summary"]["smells"] > 0' "analiza gjen erëra"
check "$work/analyze.json" 'd["model"]["available"]' "modelet e Qasjes B ngarkohen"

curl -fsS -X POST "$base/api/refactor/patch" -H "Content-Type: application/json" \
    -d '{"path": "/projekte/fixtures"}' -o "$work/patch.json" \
    || fail "/api/refactor/patch ktheu gabim"
check "$work/patch.json" 'd["verified_with_javac"]' "javac-u gjendet dhe verifikon"
check "$work/patch.json" 'len(d["applied"]) > 0' "të paktën një rishkrim aplikohet"

# Roja e VD-127, e provuar në imazh si te VD-142.
[ "$(status_of -H "Host: evil.com" "$base/api/health")" = 403 ] \
    || fail "një Host i huaj nuk u refuzua"
echo "ok: Host i huaj refuzohet"
[ "$(status_of -X POST -H "Origin: http://evil.com" -H "Content-Type: application/json" \
    -d '{"path": "/projekte/fixtures"}' "$base/api/analyze")" = 403 ] \
    || fail "një POST nga faqe e huaj nuk u refuzua"
echo "ok: POST nga faqe e huaj refuzohet"
[ "$(status_of -X POST -H "Content-Type: application/json" -d '{"path": "/etc"}' \
    "$base/api/analyze")" = 400 ] || fail "një shteg jashtë rrënjës nuk u refuzua"
echo "ok: shtegu jashtë rrënjës refuzohet"

echo "Imazhi $image kaloi provën."
