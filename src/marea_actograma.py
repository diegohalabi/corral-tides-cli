#!/usr/bin/env python3
import os
import sys
import json
import datetime
import plotext as plt
import re
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import locale

try:
    locale.setlocale(locale.LC_TIME, 'es_CL.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    except locale.Error:
        pass

console = Console()

CACHE_FILE = os.path.expanduser("~/.cache/mareas_corral.json")

def load_data():
    if not os.path.exists(CACHE_FILE):
        console.print(f"[bold red]Error:[/bold red] No se encontró el caché en {CACHE_FILE}. Ejecuta primero mareas_corral.py --update")
        sys.exit(1)
        
    with open(CACHE_FILE, 'r') as f:
        data = json.load(f)
        
    if isinstance(data, list):
        tides_raw = data
    else:
        tides_raw = data.get('tides', [])
        
    if not tides_raw:
        console.print("[bold red]Error:[/bold red] El caché está vacío o corrupto.")
        sys.exit(1)
        
    return tides_raw

def generate_actogram():
    tides_raw = load_data()
    
    now = datetime.datetime.now().astimezone()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    end_date = today_start + datetime.timedelta(days=31)
    
    tides = []
    for t in tides_raw:
        try:
            dt = datetime.datetime.fromisoformat(t['time'])
        except ValueError:
            dt = datetime.datetime.strptime(t['time'], "%Y-%m-%dT%H:%M:%S")
            
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=now.tzinfo)
            
        if today_start <= dt <= end_date:
            tides.append({
                'time': dt,
                'type': t.get('type', 'Unknown'),
                'height': float(t.get('height', 0))
            })
            
    if not tides:
        console.print("[bold red]Error:[/bold red] No hay datos en el rango requerido.")
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

    # Desactivamos el límite de tamaño interno para forzar una altura matemática exacta
    plt.limit_size(False, False)
    term_width = console.width if console.width > 20 else 80
    # 33 es la altura matemática exacta en plotext para renderizar 30 líneas (1 por día) sin saltos
    plt.plotsize(term_width - 4, 33)

    # 1. Dibujar líneas punteadas grises horizontales de fondo por cada día.
    # Esto asegura también matemáticamente a plotext que existen todos los puntos Y,
    # forzando un espaciado vertical absolutamente homogéneo.
    for d in range(30):
        plt.plot([0, 48], [d, d], color="gray", marker=".")

    # 2. Línea punteada divisoria en el centro (24h)
    plt.plot([24, 24], [0, 29], color="yellow", marker=".")

    # 3. Dibujar marcadores discretos para Pleamares (sin leyenda interna para no superponer)
    if pleamares_x:
        plt.scatter(pleamares_x, pleamares_y, color="cyan", marker=".")
        
    # 4. Dibujar marcadores grandes y fuertes para Bajamares (sin leyenda interna)
    if bajamares_x:
        plt.scatter(bajamares_x, bajamares_y, color="red", marker="x")

    plt.yreverse(True)
    plt.yticks(yticks_y, yticks_labels)
    plt.xticks([i * 6 for i in range(9)], [f"{i*6}h" for i in range(9)])
    
    # Fijamos los límites para que los 30 días tengan su espacio asegurado
    plt.xlim(0, 48)
    plt.ylim(-0.5, 29.5)
    plt.grid(False, False)

    plt.title("Actograma de Puntos Double-Plotted (30 Días)")
    plt.xlabel("Horas (0-24h: Día Base  |  24-48h: Día Siguiente)")
    
    ansi_plot = plt.build()
    
    # Limpieza estricta de fondos ANSI para transparencia
    ansi_plot = re.sub(r'\x1b\[48;5;\d+m', '', ansi_plot)
    
    # Movemos la leyenda al marco exterior del panel para que jamás ensucie los datos
    panel = Panel(
        Text.from_ansi(ansi_plot), 
        title="[bold cyan]Actograma de Mareas[/bold cyan] | [cyan]· Pleamar[/cyan] | [red]x Bajamar[/red]", 
        border_style="cyan"
    )
    console.print(panel)

if __name__ == "__main__":
    generate_actogram()
