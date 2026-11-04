"""Etiquetas persistentes de monitores, sin entrada de ratón ni teclado."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
from . import backend

CONFIG_DIR = Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config'))/'omarchy-monitors'
AUTOSTART = Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config'))/'autostart/omarchy-monitors-labels.desktop'
PREFERENCE = CONFIG_DIR/'labels-enabled'
NUMBERS = CONFIG_DIR/'monitor-numbers.json'

def enabled():
    return PREFERENCE.exists() and PREFERENCE.read_text().strip() == '1'

def numbers(displays):
    CONFIG_DIR.mkdir(parents=True,exist_ok=True)
    with (CONFIG_DIR/'numbers.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        try:
            mapping=json.loads(NUMBERS.read_text())
            if not isinstance(mapping,dict): mapping={}
            mapping={k:v for k,v in mapping.items() if isinstance(k,str) and isinstance(v,int) and v>0}
        except (OSError,ValueError): mapping={}
        previous=dict(mapping)
        for d in sorted(displays,key=lambda d:(not d['enabled'],d['y'],d['x'],d['name'])):
            if d['name'] not in mapping: mapping[d['name']]=max(mapping.values(),default=0)+1
        if mapping != previous or not NUMBERS.exists():
            backend.atomic(NUMBERS,json.dumps(mapping,ensure_ascii=False,indent=2)+'\n')
        return mapping

def set_enabled(value, launch=True):
    CONFIG_DIR.mkdir(parents=True,exist_ok=True)
    if value:
        executable=Path.home()/'.local/bin/omarchy-monitors'
        quoted='"'+str(executable).replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$')+'"'
        backend.atomic(AUTOSTART,'[Desktop Entry]\nType=Application\nName=Omarchy Monitors - Nombres\nExec='+quoted+' --labels\nTerminal=false\nNoDisplay=true\n')
        backend.atomic(PREFERENCE,'1\n')
        if launch:
            subprocess.Popen([sys.executable,'-m','pantallas','--labels'],start_new_session=True,
                             stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    else:
        backend.atomic(PREFERENCE,'0\n')
        AUTOSTART.unlink(missing_ok=True)

def run():
    os.environ['GDK_BACKEND']='wayland'
    import gi
    gi.require_version('Gtk','3.0'); gi.require_version('GtkLayerShell','0.1')
    from gi.repository import Gtk,Gdk,GLib,GtkLayerShell
    import cairo
    from .app import theme
    backend.STATE.mkdir(parents=True,exist_ok=True)
    lock=(backend.STATE/'labels.lock').open('a')
    try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: return
    windows={}; last=[None]
    css=Gtk.CssProvider()
    def refresh():
        if not enabled(): Gtk.main_quit(); return False
        try:
            config=backend.CONFIG.read_text()
            ds=backend.snapshot(backend.live_monitors(),backend.read_saved(config))
            nums=numbers(ds); display=Gdk.Display.get_default(); theme_colors=theme()
            candidates=[]
            for d in ds:
                if not d['enabled']: continue
                w,h=backend.size(d); matches=[]
                for i in range(display.get_n_monitors()):
                    mon=display.get_monitor(i); g=mon.get_geometry()
                    if (g.x,g.y,g.width,g.height)==(d['x'],d['y'],w,h): matches.append(mon)
                if len(matches)==1: candidates.append((d,matches[0],nums[d['name']]))
            signature=tuple((d['name'],d['label'],d['x'],d['y'],*backend.size(d),n) for d,m,n in candidates)+(theme_colors['background'],theme_colors['foreground'],theme_colors['accent'])
            if signature==last[0]: return True
            last[0]=signature
            for win in windows.values(): win.destroy()
            windows.clear()
            css.load_from_data(('window {background: transparent;} .monitor-badge {background: '+theme_colors['background']+'; border: 1px solid '+theme_colors['accent']+'; border-radius: 4px; padding: 5px 9px; color: '+theme_colors['foreground']+'; font-family: "Pixelify Sans", monospace; font-size: 14px;}').encode())
            Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),css,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            for d,monitor,n in candidates:
                win=Gtk.Window(); win.set_decorated(False); win.set_app_paintable(True); win.set_accept_focus(False); win.set_focus_on_map(False)
                visual=win.get_screen().get_rgba_visual()
                if visual: win.set_visual(visual)
                GtkLayerShell.init_for_window(win); GtkLayerShell.set_layer(win,GtkLayerShell.Layer.OVERLAY)
                GtkLayerShell.set_keyboard_mode(win,GtkLayerShell.KeyboardMode.NONE)
                GtkLayerShell.set_monitor(win,monitor); GtkLayerShell.set_namespace(win,'omarchy-monitor-label')
                for edge in (GtkLayerShell.Edge.BOTTOM,GtkLayerShell.Edge.RIGHT):
                    GtkLayerShell.set_anchor(win,edge,True); GtkLayerShell.set_margin(win,edge,12)
                title=Gtk.Label(label=f"{n} · {d['name']} · {d['label']}")
                title.get_style_context().add_class('monitor-badge'); win.add(title)
                win.connect('realize', lambda w: w.get_window().input_shape_combine_region(cairo.Region(),0,0))
                win.show_all(); windows[d['name']]=win
        except Exception as exc:
            print('No se pudo actualizar los nombres:',exc,file=sys.stderr,flush=True)
        return True
    refresh(); GLib.timeout_add_seconds(2,refresh); Gtk.main()
