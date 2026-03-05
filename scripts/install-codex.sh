#!/usr/bin/env bash
set -euo pipefail

red() { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    red "Missing required command: $cmd"
    exit 1
  fi
}

if command -v codex >/dev/null 2>&1; then
  green "Codex CLI already installed: $(codex --version 2>/dev/null || echo codex)"
  exit 0
fi

require_cmd npm

yellow "Installing Codex CLI with npm..."
npm install -g @openai/codex

if ! command -v codex >/dev/null 2>&1; then
  red "Codex CLI installation did not expose 'codex' in PATH."
  yellow "If npm global bin is not in PATH, re-open shell and try again."
  exit 1
fi

green "Codex CLI installed successfully."
yellow "Next step: authenticate with 'codex login' (or 'codex login --device-auth')."
