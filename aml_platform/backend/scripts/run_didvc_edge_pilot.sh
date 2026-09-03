#!/usr/bin/env bash
# run_didvc_edge_pilot.sh (AWI TASK-032 / TASK-059)
# Boots the didvc Credential Edge pilot container with per-boot random API
# keys (never committed — generated here, kept only in a 0600 env file that
# doubles as the docker --env-file), and runs the E2E tests with --test.
#
#   ./run_didvc_edge_pilot.sh            # boot only
#   ./run_didvc_edge_pilot.sh --test     # boot + pytest tests/e2e
#   ./run_didvc_edge_pilot.sh --stop     # tear the pilot down
#
# Prereq: mvn -f didvc/pom.xml -DskipTests package  (jar must exist)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
IMAGE="didvc-edge:dev"
CONTAINER="didvc-edge-pilot"
PORT="${DIDVC_EDGE_PORT:-8090}"
ENV_FILE="${DIDVC_PILOT_ENV_FILE:-/tmp/didvc_pilot.env}"

if [ "${1:-}" = "--stop" ]; then
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    rm -f "$ENV_FILE"
    echo "pilot stopped"
    exit 0
fi

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    echo "[pilot] building $IMAGE (requires the packaged jar)..."
    docker build -q -f "$REPO_ROOT/didvc/docker/Dockerfile.edge" -t "$IMAGE" "$REPO_ROOT"
fi

# Runtime-only environment: per-boot random keys (openssl), base URL and the
# demo profile. The file is 0600, lives outside the repo, and is both the
# docker --env-file and the sourceable test environment.
umask 077
{
    printf 'SPRING_PROFILES_ACTIVE=%s\n' demo
    printf 'DIDVC_EDGE_ISSUER_BASE_URL=%s\n' "http://localhost:${PORT}"
    printf 'DIDVC_EDGE_URL=%s\n' "http://127.0.0.1:${PORT}"
    printf 'DIDVC_EDGE_INTERNAL_API_KEY=%s\n' "pilot-internal-$(openssl rand -hex 12)"
    printf 'DIDVC_EDGE_M2M_API_KEYS=%s\n' "pilot-m2m-$(openssl rand -hex 12)"
} > "$ENV_FILE"

docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
docker run -d --name "$CONTAINER" -p "127.0.0.1:${PORT}:8080" \
    --env-file "$ENV_FILE" \
    "$IMAGE" >/dev/null

echo "[pilot] waiting for the edge to become healthy..."
for _ in $(seq 1 40); do
    if curl -sf "http://127.0.0.1:${PORT}/demo/issuer-kid" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done
curl -sf "http://127.0.0.1:${PORT}/demo/issuer-kid" >/dev/null || { echo "[pilot] FAILED to start"; exit 1; }

echo "[pilot] didvc-edge is up at http://127.0.0.1:${PORT} (container: $CONTAINER)"
echo "[pilot] runtime credentials in $ENV_FILE (0600)"

if [ "${1:-}" = "--test" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$ENV_FILE"
    set +a
    cd "$REPO_ROOT/aml_platform/backend"
    exec "${PYTHON:-python3}" -m pytest tests/e2e -v
else
    cat <<EOF

Run the E2E suite with:
  $0 --test
(Tear down with: $0 --stop)
EOF
fi
