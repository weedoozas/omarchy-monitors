#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -c 'import gi; gi.require_version("Gtk", "3.0"); gi.require_version("GtkLayerShell", "0.1"); from gi.repository import Gtk, GtkLayerShell' || {
  echo 'Faltan dependencias: Python, PyGObject, GTK 3 y gtk-layer-shell.' >&2; exit 1;
}
command -v hyprctl >/dev/null || { echo 'No se encontró hyprctl (Hyprland).' >&2; exit 1; }
target="${XDG_DATA_HOME:-$HOME/.local/share}/omarchy-monitors"
mkdir -p "$target/pantallas" "$target/data/fonts" "$HOME/.local/bin" "${XDG_DATA_HOME:-$HOME/.local/share}/applications" "${XDG_DATA_HOME:-$HOME/.local/share}/fonts/omarchy-monitors"
cp pantallas/*.py "$target/pantallas/"
cp data/omarchy-monitors.png "$target/data/"
cp data/fonts/PixelifySans.ttf data/fonts/OFL.txt "$target/data/fonts/"
cp data/fonts/PixelifySans.ttf "${XDG_DATA_HOME:-$HOME/.local/share}/fonts/omarchy-monitors/"
cat > "$HOME/.local/bin/omarchy-monitors" <<'LAUNCHER'
#!/usr/bin/env bash
set -euo pipefail
app_dir="${XDG_DATA_HOME:-$HOME/.local/share}/omarchy-monitors"
export PYTHONPATH="$app_dir${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m pantallas "$@"
LAUNCHER
chmod +x "$HOME/.local/bin/omarchy-monitors"
if command -v fc-cache >/dev/null; then fc-cache -f "${XDG_DATA_HOME:-$HOME/.local/share}/fonts/omarchy-monitors"; fi
python3 - <<'PY'
from pathlib import Path
import os
home = Path.home()
data = Path(os.environ.get('XDG_DATA_HOME', home / '.local/share'))
def quote(value):
    return '"' + str(value).replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$') + '"'
launcher = home/'.local/bin/omarchy-monitors'
icon = data/'omarchy-monitors/data/omarchy-monitors.png'
desktop = data/'applications/omarchy-monitors.desktop'
desktop.write_text('[Desktop Entry]\nType=Application\nName=Omarchy Monitors\nComment=Organiza tus pantallas de Hyprland\nExec='+quote(launcher)+'\nIcon='+str(icon)+'\nTerminal=false\nCategories=Settings;HardwareSettings;\nKeywords=pantallas;monitores;display;screen;hyprland;\nStartupNotify=true\n')
print('Instalado. Busca «Omarchy Monitors» en el lanzador.')
PY
