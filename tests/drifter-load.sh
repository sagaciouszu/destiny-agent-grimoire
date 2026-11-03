#!/bin/bash
# Drifter Tiered Loading System
# Creates tiered load profiles for agents
# Usage: ./drifter-load.sh [minimal|standard|deep]

TIER="${1:-standard}"
WORKSPACE="${WORKSPACE:-$(bash "$(dirname "$0")/resolve-workspace.sh" "$0")}"
LORE="${ARCHIVE:-$(cd "$(dirname "$0")" && pwd)}"

case "$TIER" in
    minimal)
        echo "=== MINIMAL TIER (~6K) ==="
        echo "Load: drifter-core.md only"
        echo ""
        echo "Files to load:"
        echo "  $WORKSPACE/drifter-core.md"
        echo ""
        echo "Use case: Quick banter, simple questions, casual conversation"
        ;;
    standard)
        echo "=== STANDARD TIER (~12K) ==="
        echo "Load: drifter-core.md + voice-core.md + relationships (condensed)"
        echo ""
        echo "Files to load:"
        echo "  $WORKSPACE/drifter-core.md"
        echo "  $WORKSPACE/voice/drifter-voice-core.md"
        echo "  $WORKSPACE/core/relationships.md (first 100 lines)"
        echo "  $WORKSPACE/core/guardrails.md"
        echo ""
        echo "Use case: Most conversations, moderate lore depth"
        ;;
    deep)
        echo "=== DEEP TIER (~50K) ==="
        echo "Load: All agent files"
        echo ""
        echo "Files to load:"
        echo "  $WORKSPACE/drifter-core.md"
        echo "  $WORKSPACE/drifter-voice.md"
        echo "  $WORKSPACE/voice/drifter-voice-core.md"
        echo "  $WORKSPACE/voice/drifter-voice-gambler.md"
        echo "  $WORKSPACE/voice/drifter-voice-grief.md"
        echo "  $WORKSPACE/voice/drifter-voice-crew.md"
        echo "  $WORKSPACE/voice/drifter-voice-combat.md"
        echo "  $WORKSPACE/voice/drifter-voice-storytelling.md"
        echo "  $WORKSPACE/voice/drifter-voice-vulnerable.md"
        echo "  $WORKSPACE/voice/drifter-voice-business.md"
        echo "  $WORKSPACE/voice/drifter-voice-identity.md"
        echo "  $WORKSPACE/core/relationships.md"
        echo "  $WORKSPACE/core/arcs.md"
        echo "  $WORKSPACE/core/guardrails.md"
        echo "  $WORKSPACE/world/items-gambit.md"
        echo "  $WORKSPACE/world/crew-derelict.md"
        echo "  $WORKSPACE/world/nine.md"
        echo "  $WORKSPACE/world/philosophy.md"
        echo "  $WORKSPACE/core/mood-triggers.md"
        echo "  $WORKSPACE/core/threats-locations.md"
        echo ""
        echo "Use case: Deep lore discussions, complex scenarios, full authenticity"
        ;;
    *)
        echo "Usage: $0 [minimal|standard|deep]"
        echo ""
        echo "Tiers:"
        echo "  minimal  - ~6K, brain only. Quick banter."
        echo "  standard - ~12K, brain + core voice + relationships. Most conversations."
        echo "  deep     - ~50K, all files. Deep lore."
        exit 1
        ;;
esac
