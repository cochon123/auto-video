#!/usr/bin/env bash
# auto-video installer — copies skills and helpers to the user's system
# Usage: bash install.sh [--opencode] [--all-agents]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$SCRIPT_DIR"

AGENTS_DIR="$HOME/.agents/skills"
OPENCODE_DIR="$HOME/.config/opencode/skill"
CONFIG_DIR="$HOME/.config/auto-video"
HELPERS_DIR="$CONFIG_DIR/helpers"

INSTALL_OPENCODE=false
INSTALL_ALL=false

for arg in "$@"; do
  case "$arg" in
    --opencode) INSTALL_OPENCODE=true ;;
    --all-agents) INSTALL_ALL=true ;;
  esac
done

echo "=== Auto-Video Installer ==="
echo ""

# Create directories
echo "Creating directories..."
mkdir -p "$AGENTS_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$HELPERS_DIR"
mkdir -p "$CONFIG_DIR/cache"
mkdir -p "$HOME/Videos/auto-video"

# Install skills to ~/.agents/skills/
echo "Installing skills to $AGENTS_DIR ..."
for skill_dir in "$SKILLS_DIR"/auto-video*; do
  if [ -d "$skill_dir" ]; then
    skill_name="$(basename "$skill_dir")"
    echo "  -> $skill_name"
    rm -rf "$AGENTS_DIR/$skill_name"
    cp -r "$skill_dir" "$AGENTS_DIR/$skill_name"
  fi
done

# If --opencode or --all-agents, also install to opencode skill dir
if [ "$INSTALL_OPENCODE" = true ] || [ "$INSTALL_ALL" = true ]; then
  echo "Installing skills to $OPENCODE_DIR ..."
  mkdir -p "$OPENCODE_DIR"
  for skill_dir in "$SKILLS_DIR"/auto-video*; do
    if [ -d "$skill_dir" ]; then
      skill_name="$(basename "$skill_dir")"
      echo "  -> $skill_name"
      rm -rf "$OPENCODE_DIR/$skill_name"
      cp -r "$skill_dir" "$OPENCODE_DIR/$skill_name"
    fi
  done
fi

# Install helpers
echo "Installing helpers to $HELPERS_DIR ..."
for helper in "$SKILLS_DIR"/shared/helpers/*; do
  if [ -f "$helper" ]; then
    echo "  -> $(basename "$helper")"
    cp "$helper" "$HELPERS_DIR/"
    chmod +x "$HELPERS_DIR/$(basename "$helper")"
  fi
done

# Install default config if not present
if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
  echo "Installing default config to $CONFIG_DIR/config.yaml ..."
  cp "$SKILLS_DIR/shared/templates/config.yaml.example" "$CONFIG_DIR/config.yaml"
  chmod 600 "$CONFIG_DIR/config.yaml"
  echo ""
  echo "  IMPORTANT: Edit $CONFIG_DIR/config.yaml to add your API keys."
  echo "  Or run: 'setup auto-video' in your AI agent to configure interactively."
fi

echo ""
echo "=== Installation complete ==="
echo ""
echo "Skills installed:"
echo "  - auto-video          (main pipeline: research, script, scenario, assembly)"
echo "  - auto-video-setup    (interactive setup)"
echo "  - auto-video-youtube  (YouTube upload)"
echo ""
echo "Helpers installed to: $HELPERS_DIR"
echo "Config: $CONFIG_DIR/config.yaml"
echo ""
echo "Next steps:"
echo "  1. Open your AI agent (opencode, claude code, etc.)"
echo "  2. Say: 'setup auto-video'"
echo "  3. The agent will guide you through configuration"
