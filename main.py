#!/usr/bin/env python3
"""
Módulo Principal de la CLI de Mareas (Tides Terminal UI)
Punto de entrada central refactorizado para importar directamente los subcomponentes.
"""
import os
import sys
import time
import datetime
import termios
import tty
import select
import locale
from rich.console import Console

# Agregar el directorio src al path para importaciones directas
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from core import CACHE_FILE, update_cache, load_local_tides

console = Console()

# Margen previo al agotamiento de datos para refrescar de forma proactiva
REFRESH_MARGIN = datetime.timedelta(days=7)

def get_key():
    """Captura una pulsación de tecla al vuelo sin requerir presionar ENTER."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        # Leemos directo del descriptor con os.read (sin buffer): así select() ve
        # los bytes restantes de las secuencias de escape. Con sys.stdin.read el
        # buffer interno de Python se tragaría '[A' y la flecha parecería un ESC.
        ch = os.read(fd, 1).decode('utf-8', 'ignore')
        if ch == '\x1b': # Secuencia de escape
            # Si no llegan más bytes de inmediato, es un ESC aislado (no una flecha):
            # evita bloquear esperando dos caracteres que nunca llegarán.
            if not select.select([fd], [], [], 0.05)[0]:
                return 'esc'
            ch2 = os.read(fd, 2).decode('utf-8', 'ignore')
            if ch2 == '[A': return 'up'
            if ch2 == '[B': return 'down'
            if ch2 == '[C': return 'right'
            if ch2 == '[D': return 'left'
            return 'esc'
        if ch in ('\r', '\n'): return 'enter'
        if ch == '\x03': return 'ctrl-c'
        if ch.lower() == 'q': return 'q'
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def check_auto_update():
    """Actualiza el caché si no existe o si sus datos ya no cubren la fecha actual.

    El SHOA solo publica unos meses de mareas, así que la frescura se mide por la
    cobertura real de los datos (no por la antigüedad del archivo): se actualiza si
    el caché está vacío, si 'ahora' quedó antes del primer registro, o si los datos
    se agotan dentro del margen REFRESH_MARGIN.
    """
    needs_update = False
    if not os.path.exists(CACHE_FILE):
        console.print("\n[bold cyan]❯[/bold cyan] [dim]No se encontró caché local. Iniciando primera descarga desde SHOA...[/dim]")
        needs_update = True
    else:
        try:
            tides = load_local_tides()
        except Exception:
            tides = []
        now = datetime.datetime.now()
        if not tides or now < tides[0]['time'] or now > tides[-1]['time'] - REFRESH_MARGIN:
            console.print("\n[bold cyan]❯[/bold cyan] [dim]Los datos en caché ya no cubren la fecha actual. Auto-actualizando desde SHOA...[/dim]")
            needs_update = True

    if needs_update:
        run_update(auto=True)

def _get_px():
    term_width = console.width
    return " " * max(0, (term_width - 45) // 2)

def run_update(auto=False):
    """Actualiza la base de datos descargando de SHOA directamente via imports."""
    px = _get_px()
    console.print("\n" + px + "[bold cyan]❯[/bold cyan] [dim]Conectando con servidor SHOA...[/dim]")
    try:
        update_cache(console)
        console.print("\n" + px + "[bold cyan]❯[/bold cyan] [bold white]Base de datos actualizada.[/bold white]")
        if auto:
            time.sleep(1)
        else:
            console.print("\n" + px + "[dim]Presiona cualquier tecla para continuar...[/dim]")
            get_key()
    except Exception as e:
        console.print(f"\n{px}[bold red]❯ Fallo crítico al actualizar la base de datos: {e}[/bold red]")
        if not auto:
            console.print("\n" + px + "[dim]Presiona cualquier tecla para continuar...[/dim]")
            get_key()

def run_tui_view(view_type):
    """Ejecuta una vista de TUI directamente importando el módulo correspondiente."""
    os.system("clear" if os.name == "posix" else "cls")
    try:
        if view_type == 3:
            import marea_3d
            marea_3d.main()
        elif view_type == 7:
            import marea_7d
            marea_7d.main()
        elif view_type == 'actograma':
            import marea_actograma
            marea_actograma.generate_actogram()
            
        px = _get_px()
        console.print("\n" + px + "[dim]Presiona cualquier tecla para volver...[/dim]")
        get_key()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        px = _get_px()
        console.print(f"\n{px}[bold red]Error al ejecutar vista: {e}[/bold red]")
        console.print("\n" + px + "[dim]Presiona cualquier tecla para volver...[/dim]")
        get_key()

def display_menu():
    """Muestra el menú principal iterativo con estética minimalista extrema."""
    options = [
        "Ver Nowcast (3 Días)",
        "Ver Proyección Semanal (7 Días)",
        "Ver Actograma Mensual (30 Días)",
        "Actualizar Base de Datos (SHOA)",
        "Salir del Sistema"
    ]
    selected_idx = 0
    
    ascii_art_lines = [
        "          [white]░[/][#ff0000]▄██▄[/][white]░[/]                       ",
        "        [#ff3300]▄██▀  ▀██▄[/]                     ",
        "      [#ff6600]▄██▀      ▀██▄[/]                   ",
        "     [#ff9900]▄█▀          ▀█▄[/]                  ",
        "   [#00ffaa]█[/][#555555]──────────────────[/#555555][#00ffaa]█[/][#555555]──────────────────[/#555555][#00ffaa]█[/]",
        "                        [#00aaff]▀█▄          ▄█▀[/]  ",
        "                         [#0066ff]▀██▄      ▄██▀[/]   ",
        "                           [#3300cc]▀██▄  ▄██▀[/]     ",
        "                             [white]░[/][#6600cc]▀██▀[/][white]░[/]       ",
        "",
        "   [bold white]M A R E A S   P U E R T O   C O R R A L[/bold white]"
    ]

    while True:
        os.system("clear" if os.name == "posix" else "cls")
        
        term_height = console.height
        term_width = console.width
        
        pad_y = max(0, (term_height - 20) // 2)
        pad_x_spaces = max(0, (term_width - 45) // 2)
        px = " " * pad_x_spaces
        
        for _ in range(pad_y):
            console.print()
            
        for line in ascii_art_lines:
            console.print(px + line)
            
        console.print()
        console.print()
        
        for i, opt in enumerate(options):
            if i == selected_idx:
                console.print(px + f"      [bold cyan]❯[/bold cyan] [bold white]{opt}[/bold white]")
            else:
                console.print(px + f"        [dim]{opt}[/dim]")
                
        console.print()
        console.print(px + "[dim](Usa ↑/↓ para mover y ENTER para seleccionar)[/dim]")
        
        for _ in range(pad_y):
            console.print()
            
        key = get_key()
        
        if key == 'up':
            selected_idx = (selected_idx - 1) % len(options)
        elif key == 'down':
            selected_idx = (selected_idx + 1) % len(options)
        elif key == 'enter':
            if selected_idx == 0:
                run_tui_view(3)
            elif selected_idx == 1:
                run_tui_view(7)
            elif selected_idx == 2:
                run_tui_view('actograma')
            elif selected_idx == 3:
                run_update(auto=False)
            elif selected_idx == 4:
                os.system("clear" if os.name == "posix" else "cls")
                console.print("[dim]Sesión finalizada. Usuario salió de la aplicación.[/dim]\n")
                sys.exit(0)
        elif key in ('ctrl-c', 'q', 'esc'):
            os.system("clear" if os.name == "posix" else "cls")
            console.print("[dim]Sesión finalizada. Usuario salió de la aplicación.[/dim]\n")
            sys.exit(0)

def main():
    try:
        locale.setlocale(locale.LC_TIME, 'es_CL.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
        except locale.Error:
            pass
            
    check_auto_update()
    display_menu()

if __name__ == "__main__":
    main()
