# Omarchy Monitors

[Español](README.es.md)

A visual display manager for Hyprland and Omarchy. This is an independent community project and is not affiliated with Omarchy.

Drag monitors to arrange your desktop, identify physical displays, and adjust resolution, refresh rate, and scaling. Edges snap together, and the app warns about overlapping or disconnected layouts. The interface is available in English and Spanish; use the pixel-art flags in the header to switch languages. English is the default.

On short windows, the display map and settings panel scroll independently so their controls remain accessible.

While the app is open, **Show display names** displays a stable number, connector, and model in the bottom-right corner of each enabled screen. The labels are click-through, can be disabled using the switch, and disappear when the last app window closes. The number is remembered when an output is disconnected and reconnected. Selecting a display highlights its physical label using the current theme's accent color.

Changes are applied with a confirmation timer. Unless you confirm within 25 seconds, an independent process restores the previous configuration, even if the window closes. If another application has changed the files in the meantime, it avoids overwriting those changes and keeps recovery data in `~/.local/state/pantallas/`.

## Installation

Requires Linux with **Hyprland**, Omarchy's Lua monitor configuration, Python 3.11 or later, PyGObject, GTK 3, Pycairo, gtk-layer-shell, and fontconfig. On Arch Linux / Omarchy the corresponding packages are `python`, `python-gobject`, `python-cairo`, `gtk3`, `gtk-layer-shell`, and `fontconfig`.

On Arch Linux and compatible distributions, download the `.pkg.tar.zst` package from the [latest release](https://github.com/weedoozas/omarchy-monitors/releases/latest) and install it with `sudo pacman -U ./omarchy-monitors-*.pkg.tar.zst`.

The Arch build recipe is available in [`packaging/arch/PKGBUILD`](packaging/arch/PKGBUILD); build it with `makepkg` from that directory.

Alternatively, install for the current user from source:

```sh
git clone https://github.com/weedoozas/omarchy-monitors.git
cd omarchy-monitors
./install.sh
```

Search for **Omarchy Monitors** in your launcher or run `~/.local/bin/omarchy-monitors`. Installation is per-user and does not require administrator privileges. The installer puts Pixelify Sans in the user's font directory.

## Configuration and limitations

The app edits explicit `hl.monitor` rules in `~/.config/hypr/monitors.lua`, preserving the rest of the file and Omarchy's general rule. It rejects complex rules that it cannot interpret safely and refuses to apply changes if the file or the connected displays have changed since the last reload. Changes are applied and verified using `hyprctl`.

Mirrored layouts and legacy `monitors.conf` configurations cannot currently be edited. If individual Lua rules use custom expressions, edit those rules manually. Visual identification requires gtk-layer-shell and a unique correspondence between GTK and Hyprland monitors. Available modes depend on what each display reports.

## Development

```sh
python3 -m unittest discover -s tests -v
python3 -m pantallas
```

Code is licensed under the [MIT License](LICENSE). [Pixelify Sans](https://github.com/google/fonts/tree/main/ofl/pixelifysans) is distributed under its own [SIL Open Font License](data/fonts/OFL.txt). The project logo was created using image generation.
