#!/usr/bin/env bash
set -euo pipefail

pids=()

cleanup() {
    for pid in "${pids[@]:-}"; do
        if kill -0 "$pid" >/dev/null 2>&1; then
            kill "$pid" >/dev/null 2>&1 || true
        fi
    done
}

trap cleanup EXIT INT TERM

cd /workspace/uis/website
PORT="${WEBSITE_PORT:-3000}" HOSTNAME="0.0.0.0" npm run dev &
pids+=("$!")

cd /workspace/uis/backoffice
PORT="${BACKOFFICE_PORT:-3001}" HOSTNAME="0.0.0.0" npm run dev &
pids+=("$!")

wait -n "${pids[@]}"