"""Comprobar el acceso a los dos paneles en una ventana de poca altura."""
import os
import unittest
from unittest.mock import patch

try:
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, GLib
    from pantallas.app import App
    from pantallas import i18n, labels
    GTK_AVAILABLE = bool(os.environ.get('WAYLAND_DISPLAY') and Gtk.init_check()[0])
except (ImportError, ValueError):
    GTK_AVAILABLE = False

@unittest.skipUnless(GTK_AVAILABLE, 'Se necesita una sesión gráfica de Wayland y GTK 3')
class VistaCompacta(unittest.TestCase):
    def test_paneles_desplazables_en_ambos_idiomas(self):
        for language in ('en','es'):
            with self.subTest(language=language), patch.object(i18n,'get_language',return_value=language), \
                 patch.object(labels,'enabled',return_value=False), patch.object(labels,'clear_selected'), \
                 patch.object(App,'reload'), patch.object(Gtk,'main_quit'):
                app=App()
                for name in ('eDP-1','DP-1','DP-2','HDMI-A-1'):
                    app.listbox.add(Gtk.Label(label=name))
                root=app.get_child(); app.remove(root)
                window=Gtk.OffscreenWindow(); window.set_size_request(950,400); window.add(root); window.show_all()
                loop=GLib.MainLoop(); errors=[]
                def scroll():
                    try:
                        for panel in (app.main_scroll,app.side_scroll):
                            adj=panel.get_vadjustment()
                            self.assertGreater(adj.get_upper(),adj.get_page_size())
                            adj.set_value(adj.get_upper()-adj.get_page_size())
                            self.assertGreater(adj.get_value(),0)
                        GLib.timeout_add(100,verify)
                    except Exception as exc:
                        errors.append(exc); loop.quit()
                    return False
                def verify():
                    try:
                        position=app.apply_button.translate_coordinates(app.side_scroll,0,0)
                        self.assertIsNotNone(position)
                        self.assertGreaterEqual(position[1],0)
                        self.assertLessEqual(position[1]+app.apply_button.get_allocated_height(),app.side_scroll.get_allocated_height())
                    except Exception as exc: errors.append(exc)
                    finally: loop.quit()
                    return False
                GLib.timeout_add(250,scroll); loop.run()
                window.destroy(); app.destroy()
                if errors: raise errors[0]

if __name__ == '__main__': unittest.main()
