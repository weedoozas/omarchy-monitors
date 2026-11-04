import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pantallas import backend as b
from pantallas import labels


def display(name='DP-1', x=0, y=0, enabled=True):
    return dict(name=name, label=name, enabled=enabled, x=x, y=y, width=1920, height=1080,
                refresh=60., scale=1., transform=0, modes=[(1920,1080,60.)], mirror='none', rule={})

class BackendTest(unittest.TestCase):
    def test_valid_and_disconnected_layout(self):
        a=display(); c=display('DP-2',1920,0)
        self.assertIsNone(b.boxes_valid([a,c]))
        c['x']=1921; self.assertIn('tocarse', b.boxes_valid([a,c]))
        c['x']=1919; self.assertIn('superpuestas', b.boxes_valid([a,c]))
        a['enabled']=False; c['enabled']=False; self.assertIn('menos una', b.boxes_valid([a,c]))

    def test_scales_and_rotation_affect_geometry(self):
        a=display(); a['scale']=1.6; a['transform']=1
        self.assertEqual(b.size(a),(675,1200))
        self.assertIsNone(b.boxes_valid([a,display('DP-2',675,0)]))

    def test_disabled_display_restores_saved_size(self):
        live=[dict(name='DP-1',model='TV',disabled=True,width=0,height=0,refreshRate=60,x=-1,y=-1,scale=1,transform=0,availableModes=['1360x768@60.02Hz','1920x1080@60.00Hz'])]
        saved={'DP-1':dict(mode='1920x1080@60',position='1920x1080',scale=1)}
        d=b.snapshot(live,saved)[0]
        self.assertEqual((d['width'],d['height'],d['x'],d['y']),(1920,1080,1920,1080))
        saved['DP-1']['mode']='0x0@60'
        self.assertEqual(b.snapshot(live,saved)[0]['width'],1360)

    def test_preserves_unrelated_lua_and_general_rule(self):
        text='-- configuración propia\nlocal scale = 1\nhl.monitor({ output = "", mode = "preferred", position = "auto", scale = scale })\nhl.monitor({ output = "DP-1", mode = "1920x1080@60", position = "0x0", scale = 1, vrr = 1 })\n-- final\n'
        out=b.render(text,[display(x=1920)])
        self.assertIn('scale = scale',out); self.assertIn('vrr = 1',out); self.assertIn('position = "1920x0"',out); self.assertIn('-- final',out)

    def test_rejects_ambiguous_lua_and_duplicates(self):
        with self.assertRaises(b.DisplayError): b.render('hl.monitor({ output = "DP-1", scale = my_scale })', [display()])
        s='hl.monitor({ output = "DP-1", scale = 1 })\n'
        with self.assertRaises(b.DisplayError): b.render(s+s,[display()])

    def test_revert_partial_transaction_and_protect_external_edits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); p=root/'one'; q=root/'two'; txpath=root/'transaction.json'; p.write_text('new'); q.write_text('old2')
            tx={'files':[{'path':str(p),'before':'old','after_hash':b.digest('new')},{'path':str(q),'before':'old2','after_hash':b.digest('new2')}]}
            txpath.write_text(json.dumps(tx))
            with patch.object(b,'LOCK',root/'lock'),patch.object(b,'ctl',return_value=''):
                self.assertTrue(b.revert(txpath)); self.assertEqual(p.read_text(),'old'); self.assertEqual(q.read_text(),'old2')
                p.write_text('externo'); txpath.write_text(json.dumps(tx))
                self.assertFalse(b.revert(txpath)); self.assertEqual(p.read_text(),'externo'); self.assertTrue(txpath.exists())

    def test_renderer_only_edits_selected_outputs(self):
        text='hl.monitor({ output = "DP-9", mode = "800x600@60", position = "0x0", scale = 1 })\n'
        out=b.render(text,[display()]); self.assertIn(text,out); self.assertIn('output = "DP-1"',out)

    def test_numeros_se_mantienen_al_cambiar_la_distribucion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(labels,'CONFIG_DIR',root),patch.object(labels,'NUMBERS',root/'numbers.json'):
                displays=[display('DP-1',1920,1080),display('eDP-1',0,0),display('DP-2',1920,0)]
                first=labels.numbers(displays)
                self.assertEqual(first,{'eDP-1':1,'DP-2':2,'DP-1':3})
                displays[0]['y']=-10
                self.assertEqual(labels.numbers(displays),first)
                displays.append(display('HDMI-A-1',0,1080))
                self.assertEqual(labels.numbers(displays)['HDMI-A-1'],4)

    def test_activar_y_desactivar_nombres_sin_arranque_automatico(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(labels,'CONFIG_DIR',root/'config'),patch.object(labels,'PREFERENCE',root/'config/enabled'),patch.object(labels,'AUTOSTART',root/'autostart/labels.desktop'):
                self.assertTrue(labels.enabled())
                labels.set_enabled(True,launch=False)
                self.assertTrue(labels.enabled())
                self.assertFalse(labels.AUTOSTART.exists())
                labels.set_enabled(False)
                self.assertFalse(labels.enabled())
                self.assertFalse(labels.AUTOSTART.exists())

    def test_etiquetas_siguen_ventanas_y_eliminan_instancias_huerfanas(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); instances=root/'instances'; old_autostart=root/'old.desktop'
            old_autostart.write_text('versión anterior')
            with patch.object(labels,'INSTANCES',instances),patch.object(labels,'AUTOSTART',old_autostart),patch.object(labels,'stop_legacy_service') as stop:
                labels.register_instance('a'); labels.register_instance('b')
                self.assertFalse(old_autostart.exists())
                stop.assert_called_once()
                self.assertTrue(labels.active_instances())
                labels.unregister_instance('a')
                self.assertTrue(labels.active_instances())
                with patch.object(labels,'process_started',return_value=None):
                    self.assertFalse(labels.active_instances())
                self.assertFalse((instances/'b').exists())

    def test_seleccion_sigue_instancia_y_se_limpia_al_cerrar(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(b,'STATE',root),patch.object(labels,'SELECTION',root/'selected.json'),patch.object(labels,'SELECTION_LOCK',root/'selection.lock'):
                labels.set_selected('DP-1','instancia-a')
                self.assertEqual(labels.selected(),'DP-1')
                labels.set_selected('DP-2','instancia-b')
                labels.clear_selected('instancia-a')
                self.assertEqual(labels.selected(),'DP-2')
                labels.clear_selected('instancia-b')
                self.assertEqual(labels.selected(),'')

    def test_color_de_texto_contrasta_con_acento(self):
        self.assertEqual(labels.selection_text_color('#ffffff'),'#000000')
        self.assertEqual(labels.selection_text_color('#000000'),'#ffffff')

    def test_seleccion_huerfana_no_resalta(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); selection=root/'selected.json'
            selection.write_text(json.dumps({'name':'DP-1','pid':99999999}))
            with patch.object(labels,'SELECTION',selection):
                self.assertEqual(labels.selected(),'')

if __name__ == '__main__': unittest.main()
