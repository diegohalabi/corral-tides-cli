# -*- coding: utf-8 -*-
"""
Módulo central (core.py) con lógica compartida para Corral Tides CLI.
Contiene la configuración de caché, parsing de SHOA, interpolación cosenoidal y utilidades de renderizado.
"""
import os
import sys
import json
import math
import datetime
import re
import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
import plotext as plt

CACHE_FILE = os.path.expanduser("~/.cache/mareas_corral.json")
SHOA_URL = "https://www.shoa.cl/php/mareas.php?local=corral"
WEEKDAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

def fetch_shoa_data():
    """Realiza un GET a la página de mareas del SHOA con el puerto Corral."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1"
    }
    response = requests.get(SHOA_URL, headers=headers, timeout=15)
    response.raise_for_status()
    return response.text

def parse_html(html):
    """Extrae todas las mareas de Corral del HTML del SHOA."""
    soup = BeautifulSoup(html, 'html.parser')
    tides = []
    
    tables = soup.find_all('table')
    if not tables:
        raise ValueError("No se encontraron tablas de mareas en el HTML del SHOA.")
        
    for table in tables:
        rows = table.find_all('tr')
        if not rows:
            continue
        headers = [th.get_text(strip=True) for th in rows[0].find_all(['th', 'td'])]
        if not headers or 'Fecha' not in headers[0]:
            continue
            
        for row in rows[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
            if not cells or len(cells) < 3:
                continue
                
            fecha_str = cells[0]
            parts = fecha_str.split('/')
            if len(parts) != 3:
                continue
                
            for idx in range(1, len(cells) - 1, 2):
                t_str = cells[idx]
                h_str = cells[idx+1]
                if not t_str or not h_str:
                    continue
                    
                if not re.match(r'^\d{2}:\d{2}$', t_str):
                    continue
                    
                match = re.match(r'^([\d\.,]+)\s*([PBpb])?$', h_str)
                if not match:
                    continue
                    
                height_val = float(match.group(1).replace(',', '.'))
                tide_type_raw = match.group(2)
                if tide_type_raw:
                    tide_type = 'Pleamar' if tide_type_raw.upper() == 'P' else 'Bajamar'
                else:
                    tide_type = 'Desconocido'
                    
                dt_str = f"{fecha_str} {t_str}"
                try:
                    dt = datetime.datetime.strptime(dt_str, "%d/%m/%Y %H:%M")
                    tides.append({
                        'time': dt,
                        'height': height_val,
                        'type': tide_type
                    })
                except ValueError as ve:
                    print(f"Error parsing date {dt_str}: {ve}", file=sys.stderr)
                    
    seen = set()
    unique_tides = []
    for t in tides:
        if t['time'] not in seen:
            seen.add(t['time'])
            unique_tides.append(t)
            
    if not unique_tides:
        raise ValueError("No se pudo extraer ningún dato de marea válido del HTML.")
        
    return sorted(unique_tides, key=lambda x: x['time'])

def load_local_tides():
    """Carga mareas estrictamente desde el archivo caché local."""
    if not os.path.exists(CACHE_FILE):
        raise FileNotFoundError(
            f"No se encontró el archivo de caché local en: {CACHE_FILE}\n"
            "Por favor, ejecuta una actualización de base de datos desde el menú principal para descargar los datos por primera vez."
        )
        
    with open(CACHE_FILE, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            raise ValueError(f"El archivo de caché local {CACHE_FILE} no es un JSON válido o está corrupto.")
            
        tides = []
        tides_raw = data if isinstance(data, list) else data.get('tides', [])
        for d in tides_raw:
            try:
                dt = datetime.datetime.fromisoformat(d['time'])
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)
                tides.append({
                    'time': dt,
                    'height': float(d['height']),
                    'type': d.get('type', 'Desconocido')
                })
            except (ValueError, KeyError, TypeError) as e:
                print(f"Ignorando registro inválido en caché: {d}. Error: {e}", file=sys.stderr)
        return sorted(tides, key=lambda x: x['time'])

def update_cache(console=None):
    """Descarga los datos del SHOA y actualiza la caché completa."""
    if console is None:
        console = Console()
    console.print("[yellow]Conectándose a la web del SHOA para descargar mareas de Corral...[/yellow]")
    # Las excepciones se propagan al llamador, que es responsable de mostrarlas
    # una sola vez (evita duplicar el mensaje de error).
    html = fetch_shoa_data()
    data = parse_html(html)

    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        serializable = [{
            'time': d['time'].isoformat(),
            'height': d['height'],
            'type': d['type']
        } for d in data]
        json.dump(serializable, f, indent=2)

    console.print(f"[bold green]¡Éxito![/bold green] Se descargaron y guardaron [cyan]{len(data)}[/cyan] registros de mareas en la caché.")

def interpolate_tide(t_current, tides_sorted):
    """
    Interpola la altura de la marea en t_current usando función cosenoidal a tramos.
    tides_sorted DEBE estar ordenado por fecha.
    Retorna: (altura, derivada (m/h), estado, datetime_proxima_marea, tipo_proxima)
    """
    if not tides_sorted:
        return None, 0, "Sin datos", None, "Desconocido"
        
    if t_current < tides_sorted[0]['time']:
        return None, 0, "Fuera de rango (pasado)", None, "Desconocido"
    if t_current > tides_sorted[-1]['time']:
        return None, 0, "Fuera de rango (futuro)", None, "Desconocido"
        
    import bisect
    times = [t['time'] for t in tides_sorted]
    idx = bisect.bisect_right(times, t_current) - 1

    if idx >= len(tides_sorted) - 1:
        # t_current coincide con el último registro: devolver ese punto exacto
        # en vez de extrapolar más allá del rango con phase > pi.
        last = tides_sorted[-1]
        return last['height'], 0.0, "Estático", last['time'], last.get('type', 'Desconocido')
        
    t0 = tides_sorted[idx]['time']
    t1 = tides_sorted[idx+1]['time']
    h0 = tides_sorted[idx]['height']
    h1 = tides_sorted[idx+1]['height']
    tipo_next = tides_sorted[idx+1].get('type', 'Desconocido')
    
    dt = (t1 - t0).total_seconds() / 3600.0
    if dt == 0:
        return h0, 0, "Estático", t1, tipo_next
        
    elapsed = (t_current - t0).total_seconds() / 3600.0
    phase = math.pi * (elapsed / dt)
    
    h_current = h0 + (h1 - h0) / 2.0 * (1 - math.cos(phase))
    rate = (h1 - h0) / 2.0 * (math.pi / dt) * math.sin(phase)
    state = "Llenando" if rate > 0 else "Vaciando"
    
    return h_current, rate, state, t1, tipo_next

def render_tide_projections(days, console=None):
    """Genera la TUI para un número específico de días (3 o 7) sin duplicación."""
    if console is None:
        console = Console()
        
    try:
        tides = load_local_tides()
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return
        
    now = datetime.datetime.now().replace(second=0, microsecond=0)
    if now.tzinfo is not None:
        now = now.replace(tzinfo=None)
        
    h_now, rate, state, t_next, tipo_next = interpolate_tide(now, tides)
    
    if h_now is None:
        console.print("[bold red]Error:[/bold red] El momento actual está fuera del rango de datos disponibles en caché.")
        console.print("Por favor actualiza la base de datos desde el menú principal.")
        return
        
    if t_next:
        time_diff = t_next - now
        hours, remainder = divmod(time_diff.total_seconds(), 3600)
        minutes = remainder // 60
        faltan_str = f"Faltan {int(hours)}h {int(minutes)}m para {tipo_next}"
    else:
        faltan_str = "Siguiente marea desconocida"
        
    rate_str = f"{rate:+.2f}m/h"
    nowcast_text = (
        f"AHORA: [bold cyan]{h_now:.2f}m[/bold cyan] | "
        f"[bold green]{state}[/bold green] ({rate_str}) | {faltan_str}\n"
        f"[dim]Modo Offline (Caché local)[/dim]"
    )
    
    panel_top = Panel(nowcast_text, title="[bold yellow]Nowcast - Puerto Corral[/bold yellow]", border_style="cyan")
    
    plot_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    plot_end = plot_start + datetime.timedelta(days=days)
    
    x_timestamps = []
    y_heights = []
    
    current_plot = plot_start
    while current_plot <= plot_end:
        h, _, _, _, _ = interpolate_tide(current_plot, tides)
        if h is not None:
            x_timestamps.append(current_plot.timestamp())
            y_heights.append(h)
        current_plot += datetime.timedelta(minutes=15)
        
    if not x_timestamps:
        console.print(f"[bold red]Error:[/bold red] No hay suficientes datos en la caché para graficar los próximos {days} días.")
        return
        
    start_hour = (plot_start.hour // 12) * 12
    current_tick = plot_start.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    
    ticks_x = []
    labels_x = []
    
    while current_tick <= plot_end:
        ts = current_tick.timestamp()
        if min(x_timestamps) <= ts <= max(x_timestamps):
            ticks_x.append(ts)
            day_name = WEEKDAYS[current_tick.weekday()]
            labels_x.append(f"{day_name} {current_tick.day} - {current_tick.strftime('%H:%M')}")
        current_tick += datetime.timedelta(hours=12)
        
    plt.clf()
    plt.theme('dark')
    plt.canvas_color('none')
    plt.axes_color('none')
    plt.ticks_color('white')
    
    term_width = console.width if console.width > 20 else 80
    plt.plotsize(term_width - 4, 15)
    
    plt.plot(x_timestamps, y_heights, color="cyan", label="Marea")
    plt.scatter([now.timestamp()], [h_now], color="red", marker="x", label="Actual")
    
    if y_heights:
        y_min, y_max = min(y_heights), max(y_heights)
        y_line = [y_min + i * (y_max - y_min) / 40.0 for i in range(41)]
        day_tick = plot_start
        while day_tick <= plot_end:
            ts = day_tick.timestamp()
            plt.plot([ts] * len(y_line), y_line, marker=".", color="gray")
            day_tick += datetime.timedelta(days=1)
            
    next_low_tide = None
    for t_info in tides:
        if t_info['time'] > now and t_info['type'] == 'Bajamar':
            next_low_tide = t_info
            break
            
    if next_low_tide:
        lbl_time = next_low_tide['time'].strftime('%H:%M')
        ts_low = next_low_tide['time'].timestamp()
        plt.text(lbl_time, ts_low, next_low_tide['height'] + 0.25, color="gray", alignment="center")
    
    plt.xticks(ticks_x, labels_x)
    plt.title(f"Proyección a {days} días (Curva interpolada)")
    plt.xlabel("Fecha / Hora")
    plt.ylabel("Altura (m)")
    
    ansi_plot = plt.build()
    ansi_plot = re.sub(r'\x1b\[48;5;\d+m', '', ansi_plot)
    
    panel_mid = Panel(Text.from_ansi(ansi_plot), title="Visualización de Marea", border_style="cyan")
    
    table = Table(title=f"Mareas Oficiales SHOA (Próximos {days} días)", expand=True, border_style="cyan")
    table.add_column("Día", justify="center", style="cyan")
    table.add_column("Hora", justify="center", style="green")
    table.add_column("Altura (m)", justify="center", style="yellow")
    table.add_column("Tipo", justify="center", style="magenta")
    
    for t_info in tides:
        dt = t_info['time']
        if now <= dt <= plot_end:
            day_name = WEEKDAYS[dt.weekday()]
            table.add_row(
                f"{day_name} {dt.strftime('%d-%m-%Y')}",
                dt.strftime("%H:%M"),
                f"{t_info['height']:.2f}",
                t_info.get('type', 'Desconocido')
            )
            
    panel_bot = Panel(table, border_style="cyan")
    
    console.print(panel_top)
    console.print(panel_mid)
    console.print(panel_bot)
