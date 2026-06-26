#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo Nowcast (Proyección a 3 Días)
Utiliza la lógica centralizada en core.py para renderizar el panel.
"""

import argparse
from rich.console import Console
from core import render_tide_projections, update_cache

def main():
    parser = argparse.ArgumentParser(description="TUI offline para monitorear mareas en Corral, Chile (3 días).")
    parser.add_argument('--update', action='store_true', help="Actualiza la caché local desde el sitio de SHOA y finaliza.")
    args = parser.parse_args()
    
    console = Console()
    
    if args.update:
        try:
            update_cache(console)
        except Exception as e:
            console.print(f"[bold red]Error al actualizar la base de datos:[/bold red] {e}")
        return
        
    render_tide_projections(days=3, console=console)

if __name__ == "__main__":
    main()
