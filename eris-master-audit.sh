#!/bin/bash
# Eris Master Audit - thin wrapper over the shared agent-audit runner.
# Usage: ./eris-master-audit.sh
exec bash "$(dirname "$0")/tests/agent-audit.sh" eris
