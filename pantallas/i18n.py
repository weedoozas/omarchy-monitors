"""Traducciones y preferencia de idioma de la interfaz."""
from pathlib import Path
import os
from . import backend

LANGUAGE_FILE = Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config'))/'omarchy-monitors/language'
ENGLISH = {
    'Tu escritorio, en el orden que tú quieras': 'Your desktop, arranged your way',
    'Identificar': 'Identify',
    'Recargar': 'Reload',
    'DISTRIBUCIÓN': 'LAYOUT',
    'Arrastra para mover · Los bordes se ajustan solos': 'Drag to move · Edges snap together',
    'Selecciona una pantalla para ver sus opciones.': 'Select a display to see its settings.',
    'PANTALLAS CONECTADAS': 'CONNECTED DISPLAYS',
    'Selecciona una pantalla': 'Select a display',
    'Pantalla encendida': 'Display enabled',
    'Resolución y frecuencia': 'Resolution and refresh rate',
    'Escala': 'Scale',
    'Una escala mayor aumenta el contenido y reduce el tamaño en el mapa.': 'A larger scale makes content bigger and the display smaller on the map.',
    'Nombres siempre visibles': 'Always show display names',
    'Aplicar cambios': 'Apply changes',
    'Podrás confirmar o volver atrás.': 'You can keep or revert the changes.',
    'No se pudo completar la operación': 'The operation could not be completed',
    'No se encontraron pantallas con modos disponibles.': 'No displays with available modes were found.',
    'Encendida': 'Enabled',
    'Apagada': 'Disabled',
    'No hay pantallas disponibles.': 'No displays are available.',
    'Las pantallas están conectadas por sus bordes.': 'Displays are connected at their edges.',
    '¿Se ven bien las pantallas?': 'Do the displays look right?',
    'Volver atrás': 'Revert',
    'Conservar cambios': 'Keep changes',
    'Si no confirmas, se restaurará la distribución anterior en {seconds} segundos.': 'The previous layout will be restored in {seconds} seconds unless you confirm.',
    'La configuración cambió desde otra aplicación; no se sobrescribió. Se conservó una copia de recuperación.': 'The configuration changed in another application, so it was not overwritten. Recovery data was preserved.',
    'Debe quedar al menos una pantalla encendida.': 'At least one display must remain enabled.',
    'El modo espejo no se puede editar todavía. Desactívalo antes de aplicar.': 'Mirroring cannot be edited yet. Disable it before applying changes.',
    'Hay pantallas superpuestas. Arrástralas hasta que solo se toquen por los bordes.': 'Displays overlap. Drag them until they only touch at the edges.',
    'Las pantallas deben tocarse por un borde para poder mover el cursor entre ellas.': 'Displays must touch at an edge so the cursor can move between them.',
    'No existe ~/.config/hypr/monitors.lua.': '~/.config/hypr/monitors.lua does not exist.',
    'La configuración cambió en otra aplicación. Pulsa Recargar antes de intentarlo otra vez.': 'The configuration changed in another application. Select Reload before trying again.',
    'Las pantallas conectadas cambiaron. Pulsa Recargar.': 'The connected displays changed. Select Reload.',
    'La distribución cambió en otra aplicación. Pulsa Recargar.': 'The layout changed in another application. Select Reload.',
    'La configuración contiene una regla de monitor compleja que no se puede editar con seguridad.': 'The configuration contains a complex monitor rule that cannot be edited safely.',
    'La configuración contiene reglas de monitor que no se pueden editar con seguridad.': 'The configuration contains monitor rules that cannot be edited safely.',
    'Hyprland no aplicó todos los cambios.': 'Hyprland did not apply all the changes.',
    'Falló hyprctl': 'hyprctl failed',
}
PREFIXES = {
    'No se pudo cambiar la opción: ': 'Could not change the setting: ',
    'No se pudieron mostrar los identificadores: ': 'Could not show the display identifiers: ',
    'No se pudo consultar Hyprland: ': 'Could not query Hyprland: ',
    'Hay reglas duplicadas para ': 'Duplicate rules for ',
    'Hyprland informó un error: ': 'Hyprland reported an error: ',
}

def get_language():
    try: value=LANGUAGE_FILE.read_text().strip()
    except OSError: return 'en'
    return value if value in ('en','es') else 'en'

def set_language(language):
    if language not in ('en','es'): raise ValueError('Unsupported language')
    backend.atomic(LANGUAGE_FILE,language+'\n')

def tr(message, language):
    if language != 'en': return message
    if message in ENGLISH: return ENGLISH[message]
    for source,target in PREFIXES.items():
        if message.startswith(source): return target+tr(message[len(source):],language)
    return message
