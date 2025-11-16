#!/bin/bash
# Batch Processing Script - Production Pattern
# Parallel refactoring across multiple repositories

set -e

REPOS=(
  "/path/to/repo1"
  "/path/to/repo2"
  "/path/to/repo3"
)

# Configuration
MAX_PARALLEL=3
LOG_DIR="./logs/batch-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$LOG_DIR"

echo "================================================================"
echo "Claude Code Batch Processing"
echo "================================================================"
echo "Repositories: ${#REPOS[@]}"
echo "Max parallel: $MAX_PARALLEL"
echo "Log directory: $LOG_DIR"
echo ""

# Function to process single repo
process_repo() {
    local repo_path="$1"
    local repo_name=$(basename "$repo_path")
    local log_file="$LOG_DIR/$repo_name.log"

    echo "[$(date +%H:%M:%S)] Processing: $repo_name"

    (
        cd "$repo_path" || exit 1

        # Execute Claude Code CLI
        python3 -m src.cli \
            --message "Refactor authentication to use OAuth2" \
            > "$log_file" 2>&1

        if [ $? -eq 0 ]; then
            echo "[$(date +%H:%M:%S)] ✅ $repo_name: SUCCESS"
        else
            echo "[$(date +%H:%M:%S)] ❌ $repo_name: FAILED (see $log_file)"
        fi
    ) &
}

# Process repos in parallel (max MAX_PARALLEL at a time)
active_jobs=0
for repo in "${REPOS[@]}"; do
    # Wait if at max parallelism
    while [ $active_jobs -ge $MAX_PARALLEL ]; do
        wait -n
        ((active_jobs--))
    done

    process_repo "$repo"
    ((active_jobs++))
done

# Wait for all remaining jobs
wait

echo ""
echo "================================================================"
echo "Batch processing complete"
echo "Logs: $LOG_DIR"
echo "================================================================"
