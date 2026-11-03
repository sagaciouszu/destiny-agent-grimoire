#!/bin/bash
# Drifter Master Audit - thin wrapper over the shared agent-audit runner.
# Usage: ./drifter-master-audit.sh
exec bash "$(dirname "$0")/tests/agent-audit.sh" drifter
