# Corral Tides CLI

Una Terminal User Interface (TUI) extremadamente minimalista con estética hacker para visualizar, monitorear y analizar el comportamiento de las mareas en **Puerto Corral, Chile**.

Este proyecto se conecta en vivo de manera invisible con el servicio del SHOA, extrae los datos limpios en segundo plano y despliega proyecciones locales utilizando interpolación cosenoidal a tramos. Toda la arquitectura funciona *offline-first* apoyándose en una memoria caché automática para no abusar del servidor.

## 🌊 Características

- **Nowcast (3 Días)**: Monitoreo a corto plazo mediante un ploteo continuo con indicadores flotantes de las próximas bajamares.
- **Proyección Semanal (7 Días)**: Análisis extendido a 7 días y una tabla informativa formateada y codificada por colores.
- **Actograma Mensual (30 Días)**: Una potente herramienta inspirada en cronobiología (Double-Plotted Actogram) para trazar visualmente el corrimiento de la fase lunar a lo largo de 30 días, identificando el "drifting" (desfase) de pleamares y bajamares de manera totalmente orgánica.
- **Navegación Interactiva por Teclado**: Menú manejado íntegramente por flechas de dirección (`↑`, `↓`) con estética minimalista profunda.
- **Diseño Responsivo**: Auto-centrado y relajación geométrica adaptable a cualquier tamaño de terminal.

## ⚙️ Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/tu-usuario/nombre-del-repo.git
   cd nombre-del-repo
   ```

2. (Opcional pero recomendado) Crea un entorno virtual:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Instala las dependencias necesarias (`plotext`, `rich`, `requests`, `beautifulsoup4`):
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Uso

Ejecuta el menú principal. Si es la primera vez que lo corres, el programa contactará a SHOA y creará un archivo caché inteligente `~/.cache/mareas_corral.json`. 

```bash
./main.py
```

Utiliza las flechas del teclado y presiona `ENTER` para moverte a través del Nowcast, Proyecciones o actualizar los datos manualmente (el sistema se auto-actualiza solo si los datos cumplen 1 año de antigüedad).

## 🛠 Arquitectura

- `/src/marea_3d.py`: Motor principal e interpolación matemática.
- `/src/marea_7d.py`: Motor extendido de la proyección semanal.
- `/src/marea_actograma.py`: Motor de gráficos de dispersión/cronobiológicos.
- `/main.py`: Menú principal responsivo y captura interactiva de teclado a bajo nivel (`tty`, `termios`).
