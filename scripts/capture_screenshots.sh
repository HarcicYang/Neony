#!/usr/bin/env bash
# Capture the README/documentation screenshots from the real Gallery.
#
# Run from the repository root under a virtual X display:
#   xvfb-run --auto-servernum --server-args="-screen 0 2200x1400x24" \
#     bash scripts/capture_screenshots.sh
set -euo pipefail

for command in .venv/bin/python xdotool import magick; do
  if [[ "$command" == */* ]]; then
    [[ -x "$command" ]] || {
      echo "Missing executable: $command" >&2
      exit 1
    }
  elif ! command -v "$command" >/dev/null; then
    echo "Missing command: $command" >&2
    exit 1
  fi
done

export GDK_BACKEND=x11
export WAYLAND_DISPLAY=""
export GDK_SCALE=2

output_dir="docs/assets/screenshots"
mkdir -p "$output_dir"

capture() {
  local panel="$1"
  local output="$2"
  local scroll_count="$3"
  local theme="$4"
  local click_x="${5:-}"
  local click_y="${6:-}"

  NEONY_CAPTURE_PANEL="$panel" NEONY_CAPTURE_THEME="$theme" .venv/bin/python - <<'PY' &
import os

from neony.application import Theme
from neony.gallery.assemble import app, page
from neony.gallery.core import theme_mode, theme_picker
from neony.gallery.tree import gallery_tree

theme = Theme.get(os.environ["NEONY_CAPTURE_THEME"])
app.theme = theme
theme_mode.set(theme.mode)
theme_picker.value = theme.mode
gallery_tree.selected_key = os.environ["NEONY_CAPTURE_PANEL"]
app.run(page)
PY
  local app_pid=$!

  cleanup() {
    kill "$app_pid" 2>/dev/null || true
    wait "$app_pid" 2>/dev/null || true
  }
  trap cleanup RETURN

  local window_id=""
  for _ in $(seq 1 40); do
    window_id="$(xdotool search --onlyvisible --name "Neony" 2>/dev/null | tail -n 1 || true)"
    if [[ -n "$window_id" ]]; then
      break
    fi
    sleep 0.25
  done
  if [[ -z "$window_id" ]]; then
    echo "Neony gallery window was not found" >&2
    return 1
  fi

  sleep 4
  if (( scroll_count > 0 )); then
    xdotool mousemove --window "$window_id" 1500 1100
    xdotool click --repeat "$scroll_count" --delay 80 5
    sleep 2
  fi
  if [[ -n "$click_x" && -n "$click_y" ]]; then
    xdotool mousemove --window "$window_id" "$click_x" "$click_y"
    xdotool click 1
    sleep 2
  fi

  import -window "$window_id" +repage "$output"
  magick "$output" -strip -define png:compression-level=9 "$output"
  cleanup
  trap - RETURN
}

capture overlays "$output_dir/gallery-overlays.png" 12 cyberangel-dark 1775 695
capture feedback "$output_dir/gallery-feedback.png" 11 ember-zone-light
capture datatable "$output_dir/gallery-datatable.png" 5 nightglow-dark
capture media "$output_dir/gallery-media.png" 6 planet-plaza-light
