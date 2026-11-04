"""Consulta y aplica distribuciones de Hyprland con recuperación automática."""
from __future__ import annotations
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import uuid

HOME = Path.home()
CONFIG = HOME / '.config/hypr/monitors.lua'
STATE = HOME / '.local/state/pantallas'
LOCK = HOME / '.local/state/omarchy/display-config.lock'
BLOCK = re.compile(r'hl\.monitor\s*\(\s*\{([^{}]*)\}\s*\)', re.S)
FIELD = re.compile(r'\s*(\w+)\s*=\s*("(?:[^"\\]|\\.)*"|true|false|-?\d+(?:\.\d+)?)\s*,?')
MODE = re.compile(r'^(\d+)x(\d+)@([\d.]+)(?:Hz)?$')

class DisplayError(Exception):
    pass

def ctl(*args):
    result = subprocess.run(['hyprctl', *args], capture_output=True, text=True, timeout=10)
    if result.returncode or result.stdout.lstrip().lower().startswith(('error:', 'unknown')):
        raise DisplayError(result.stderr.strip() or result.stdout.strip() or 'Falló hyprctl')
    return result.stdout

def live_monitors():
    try:
        return json.loads(ctl('-j', 'monitors', 'all'))
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        raise DisplayError('No se pudo consultar Hyprland: ' + str(exc)) from exc

def atomic(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as out:
            out.write(content)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(name, path.stat().st_mode & 0o777 if path.exists() else 0o600)
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def parse_block(block):
    result = {}
    def capture(match):
        result[match[1]] = json.loads(match[2])
        return ''
    rest = FIELD.sub(capture, block)
    if rest.strip() or 'output' not in result:
        return None
    return result

def read_saved(text):
    rules = {}
    for match in BLOCK.finditer(text):
        rule = parse_block(match[1])
        if rule and rule['output']:
            if rule['output'] in rules:
                raise DisplayError('Hay reglas duplicadas para ' + rule['output'])
            rules[rule['output']] = rule
    return rules

def mode_parts(mode):
    match = MODE.match(str(mode))
    if not match or not int(match[1]) or not int(match[2]):
        return None
    return int(match[1]), int(match[2]), float(match[3])

def snapshot(live, saved):
    displays = []
    for m in live:
        rule = saved.get(m['name'], {})
        enabled = not m.get('disabled', False)
        current = (int(m['width']), int(m['height']), float(m['refreshRate'])) if enabled and m['width'] and m['height'] else mode_parts(rule.get('mode', ''))
        modes = [mode_parts(x) for x in m.get('availableModes', [])]
        modes = list(dict.fromkeys(x for x in modes if x))
        current = current or (modes[0] if modes else None)
        if not current:
            continue
        position = re.fullmatch(r'(-?\d+)x(-?\d+)', str(rule.get('position', '')))
        x, y = (int(m['x']), int(m['y'])) if enabled else ((int(position[1]), int(position[2])) if position else (0, 0))
        displays.append(dict(name=m['name'], label=m.get('model') or m['name'], enabled=enabled,
            x=x, y=y, width=current[0], height=current[1], refresh=current[2],
            scale=float(m['scale'] if enabled else rule.get('scale', 1)),
            transform=int(m.get('transform', 0) if enabled else rule.get('transform', 0)),
            modes=modes, mirror=m.get('mirrorOf', 'none'), rule=copy.deepcopy(rule)))
    return displays

def size(d):
    w, h = d['width'], d['height']
    if d['transform'] % 2: w, h = h, w
    return round(w / d['scale']), round(h / d['scale'])

def boxes_valid(displays):
    active = [d for d in displays if d['enabled']]
    if not active: return 'Debe quedar al menos una pantalla encendida.'
    if any(d.get('mirror', 'none') not in ('none', '', None) for d in active):
        return 'El modo espejo no se puede editar todavía. Desactívalo antes de aplicar.'
    for i, a in enumerate(active):
        aw, ah = size(a)
        for b in active[i + 1:]:
            bw, bh = size(b)
            if min(a['x'] + aw, b['x'] + bw) > max(a['x'], b['x']) and min(a['y'] + ah, b['y'] + bh) > max(a['y'], b['y']):
                return 'Hay pantallas superpuestas. Arrástralas hasta que solo se toquen por los bordes.'
    seen = {0}
    while True:
        previous = len(seen)
        for i in list(seen):
            a = active[i]; aw, ah = size(a)
            for j, b in enumerate(active):
                bw, bh = size(b)
                dx = min(a['x'] + aw, b['x'] + bw) - max(a['x'], b['x'])
                dy = min(a['y'] + ah, b['y'] + bh) - max(a['y'], b['y'])
                if (dx == 0 and dy > 0) or (dy == 0 and dx > 0): seen.add(j)
        if len(seen) == previous: break
    if len(seen) != len(active): return 'Las pantallas deben tocarse por un borde para poder mover el cursor entre ellas.'
    return None

def build_rule(d):
    r = copy.deepcopy(d['rule'])
    r.update(output=d['name'], mode=f"{d['width']}x{d['height']}@{d['refresh']}",
             position=f"{d['x']}x{d['y']}", scale=d['scale'], disabled=not d['enabled'], transform=d['transform'])
    return r

def render(text, displays):
    updates = {d['name']: build_rule(d) for d in displays}
    touched = set()
    def replace(match):
        rule = parse_block(match[1])
        if not rule:
            # La regla general de Omarchy suele usar variables Lua para la
            # escala; se conserva tal cual porque no corresponde a una salida.
            if re.search(r'\boutput\s*=\s*""', match[1]): return match[0]
            # No se reescriben expresiones Lua que la aplicación no comprende.
            raise DisplayError('La configuración contiene una regla de monitor compleja que no se puede editar con seguridad.')
        name = rule['output']
        if name not in updates: return match[0]
        if name in touched: raise DisplayError('Hay reglas duplicadas para ' + name)
        touched.add(name)
        merged = dict(rule); merged.update(updates[name])
        return 'hl.monitor({ ' + ', '.join(f'{k} = {json.dumps(v, ensure_ascii=False)}' for k, v in merged.items()) + ' })'
    rendered = BLOCK.sub(replace, text)
    # Rechazar reglas que el parser no detectó en lugar de escribir algo ambiguo.
    if len(re.findall(r'hl\.monitor\s*\(', text)) != len(list(BLOCK.finditer(text))):
        raise DisplayError('La configuración contiene reglas de monitor que no se pueden editar con seguridad.')
    for name, rule in updates.items():
        if name not in touched:
            rendered += '\nhl.monitor({ ' + ', '.join(f'{k} = {json.dumps(v, ensure_ascii=False)}' for k, v in rule.items()) + ' })\n'
    return rendered

def compat_conf(displays):
    lines = ['# Copia compatible; la fuente es monitors.lua.']
    for d in displays:
        r = build_rule(d)
        if not d['enabled']: lines.append('monitor=' + d['name'] + ',disable'); continue
        line = f"monitor={d['name']},{r['mode']},{r['position']},{r['scale']}"
        for k in ('mirror', 'transform', 'vrr', 'bitdepth', 'cm', 'sdrbrightness', 'sdrsaturation'):
            if k in r: line += f',{k},{r[k]}'
        lines.append(line)
    return '\n'.join(lines) + '\n'

def locked():
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    f = LOCK.open('a')
    fcntl.flock(f, fcntl.LOCK_EX)
    return f

def verify(displays):
    current = {m['name']: m for m in live_monitors()}
    for d in displays:
        m = current.get(d['name'])
        if not m or bool(m['disabled']) == d['enabled']: return False
        if d['enabled'] and ((m['width'],m['height']) != (d['width'],d['height']) or
            (m['x'],m['y']) != (d['x'],d['y']) or abs(m['scale'] - d['scale']) > .001 or
            abs(m['refreshRate'] - d['refresh']) > .15 or m['transform'] != d['transform']): return False
    return True

def apply(displays, original_text, original_displays=None, timeout=25):
    issue = boxes_valid(displays)
    if issue: raise DisplayError(issue)
    if not CONFIG.exists(): raise DisplayError('No existe ~/.config/hypr/monitors.lua.')
    with locked():
        before = CONFIG.read_text()
        if before != original_text: raise DisplayError('La configuración cambió en otra aplicación. Pulsa Recargar antes de intentarlo otra vez.')
        actual = live_monitors()
        actual_names = {m['name'] for m in actual}
        if actual_names != {d['name'] for d in displays}: raise DisplayError('Las pantallas conectadas cambiaron. Pulsa Recargar.')
        if original_displays is not None and not verify(original_displays):
            raise DisplayError('La distribución cambió en otra aplicación. Pulsa Recargar.')
        after = render(before, displays)
        files = [(CONFIG, before, after)]
        if before.startswith('-- Fuente compartida de Pantallas, barras'):
            conf = CONFIG.parent / 'nwg-displays-monitors.conf'
            lua = CONFIG.parent / 'nwg-displays-monitors.lua'
            if conf.exists(): files.append((conf, conf.read_text(), compat_conf(displays)))
            if lua.exists(): files.append((lua, lua.read_text(), after))
        STATE.mkdir(parents=True, exist_ok=True)
        txpath = STATE / (uuid.uuid4().hex + '.json')
        tx = dict(deadline=time.time() + timeout, files=[dict(path=str(p), before=b, after_hash=digest(a)) for p,b,a in files])
        atomic(txpath, json.dumps(tx))
        # El vigilante es otro proceso: sobrevive al cierre inesperado de la interfaz.
        subprocess.Popen([sys.executable, '-m', 'pantallas.watchdog', str(txpath)],
                         start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for path, _, value in files: atomic(path, value)
            ctl('reload')
            errors = ctl('configerrors').strip()
            if errors: raise DisplayError('Hyprland informó un error: ' + errors)
            for _ in range(30):
                if verify(displays): return txpath
                time.sleep(.1)
            raise DisplayError('Hyprland no aplicó todos los cambios.')
        except Exception:
            for path, prior, _ in files: atomic(path, prior)
            ctl('reload')
            txpath.unlink(missing_ok=True)
            raise

def confirm(txpath):
    with locked():
        txpath.unlink(missing_ok=True)

def revert(txpath):
    with locked():
        if not txpath.exists(): return False
        tx = json.loads(txpath.read_text())
        # Si el proceso murió durante la escritura, acepta tanto archivos ya
        # escritos como archivos todavía intactos; nunca pisa cambios ajenos.
        for item in tx['files']:
            path = Path(item['path'])
            if not path.exists() or digest(path.read_text()) not in (item['after_hash'], digest(item['before'])):
                return False
        for item in tx['files']:
            atomic(Path(item['path']), item['before'])
        ctl('reload')
        txpath.unlink(missing_ok=True)
        return True
