#!/usr/bin/env bash
# Copia .claude/skills (fuente, Claude Code) a .agents/skills (Codex y otros agentes).
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf .agents/skills
cp -r .claude/skills .agents/skills
echo "Skills sincronizadas: .claude/skills -> .agents/skills"
