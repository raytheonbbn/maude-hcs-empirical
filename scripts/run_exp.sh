#!/bin/bash
set -euo pipefail

# --- Parameter Parsing & Validation ---
if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <loop_count> <yaml_config_path>"
  echo "Example: $0 5 /src/cp4/mastodon_only_debug.yaml"
  exit 1
fi

LOOP_COUNT="$1"
CONFIG_YAML="$2"


# Validate loop count is a positive integer
if ! [[ "$LOOP_COUNT" =~ ^[0-9]+$ ]] || [ "$LOOP_COUNT" -le 0 ]; then
  echo "Error: loop_count must be a positive integer."
  exit 1
fi

# --- Main Execution Loop ---
for ((i = 1; i <= LOOP_COUNT; i++)); do
  echo "=========================================="
  echo "Starting Iteration $i of $LOOP_COUNT: $(date)"
  echo "=========================================="

  # 1. Start the controller environment/container
  echo "[Host] Starting controller container..."
  docker compose build
  docker compose --project-name ${USER} up -d

  # 2. Run test sequence inside the container non-interactively
  CONTAINER_NAME="${USER}_controller_cp3"
  echo "[Host] Executing workloads inside '$CONTAINER_NAME'..."
  docker exec ${CONTAINER_NAME}  bash -c "
    set -e
    echo \"[Container] Starting run: \$(date)\"
    ./start_default.sh -c '/$CONFIG_YAML'
    echo \"[Container] Finished start_default: \$(date)\"
    ./stop_default.sh -c '/$CONFIG_YAML'
    echo \"[Container] Finished stop_default: \$(date)\"
  "

  # 3. Stop controller
  echo "[Host] Stopping controller..."
  docker compose --project-name ${USER} down

  # 4. Host cleanup
  echo "[Host] Cleaning up leftover containers and networks..."
  RUNNING_CONTAINERS=$(docker ps -q)
  if [ -n "$RUNNING_CONTAINERS" ]; then
    docker stop "$RUNNING_CONTAINERS"
  fi
  docker network prune -f

  echo "Completed Iteration $i: $(date)"
  echo ""
done

echo "All $LOOP_COUNT iterations completed successfully."
