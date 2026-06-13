#!/usr/bin/env python3
"""
Módulo Principal de la CLI de Mareas (Tides Terminal UI)
Este script actúa como el punto de entrada central para la aplicación. 
Implementa una interfaz gráfica de terminal interactiva (TUI) extremadamente minimalista,
gestionando la navegación por teclado a bajo nivel para ofrecer una experiencia similar a
los modernos frameworks CLI. También orquesta actualizaciones del caché de datos.
"""
import os
import sys
import time
import subprocess
import termios
import tty
from rich.console import Console
import locale

console = Console()

CACHE_FILE = os.path.expanduser("~/.cache/mareas_corral.json")
# Segundos en un año (365 días)
ONE_YEAR_SEC = 365 * 24 * 3600

def get_key():
    """Captura una pulsación de tecla al vuelo sin requerir presionar ENTER."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
        if ch == '\x1b': # Secuencia de escape
            ch2 = sys.stdin.read(2)
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
    """Verifica si el caché no existe o tiene más de 1 año de antigüedad y lo actualiza."""
    needs_update = False
    if not os.path.exists(CACHE_FILE):
        console.print("\n[bold cyan]❯[/bold cyan] [dim]No se encontró caché local. Iniciando primera descarga desde SHOA...[/dim]")
        needs_update = True
    else:
        mtime = os.path.getmtime(CACHE_FILE)
        if time.time() - mtime > ONE_YEAR_SEC:
            console.print("\n[bold cyan]❯[/bold cyan] [dim]El caché de mareas tiene más de un año de antigüedad. Auto-actualizando...[/dim]")
            needs_update = True
            
    if needs_update:
        run_update(auto=True)

def _get_px():
    term_width = console.width
    return " " * max(0, (term_width - 45) // 2)

def run_update(auto=False):
    """Ejecuta el script subyacente para descargar la data."""
    px = _get_px()
    console.print("\n" + px + "[bold cyan]❯[/bold cyan] [dim]Conectando con servidor SHOA...[/dim]")
    script_path = os.path.join(os.path.dirname(__file__), "src", "marea_3d.py")
    try:
        subprocess.run([sys.executable, script_path, "--update"], check=True)
        console.print("\n" + px + "[bold cyan]❯[/bold cyan] [bold white]Base de datos actualizada.[/bold white]")
        if auto:
            time.sleep(1)
        else:
            console.print("\n" + px + "[dim]Presiona cualquier tecla para continuar...[/dim]")
            get_key()
    except subprocess.CalledProcessError:
        console.print("\n" + px + "[bold red]❯ Fallo crítico al actualizar la base de datos.[/bold red]")
        if not auto:
            console.print("\n" + px + "[dim]Presiona cualquier tecla para continuar...[/dim]")
            get_key()

def run_script(script_name):
    """Ejecuta un script del directorio src/ limpiando la pantalla antes."""
    script_path = os.path.join(os.path.dirname(__file__), "src", script_name)
    try:
        os.system("clear" if os.name == "posix" else "cls")
        subprocess.run([sys.executable, script_path])
        px = _get_px()
        console.print("\n" + px + "[dim]Presiona cualquier tecla para volver...[/dim]")
        get_key()
    except KeyboardInterrupt:
        pass

def display_menu():
    """Muestra el menú principal iterativo con estética minimalista extrema tipo Claude Code."""
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
        
        # Relajación vertical adaptada al nuevo logo
        pad_y = max(0, (term_height - 20) // 2)
        # Relajación horizontal asumiendo un ancho de bloque de 45 caracteres
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
                # Minimalismo puro: Chevron cian y texto blanco bold desplazado
                console.print(px + f"      [bold cyan]❯[/bold cyan] [bold white]{opt}[/bold white]")
            else:
                # Opciones inactivas tenues
                console.print(px + f"        [dim]{opt}[/dim]")
                
        console.print()
        console.print(px + "[dim](Usa ↑/↓ para mover y ENTER para seleccionar)[/dim]")
        
        for _ in range(pad_y):
            console.print()
            
        # Leer tecla
        key = get_key()
        
        if key == 'up':
            selected_idx = (selected_idx - 1) % len(options)
        elif key == 'down':
            selected_idx = (selected_idx + 1) % len(options)
        elif key == 'enter':
            if selected_idx == 0:
                run_script("marea_3d.py")
            elif selected_idx == 1:
                run_script("marea_7d.py")
            elif selected_idx == 2:
                run_script("marea_actograma.py")
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
            
    # Lógica de auto-update inteligente
    check_auto_update()
    
    # Loop de Menú
    display_menu()

if __name__ == "__main__":
    main()
