# Omarchy Monitors

[English](README.md)

Gestor visual de pantallas para Hyprland y Omarchy. Es un proyecto comunitario independiente; no está afiliado al proyecto Omarchy.

Arrastra los monitores para ordenar tu escritorio, identifica cada pantalla física y ajusta resolución, frecuencia y escala. Los bordes se acoplan al acercarlos y la aplicación avisa cuando una distribución se superpone o deja pantallas aisladas. La interfaz está disponible en inglés y español; usa las banderas pixeladas de la parte superior para cambiar de idioma. El idioma predeterminado es inglés.

En ventanas de poca altura, el mapa y el panel de configuración se desplazan de forma independiente para mantener accesibles sus controles.

La opción **Nombres siempre visibles** muestra en la esquina inferior derecha de cada monitor encendido un número estable, el conector y el modelo. Las etiquetas no capturan clics y siguen funcionando al cerrar la aplicación; se pueden desactivar desde el mismo control. El número se conserva al desconectar y reconectar cada salida.

Al seleccionar un monitor en la aplicación, su etiqueta física se resalta con el color de acento del tema. Al cerrar la ventana, las etiquetas recuperan su aspecto normal.

Los cambios se aplican con un temporizador de confirmación. Si no confirmas en 25 segundos, un proceso independiente restaura la configuración anterior incluso si la ventana se cierra. Si detecta que otro programa cambió los archivos, evita sobrescribirlos y conserva datos para recuperación en `~/.local/state/pantallas/`.

## Instalación

Requiere Linux con **Hyprland**, configuración Lua de monitores de Omarchy, Python 3.11 o posterior, PyGObject, GTK 3, Pycairo, gtk-layer-shell y fontconfig. En Arch Linux / Omarchy los paquetes correspondientes son `python`, `python-gobject`, `python-cairo`, `gtk3`, `gtk-layer-shell` y `fontconfig`.

```sh
git clone https://github.com/weedoozas/omarchy-monitors.git
cd omarchy-monitors
./install.sh
```

Busca **Omarchy Monitors** en el lanzador o ejecuta `~/.local/bin/omarchy-monitors`. La instalación es para el usuario actual y no requiere permisos de administrador. La tipografía Pixelify Sans se instala en el directorio de fuentes del usuario.

## Cómo se guarda

La aplicación edita reglas explícitas `hl.monitor` en `~/.config/hypr/monitors.lua`, conservando el resto del archivo y la regla general de Omarchy. Rechaza reglas complejas que no pueda interpretar de manera segura y se niega a aplicar si el archivo o los monitores cambiaron desde la última recarga. Aplica y verifica los cambios con `hyprctl`.

Actualmente no edita distribuciones en modo espejo ni configuraciones antiguas `monitors.conf`. En configuraciones Lua personalizadas con expresiones en las reglas individuales, ajusta las reglas manualmente. La identificación visual requiere gtk-layer-shell y una correspondencia única entre el monitor de GTK y Hyprland. El funcionamiento depende de los modos que anuncie cada monitor.

## Desarrollo

```sh
python3 -m unittest discover -s tests -v
python3 -m pantallas
```

Código bajo licencia [MIT](LICENSE). La fuente [Pixelify Sans](https://github.com/google/fonts/tree/main/ofl/pixelifysans) se distribuye bajo su propia [SIL Open Font License](data/fonts/OFL.txt). El logotipo fue creado con generación de imágenes para este proyecto.
