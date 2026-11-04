"""Idioma inicial, persistencia y traducción de mensajes de seguridad."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pantallas import i18n, backend

class Idiomas(unittest.TestCase):
    def test_ingles_es_predeterminado(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(i18n, 'LANGUAGE_FILE', Path(directory)/'language'):
                self.assertEqual(i18n.get_language(),'en')
                self.assertEqual(i18n.tr('Aplicar cambios',i18n.get_language()),'Apply changes')

    def test_preferencia_persiste_y_valida(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(i18n, 'LANGUAGE_FILE', Path(directory)/'language'):
                i18n.set_language('es'); self.assertEqual(i18n.get_language(),'es')
                self.assertEqual(i18n.tr('Aplicar cambios','es'),'Aplicar cambios')
                i18n.set_language('en'); self.assertEqual(i18n.get_language(),'en')
                with self.assertRaises(ValueError): i18n.set_language('fr')

    def test_errores_tambien_se_traducen(self):
        issue=backend.boxes_valid([])
        self.assertEqual(i18n.tr(issue,'en'),'At least one display must remain enabled.')
        self.assertEqual(i18n.tr('Hay reglas duplicadas para DP-1','en'),'Duplicate rules for DP-1')
        self.assertIn('25',i18n.tr('Si no confirmas, se restaurará la distribución anterior en {seconds} segundos.','en').format(seconds=25))

if __name__ == '__main__': unittest.main()
