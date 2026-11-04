"""Interfaz gráfica de Pantallas."""
import copy
import json
import math
import os
import time
import tomllib
import uuid
from pathlib import Path
os.environ['GDK_BACKEND'] = 'wayland'
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from . import backend
from . import i18n
from . import labels

CSS = b'''
* { font-family: "Pixelify Sans", monospace; font-size: 17px; }
window { background: #101722; color: #eef3f8; }
.header { background: #141f2c; border-bottom: 1px solid #293b4c; }
.title { font-size: 24px; font-weight: 800; color: #f3f8fc; }
.subtitle, .hint { color: #a8bbc9; font-size: 15px; }
.section { color: #c4d6e2; font-size: 15px; font-weight: 700; }
.card { background: #192635; border: none; border-radius: 14px; }
.card > border { border: none; }
.sidebar { background: #141f2c; border: none; }
button { background: #263949; color: #f3f8fc; border: 1px solid #405667; border-radius: 8px; padding: 8px 13px; text-shadow: none; box-shadow: none; }
button:hover { background: #345063; }
button.suggested-action { background: #43d2b3; color: #0c2526; border: 0; font-weight: bold; }
button.suggested-action:hover { background: #67e4c6; }
button:disabled { opacity: .45; }
button.language { padding: 5px; }
button.language-active { border: 2px solid #43d2b3; }
combobox button { min-height: 26px; }
.warning { color: #f6c779; }
list, row { background: #192635; color: #eef3f8; }
row:selected { background: #285a59; color: #ffffff; }
row label { color: #eef3f8; }
row label.hint { color: #a8bbc9; }
switch:checked { background: #43d2b3; }
'''

def theme():
    defaults = {'background':'#101722','dark_background':'#141f2c','selection':'#263949',
                'accent':'#43d2b3','foreground':'#eef3f8','bright_foreground':'#a8bbc9'}
    path=Path.home()/'.local/state/omarchy/current/theme/colors.toml'
    try:
        values=tomllib.loads(path.read_text())
        for key in defaults:
            value=values.get(key)
            if isinstance(value,str) and len(value)==7 and value.startswith('#'):
                int(value[1:],16); defaults[key]=value
    except (OSError,ValueError,tomllib.TOMLDecodeError): pass
    return defaults

def themed_css(palette):
    css=CSS.decode()
    replacements={'#101722':palette['background'], '#141f2c':palette['dark_background'],
                  '#192635':palette['dark_background'], '#263949':palette['selection'],
                  '#285a59':palette['selection'], '#304355':palette['accent'],
                  '#293b4c':palette['selection'], '#405667':palette['accent'],
                  '#43d2b3':palette['accent'], '#67e4c6':palette['accent'],
                  '#eef3f8':palette['foreground'], '#f3f8fc':palette['foreground'],
                  '#c4d6e2':palette['foreground'], '#a8bbc9':palette['bright_foreground']}
    for old,new in replacements.items(): css=css.replace(old,new)
    return css.encode()

def rgb(value):
    return tuple(int(value[i:i+2],16)/255 for i in (1,3,5))

def label(text, css=None, xalign=0):
    w = Gtk.Label(label=text, xalign=xalign)
    if css: w.get_style_context().add_class(css)
    w.set_line_wrap(True)
    return w

def button(text, callback, primary=False):
    w = Gtk.Button(label=text)
    if primary: w.get_style_context().add_class('suggested-action')
    w.connect('clicked', callback)
    return w

def draw_flag(widget, cr, language):
    """Dibuja una bandera pequeña mediante una cuadrícula de píxeles."""
    columns,rows=15,10
    width=widget.get_allocated_width()/columns; height=widget.get_allocated_height()/rows
    for y in range(rows):
        for x in range(columns):
            if language == 'es':
                color = '#aa151b' if y < 3 or y >= 7 else '#f1bf00'
                if x in (4,5) and y in (4,5): color='#aa151b'
            else:
                color='#012169'
                diagonal=abs(abs((x-7)/7)-abs((y-4.5)/4.5))
                if diagonal < .30: color='#ffffff'
                if diagonal < .13: color='#c8102e'
                if x in (6,7,8) or y in (3,4,5,6): color='#ffffff'
                if x == 7 or y in (4,5): color='#c8102e'
            cr.set_source_rgb(*rgb(color)); cr.rectangle(x*width,y*height,width+0.1,height+0.1); cr.fill()
    return False

class Canvas(Gtk.DrawingArea):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK | Gdk.EventMask.POINTER_MOTION_MASK)
        self.connect('draw', self.draw)
        self.connect('button-press-event', self.press)
        self.connect('button-release-event', self.release)
        self.connect('motion-notify-event', self.motion)
        self.drag = None
        self.geometry = {}
        self.factor = 1
        self.set_size_request(450, 320)

    def draw(self, widget, cr):
        allocation = self.get_allocation(); width, height = allocation.width, allocation.height
        colors=theme()
        cr.set_source_rgb(*rgb(colors['background'])); cr.paint()
        active = [d for d in self.app.displays if d['enabled']]
        if not active: return
        bounds = [(d['x'],d['y'],*backend.size(d)) for d in active]
        x0 = min(b[0] for b in bounds); y0 = min(b[1] for b in bounds)
        x1 = max(b[0]+b[2] for b in bounds); y1 = max(b[1]+b[3] for b in bounds)
        # Mantener fijo el zoom y el origen mientras se arrastra para evitar saltos.
        if not self.drag:
            self.factor = min((width-100)/max(x1-x0,1), (height-100)/max(y1-y0,1), .25)
            self.origin = ((width-(x1-x0)*self.factor)/2-x0*self.factor, (height-(y1-y0)*self.factor)/2-y0*self.factor)
        factor = self.factor; ox,oy = self.origin
        self.geometry = {}
        for d in active:
            w,h = backend.size(d); x = ox+d['x']*factor; y = oy+d['y']*factor; w*=factor; h*=factor
            self.geometry[d['name']] = (x,y,w,h)
            chosen = d['name'] == self.app.selected
            cr.rectangle(x+3,y+3,max(1,w-6),max(1,h-6))
            cr.set_source_rgb(*rgb(colors['selection'] if chosen else colors['dark_background'])); cr.fill_preserve()
            cr.set_line_width(3 if chosen else 1.5); cr.set_source_rgb(*rgb(colors['accent'] if chosen else colors['bright_foreground'])); cr.stroke()
            cr.set_source_rgb(*rgb(colors['foreground'])); cr.select_font_face('Pixelify Sans', 0, 1); cr.set_font_size(max(11,min(17,w/8)))
            text = f"{self.app.numbers.get(d['name'], '?')} · {d['name']}"; ext = cr.text_extents(text); cr.move_to(x+(w-ext.width)/2,y+h/2-2); cr.show_text(text)
            cr.select_font_face('Pixelify Sans',0,0); cr.set_font_size(max(10,min(12,w/12)))
            text = f"{d['width']} × {d['height']} · {d['scale']:g}×"; ext = cr.text_extents(text); cr.move_to(x+(w-ext.width)/2,y+h/2+17); cr.show_text(text)

    def press(self, widget, event):
        if event.button != 1: return
        for name,(x,y,w,h) in reversed(list(self.geometry.items())):
            if x <= event.x <= x+w and y <= event.y <= y+h:
                self.app.select(name)
                d = self.app.get_selected()
                self.drag = (name,event.x,event.y,d['x'],d['y'])
                self.queue_draw(); return True
        return False

    def motion(self, widget, event):
        if not self.drag: return False
        name, sx, sy, x, y = self.drag
        d = next(d for d in self.app.displays if d['name'] == name)
        d['x'] = round(x + (event.x-sx)/self.factor)
        d['y'] = round(y + (event.y-sy)/self.factor)
        self.queue_draw(); self.app.changed(); return True

    def release(self, widget, event):
        if not self.drag: return False
        d = self.app.get_selected(); self.snap(d)
        self.drag = None; self.queue_draw(); self.app.changed(); return True

    def snap(self, d):
        w,h = backend.size(d); candidates=[]
        for other in self.app.displays:
            if not other['enabled'] or other is d: continue
            ow,oh=backend.size(other); x,y=d['x'],d['y']; ox,oy=other['x'],other['y']
            # Acercar bordes y, cuando coincidan, alinear también las esquinas.
            for nx in (ox+ow, ox-w):
                if min(y+h,oy+oh) > max(y,oy): candidates.append((abs(nx-x), nx,y,'x'))
            for ny in (oy+oh, oy-h):
                if min(x+w,ox+ow) > max(x,ox): candidates.append((abs(ny-y), x,ny,'y'))
        if not candidates: return
        dist,x,y,axis=min(candidates)
        if dist > max(100, round(24/self.factor)): return
        d['x'],d['y']=x,y
        for o in self.app.displays:
            if not o['enabled'] or o is d: continue
            ow,oh=backend.size(o)
            if axis == 'x':
                for n in (o['y'],o['y']+oh-h):
                    if abs(n-d['y']) < 70: d['y']=n; break
            else:
                for n in (o['x'],o['x']+ow-w):
                    if abs(n-d['x']) < 70: d['x']=n; break

class App(Gtk.Window):
    def __init__(self):
        super().__init__(title='Omarchy Monitors')
        self.set_default_size(1060, 690); self.set_position(Gtk.WindowPosition.CENTER)
        self.instance=uuid.uuid4().hex
        labels.register_instance(self.instance)
        self.connect('destroy', self.on_destroy)
        self.language=i18n.get_language(); self.translated_widgets=[]; self.language_buttons={}
        self.displays=[]; self.selected=None; self.updating=False; self.original=''; self.tx=None; self.numbers={}
        css = Gtk.CssProvider(); css.load_from_data(themed_css(theme()))
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        root=Gtk.Box(orientation=Gtk.Orientation.VERTICAL); self.add(root)
        header=Gtk.Box(spacing=14); header.set_border_width(20); header.get_style_context().add_class('header'); root.pack_start(header,False,False,0)
        logo=Path(__file__).resolve().parent.parent/'data/omarchy-monitors.png'
        if logo.exists():
            from gi.repository import GdkPixbuf
            icon=GdkPixbuf.Pixbuf.new_from_file_at_scale(str(logo),48,48,True); self.set_icon(icon)
            header.pack_start(Gtk.Image.new_from_pixbuf(icon),False,False,0)
        else:
            symbol=label('▦'); symbol.set_markup('<span size="24000">▦</span>'); header.pack_start(symbol,False,False,0)
        titles=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=3); titles.pack_start(label('OMARCHY MONITORS','title'),False,False,0); titles.pack_start(self.localized_label('Tu escritorio, en el orden que tú quieras','subtitle'),False,False,0); header.pack_start(titles,True,True,0)
        for code,name in (('en','English'),('es','Español')):
            flag=Gtk.DrawingArea(); flag.set_size_request(30,20); flag.connect('draw',draw_flag,code)
            control=Gtk.Button(); control.add(flag); control.set_tooltip_text(name); control.get_accessible().set_name(name)
            control.get_style_context().add_class('language'); control.connect('clicked',lambda _,lang=code: self.change_language(lang))
            self.language_buttons[code]=control; header.pack_start(control,False,False,0)
        self.update_language_buttons()
        header.pack_start(self.localized_button('Identificar',self.identify),False,False,0)
        header.pack_start(self.localized_button('Recargar',self.reload),False,False,0)
        content=Gtk.Box(); root.pack_start(content,True,True,0)
        self.main_scroll=Gtk.ScrolledWindow()
        self.main_scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        content.pack_start(self.main_scroll,True,True,0)
        main=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14); main.set_border_width(22); self.main_scroll.add(main)
        row=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
        row.pack_start(self.localized_label('DISTRIBUCIÓN','section'),False,False,0)
        row.pack_start(self.localized_label('Arrastra para mover · Los bordes se ajustan solos','hint'),False,False,0)
        main.pack_start(row,False,False,0)
        frame=Gtk.Frame(); frame.get_style_context().add_class('card'); main.pack_start(frame,True,True,0)
        self.canvas=Canvas(self); frame.add(self.canvas)
        self.message=label(self.tr('Selecciona una pantalla para ver sus opciones.'),'hint'); main.pack_start(self.message,False,False,0)
        self.side_scroll=Gtk.ScrolledWindow()
        self.side_scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        self.side_scroll.set_propagate_natural_width(True)
        content.pack_start(self.side_scroll,False,False,0)
        side=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14); side.set_border_width(22); side.set_size_request(300,-1); side.get_style_context().add_class('sidebar'); self.side_scroll.add(side)
        side.pack_start(self.localized_label('PANTALLAS CONECTADAS','section'),False,False,0)
        self.listbox=Gtk.ListBox(); self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE); self.listbox.connect('row-selected',self.list_selected); side.pack_start(self.listbox,False,False,0)
        side.pack_start(Gtk.Separator(),False,False,2)
        self.detail=label(self.tr('Selecciona una pantalla'),'title'); side.pack_start(self.detail,False,False,0)
        self.enabled=Gtk.Switch(); self.enabled.connect('notify::active',self.toggle_enabled)
        switchrow=Gtk.Box(); switchrow.pack_start(self.localized_label('Pantalla encendida'),True,True,0); switchrow.pack_end(self.enabled,False,False,0); side.pack_start(switchrow,False,False,0)
        side.pack_start(self.localized_label('Resolución y frecuencia','hint'),False,False,0)
        self.modes=Gtk.ComboBoxText(); self.modes.connect('changed',self.mode_changed); side.pack_start(self.modes,False,False,0)
        side.pack_start(self.localized_label('Escala','hint'),False,False,0)
        self.scales=Gtk.ComboBoxText(); self.scales.connect('changed',self.scale_changed); side.pack_start(self.scales,False,False,0)
        side.pack_start(self.localized_label('Una escala mayor aumenta el contenido y reduce el tamaño en el mapa.','hint'),False,False,0)
        side.pack_start(Gtk.Separator(),False,False,3)
        labelrow=Gtk.Box(spacing=8); labelrow.pack_start(self.localized_label('Mostrar nombres en las pantallas'),True,True,0)
        self.labels_switch=Gtk.Switch(); self.labels_switch.set_active(labels.enabled())
        self.labels_switch.connect('notify::active',self.toggle_labels); labelrow.pack_end(self.labels_switch,False,False,0)
        side.pack_start(labelrow,False,False,0)
        side.pack_start(Gtk.Box(),True,True,0)
        self.apply_button=self.localized_button('Aplicar cambios',self.apply,True); side.pack_start(self.apply_button,False,False,0)
        side.pack_start(self.localized_label('Podrás confirmar o volver atrás.','hint'),False,False,0)
        self.reload()
        labels.start_service()
        # Si otra ventana se cierra justo al abrir esta, reintentar después de
        # que el proceso anterior haya liberado su bloqueo de instancia única.
        GLib.timeout_add(700,lambda: (labels.start_service(),False)[1])

    def tr(self, text): return i18n.tr(text,self.language)

    def localized_label(self, text, css=None):
        widget=label(self.tr(text),css)
        self.translated_widgets.append((widget,text,'set_text'))
        return widget

    def localized_button(self, text, callback, primary=False):
        widget=button(self.tr(text),callback,primary)
        self.translated_widgets.append((widget,text,'set_label'))
        return widget

    def update_language_buttons(self):
        for code,control in self.language_buttons.items():
            style=control.get_style_context()
            if code == self.language: style.add_class('language-active')
            else: style.remove_class('language-active')

    def change_language(self, language):
        if language == self.language: return
        try: i18n.set_language(language)
        except OSError as exc: self.error(str(exc)); return
        self.language=language
        for widget,text,method in self.translated_widgets: getattr(widget,method)(self.tr(text))
        self.update_language_buttons(); self.populate(); self.changed()

    def error(self, text):
        dialog=Gtk.MessageDialog(transient_for=self,modal=True,message_type=Gtk.MessageType.ERROR,buttons=Gtk.ButtonsType.CLOSE,text=self.tr('No se pudo completar la operación'))
        dialog.format_secondary_text(self.tr(str(text))); dialog.run(); dialog.destroy()

    def on_destroy(self, *_):
        labels.unregister_instance(self.instance)
        labels.clear_selected(self.instance)
        Gtk.main_quit()

    def reload(self, *_):
        try:
            self.original=backend.CONFIG.read_text()
            self.displays=backend.snapshot(backend.live_monitors(), backend.read_saved(self.original))
            if not self.displays: raise backend.DisplayError('No se encontraron pantallas con modos disponibles.')
            self.numbers=labels.numbers(self.displays)
            self.original_displays=copy.deepcopy(self.displays)
            if self.selected not in [d['name'] for d in self.displays]: self.selected=self.displays[0]['name']
            labels.set_selected(self.selected,self.instance)
            self.populate(); self.canvas.queue_draw(); self.changed()
        except Exception as exc: self.error(exc)

    def get_selected(self): return next((d for d in self.displays if d['name']==self.selected),None)
    def toggle_labels(self, switch, pspec):
        try: labels.set_enabled(switch.get_active())
        except Exception as exc: self.error('No se pudo cambiar la opción: '+str(exc))
    def identify(self, *_):
        try:
            gi.require_version('GtkLayerShell', '0.1')
            from gi.repository import GtkLayerShell
            screen=Gdk.Display.get_default()
            for d in self.displays:
                if not d['enabled']: continue
                w,h=backend.size(d)
                matches=[]
                for i in range(screen.get_n_monitors()):
                    monitor=screen.get_monitor(i); g=monitor.get_geometry()
                    if (g.x,g.y,g.width,g.height)==(d['x'],d['y'],w,h): matches.append(monitor)
                if len(matches)!=1: continue
                overlay=Gtk.Window(); overlay.set_decorated(False); overlay.set_default_size(270,110)
                GtkLayerShell.init_for_window(overlay); GtkLayerShell.set_layer(overlay,GtkLayerShell.Layer.OVERLAY)
                GtkLayerShell.set_monitor(overlay,matches[0]); GtkLayerShell.set_namespace(overlay,'pantallas-identificar')
                box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8); box.set_border_width(25); box.get_style_context().add_class('card')
                box.pack_start(label(f"{self.numbers.get(d['name'], '?')} · {d['name']}",'title',.5),True,True,0); box.pack_start(label(d['label'],'hint',.5),True,True,0); overlay.add(box); overlay.show_all()
                GLib.timeout_add_seconds(4,lambda win=overlay: (win.destroy(),False)[1])
        except Exception as exc: self.error('No se pudieron mostrar los identificadores: ' + str(exc))
    def select(self,name):
        self.selected=name
        labels.set_selected(name,self.instance)
        self.populate(); self.canvas.queue_draw()
    def list_selected(self, box, row):
        if not self.updating and row: self.select(row.name)

    def populate(self):
        self.updating=True
        for row in self.listbox.get_children(): self.listbox.remove(row)
        for d in sorted(self.displays, key=lambda item: self.numbers.get(item['name'], 0)):
            row=Gtk.ListBoxRow(); row.name=d['name']; box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=2); box.set_border_width(9)
            box.pack_start(label(str(self.numbers.get(d['name'],'?'))+'  ·  '+d['name']+'  ·  '+d['label']),False,False,0); box.pack_start(label(self.tr('Encendida' if d['enabled'] else 'Apagada'),'hint'),False,False,0); row.add(box); self.listbox.add(row)
            if d['name']==self.selected: self.listbox.select_row(row)
        self.listbox.show_all(); d=self.get_selected()
        if d:
            self.detail.set_text(d['name']); self.enabled.set_active(d['enabled']); self.modes.remove_all()
            modes=list(d['modes']); current=(d['width'],d['height'],d['refresh'])
            if not any((w,h)==current[:2] and abs(hz-current[2])<.15 for w,h,hz in modes): modes.insert(0,current)
            self.mode_values=modes
            for w,h,hz in modes: self.modes.append_text(f'{w} × {h}  ·  {hz:g} Hz')
            self.modes.set_active(next((i for i,(w,h,hz) in enumerate(modes) if (w,h)==current[:2] and abs(hz-current[2])<.15),0))
            self.scales.remove_all(); self.scale_values=[s for s in (1,1.25,1.5,1.6,1.75,2,2.5,3,4) if abs(round(d['width']/s)*s-d['width'])<.01 and abs(round(d['height']/s)*s-d['height'])<.01]
            if d['scale'] not in self.scale_values: self.scale_values.append(d['scale']); self.scale_values.sort()
            for s in self.scale_values: self.scales.append_text(f'{s:g}×')
            self.scales.set_active(self.scale_values.index(d['scale']))
            self.modes.set_sensitive(d['enabled']); self.scales.set_sensitive(d['enabled'])
        self.updating=False

    def toggle_enabled(self, switch, pspec):
        if self.updating: return
        d=self.get_selected()
        if d: d['enabled']=switch.get_active(); self.populate(); self.canvas.queue_draw(); self.changed()
    def mode_changed(self, combo):
        if self.updating or combo.get_active()<0:return
        d=self.get_selected(); d['width'],d['height'],d['refresh']=self.mode_values[combo.get_active()]; self.populate(); self.canvas.queue_draw(); self.changed()
    def scale_changed(self, combo):
        if self.updating or combo.get_active()<0:return
        self.get_selected()['scale']=self.scale_values[combo.get_active()]; self.canvas.queue_draw(); self.changed()
    def changed(self):
        issue=backend.boxes_valid(self.displays) if self.displays else 'No hay pantallas disponibles.'
        self.message.set_text(self.tr(issue or 'Las pantallas están conectadas por sus bordes.')); self.message.get_style_context().remove_class('warning')
        if issue: self.message.get_style_context().add_class('warning')
        self.apply_button.set_sensitive(not issue)
    def apply(self, *_):
        try: self.tx=backend.apply(self.displays,self.original,self.original_displays)
        except Exception as exc: self.error(exc); return
        dialog=Gtk.MessageDialog(transient_for=self,modal=True,message_type=Gtk.MessageType.QUESTION,buttons=Gtk.ButtonsType.NONE,text=self.tr('¿Se ven bien las pantallas?'))
        dialog.add_button(self.tr('Volver atrás'),Gtk.ResponseType.REJECT); dialog.add_button(self.tr('Conservar cambios'),Gtk.ResponseType.ACCEPT)
        deadline=time.monotonic()+max(0,json.loads(self.tx.read_text())['deadline']-time.time())
        def tick():
            remaining=max(0,math.ceil(deadline-time.monotonic()))
            dialog.format_secondary_text(self.tr('Si no confirmas, se restaurará la distribución anterior en {seconds} segundos.').format(seconds=remaining))
            if remaining<=0: dialog.response(Gtk.ResponseType.REJECT); return False
            return True
        tick(); timer=GLib.timeout_add_seconds(1,tick); response=dialog.run(); GLib.source_remove(timer) if GLib.MainContext.default().find_source_by_id(timer) else None; dialog.destroy()
        try:
            if response==Gtk.ResponseType.ACCEPT and time.time()<json.loads(self.tx.read_text())['deadline']: backend.confirm(self.tx)
            elif self.tx.exists() and not backend.revert(self.tx): self.error('La configuración cambió desde otra aplicación; no se sobrescribió. Se conservó una copia de recuperación.')
        except FileNotFoundError: pass
        except Exception as exc: self.error(exc)
        self.tx=None; self.reload()

def main():
    win=App(); win.show_all(); Gtk.main()
