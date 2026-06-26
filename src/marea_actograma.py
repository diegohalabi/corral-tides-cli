#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo Actograma Cronobiológico (30 Días)
Implementa la técnica "Double-Plotted Actogram" utilizando los datos de core.py.
"""
import os
import sys
import datetime
import plotext as plt
import re
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import locale

# Asegurar import de core.py
try:
    from core import load_local_tides
except ImportError:
    # Si se ejecuta directamente fuera del PYTHONPATH de src/
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from core import load_local_tides

try:
    locale.setlocale(locale.LC_TIME, 'es_CL.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    except locale.Error:
        pass

console = Console()

def generate_actogram():
    try:
        tides_raw = load_local_tides()
    except Exception as e:
        console.print(f"[bold red]Error al cargar datos:[/bold red] {e}")
        sys.exit(1)
    
    # Usamos timezone naive de forma consistente en todo el proyecto
    now = datetime.datetime.now().replace(second=0, microsecond=0)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = today_start + datetime.timedelta(days=31)
    
    # Filtrar mareas del rango de interés (próximos 30-31 días)
    tides = [t for t in tides_raw if today_start <= t['time'] <= end_date]
            
    if not tides:
        console.print("[bold red]Error:[/bold red] No hay datos en el rango requerido (próximos 30 días).")
        console.print("Por favor actualiza la base de datos desde el menú principal.")
        sys.exit(1)

    pleamares_x, pleamares_y = [], []
    bajamares_x, bajamares_y = [], []
    
    yticks_y = []
    yticks_labels = []
    
    for day_idx in range(30):
        current_day = today_start + datetime.timedelta(days=day_idx)
        next_day = current_day + datetime.timedelta(days=1)
        
        yticks_y.append(day_idx)
        yticks_labels.append(current_day.strftime("%b %d"))
        
        for t in tides:
            t_time = t['time']
            # Mitad Izquierda (0-24)
            if current_day <= t_time < next_day:
                hour_dec = t_time.hour + t_time.minute / 60.0
                if t['type'].lower() == 'pleamar':
                    pleamares_x.append(hour_dec)
                    pleamares_y.append(day_idx)
                elif t['type'].lower() == 'bajamar':
                    bajamares_x.append(hour_dec)
                    bajamares_y.append(day_idx)
            
            # Mitad Derecha (24-48)
            if next_day <= t_time < next_day + datetime.timedelta(days=1):
                hour_dec = 24.0 + t_time.hour + t_time.minute / 60.0
                if t['type'].lower() == 'pleamar':
                    pleamares_x.append(hour_dec)
                    pleamares_y.append(day_idx)
                elif t['type'].lower() == 'bajamar':
                    bajamares_x.append(hour_dec)
                    bajamares_y.append(day_idx)

    plt.clf()
    plt.theme('dark')
    plt.canvas_color('none')
    plt.axes_color('none')
    plt.ticks_color('white')

    plt.limit_size(False, False)
    term_width = console.width if console.width > 20 else 80
    plt.plotsize(term_width - 4, 33)

    for d in range(30):
        plt.plot([0, 48], [d, d], color="gray", marker=".")

    plt.plot([24, 24], [0, 29], color="yellow", marker=".")

    if pleamares_x:
        # Marcador propio ("o") para no confundirse con la grilla de puntos "."
        plt.scatter(pleamares_x, pleamares_y, color="cyan", marker="o")
        
    if bajamares_x:
        plt.scatter(bajamares_x, bajamares_y, color="red", marker="x")

    plt.yreverse(True)
    plt.yticks(yticks_y, yticks_labels)
    plt.xticks([i * 6 for i in range(9)], [f"{i*6}h" for i in range(9)])
    
    plt.xlim(0, 48)
    plt.ylim(-0.5, 29.5)
    plt.grid(False, False)

    plt.title("Actograma de Puntos Double-Plotted (30 Días)")
    plt.xlabel("Horas (0-24h: Día Base  |  24-48h: Día Siguiente)")
    
    ansi_plot = plt.build()
    ansi_plot = re.sub(r'\x1b\[48;5;\d+m', '', ansi_plot)
    
    panel = Panel(
        Text.from_ansi(ansi_plot), 
        title="[bold cyan]Actograma de Mareas[/bold cyan] | [cyan]o Pleamar[/cyan] | [red]x Bajamar[/red]",
        border_style="cyan"
    )
    console.print(panel)

if __name__ == "__main__":
    generate_actogram()
