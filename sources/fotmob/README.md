# Módulo FotMob: Extracción de Big Data y ETL

Este módulo es el motor principal del proyecto. Se encarga de conectarse a la API no documentada de FotMob para descargar el detalle completo de las ligas y partidos del fútbol argentino, almacenarlos localmente como un *Data Lake* (JSON) y luego procesarlos e inyectarlos en la base de datos PostgreSQL.

## Archivos del Módulo

* `fotmob_scraper.py`: Script principal de extracción. Descarga los datos mediante un sistema de "goteo" para no saturar la API y guarda el progreso en `checkpoint.json`.
* `fotmob_updater.py`: Script auxiliar para forzar la actualización de un torneo específico, ideal para partidos en curso o recientes.
* `inyect_fotmob.py`: El script ETL. Lee los JSON descargados y distribuye la información en las tablas relacionales (`partidos`, `jugadores`, `stats_jugador_partido`, `tiros`, `eventos`, etc.), manejando la ausencia de datos con programación defensiva.
* `fotmob_config.py`: Diccionario de configuración con los IDs internos que usa FotMob para cada competición.
* `auditor.py`: Utilidad para contar y verificar la cantidad de archivos descargados en el Data Lake.

## Evasión de Turnstile (Anti-Bot)

FotMob utiliza protección de Cloudflare. Para evadirla, los scrapers de este módulo no usan solicitudes HTTP tradicionales, sino **Nodriver**, que levanta una instancia de Google Chrome indetectable.

### Primer uso y Generación de Sesión:
1. Asegurate de crear una carpeta vacía llamada `chrome_profile` en la raíz del proyecto.
2. Ejecutá `python fotmob_scraper.py`.
3. Si el script se detiene indicando un bloqueo, ve a la ventana de Chrome que se abrió, resuelve el Captcha humano y presiona `ENTER` en tu consola.
4. Las cookies de validación quedarán guardadas en tu perfil local para futuras ejecuciones silenciosas.

## Uso del ETL

Una vez que los JSONs estén descargados en `/data/fotmob/`:
```bash
python inyect_fotmob.py