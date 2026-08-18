# Módulo FotMob: Extracción de Big Data y ETL

Este módulo es el motor principal del proyecto. Se encarga de conectarse a la API no documentada de FotMob para descargar el detalle completo de las ligas y partidos del fútbol argentino, almacenarlos localmente como un *Data Lake* (JSON) y luego procesarlos e inyectarlos en la base de datos PostgreSQL.

## Archivos del Módulo

* `fotmob_scraper.py`: Script principal de extracción. Descarga los datos mediante un sistema de "goteo" para no saturar la API y guarda el progreso en `checkpoint.json`.
* `fotmob_updater.py`: Script auxiliar para forzar la actualización de un torneo específico, ideal para partidos en curso o recientes.
* `inyect_fotmob.py`: El script ETL. Lee los JSON descargados y distribuye la información en las tablas relacionales (`partidos`, `jugadores`, `stats_jugador_partido`, `tiros`, `eventos`, etc.), manejando la ausencia de datos con programación defensiva.
* `fotmob_config.py`: Diccionario de configuración con los IDs internos que usa FotMob para cada competición.
* `auditor.py`: Utilidad para contar y verificar la cantidad de archivos descargados en el Data Lake.

## Desafíos Técnicos Resueltos

### 1. Evasión de Sistemas Anti-Bot (Cloudflare Turnstile)
Las APIs deportivas modernas bloquean peticiones automatizadas estándar (como la librería `requests`). 
Este proyecto utiliza **Nodriver** para automatizar un navegador Chrome indetectable. El script genera un perfil de usuario local (`chrome_profile`) que guarda las cookies y tokens de sesión (clearance), permitiendo ejecuciones subsiguientes 100% silenciosas y automáticas.

### 2. Manejo de Datos Asimétricos (Programación Defensiva)
Los *payloads* de las APIs varían drásticamente dependiendo de la relevancia del partido (ej. un partido de Primera División incluye *Expected Goals*, Mapas de Tiros y Alineaciones, mientras que un partido del Ascenso no). Los scripts ETL utilizan extracción segura para parsear estructuras anidadas sin romper la ejecución ante valores nulos.

### 3. Inserción Idempotente en PostgreSQL
Para mantener la integridad de la base de datos al ejecutar los scripts múltiples veces, la base de datos emplea restricciones `UNIQUE` y los scripts de Python utilizan cláusulas `ON CONFLICT DO UPDATE` u `ON CONFLICT DO NOTHING`. Esto garantiza que los datos se actualicen si hay cambios (ej. el resultado de un partido en curso) sin generar registros duplicados.

### 4. Preservación del "Data Lake"
La columna `metadata` (tipo `JSONB`) en la base de datos relacional almacena el bloque de estadísticas puras de los equipos. Esto asegura que si en el futuro se requiere analizar una métrica no contemplada en el esquema original (ej. "posesión de balón"), no sea necesario volver a consultar la API externa.

### Primer uso y Generación de Sesión:

1. **Configuración de la Base de Datos:** Antes de ejecutar los scripts, abre los archivos `inyect_footballdata.py` y `check_names.py` y reemplaza el string de la variable `DB_URL` con las credenciales de tu servidor PostgreSQL local:
   ```python
   # Ejemplo de configuración en el código:
   DB_URL = "postgresql://usuario:contraseña@localhost:5432/nombre_db"
2. Asegurate de crear una carpeta vacía llamada `chrome_profile` en la raíz del proyecto.
3. Ejecutá `python fotmob_scraper.py`.
4. Si el script se detiene indicando un bloqueo, ve a la ventana de Chrome que se abrió, resuelve el Captcha humano y presiona `ENTER` en tu consola.
5. Las cookies de validación quedarán guardadas en tu perfil local para futuras ejecuciones silenciosas.

## Uso del ETL

Una vez que los JSONs estén descargados en `/data/fotmob/`:
```bash
python inyect_fotmob.py
```

El script guarda su estado de descarga en /data/fotmob/checkpoint.json. Si la ejecución se interrumpe, vuelve a correr el comando; el script leerá el checkpoint y se reanudará exactamente en el último partido descargado. Si deseas forzar una descarga desde cero, simplemente elimina este archivo.

## Actualización de Torneos en Curso (`fotmob_updater.py`)
Si estás siguiendo una liga que se está jugando actualmente, no necesitas correr el scraper principal completo. Puedes usar el actualizador específico:

1. Abre el archivo `sources/fotmob/fotmob_updater.py`.
2. Modifica las variables al final del script para apuntar al torneo exacto (ej. `LIGA_OBJETIVO = "112"` y `ANIO_OBJETIVO = "2026"`).
3. Ejecuta el actualizador:
   ```bash
   python sources/fotmob/fotmob_updater.py

El script leerá el listado actual de partidos de esa liga y descargará únicamente los JSONs de los encuentros que falten en  local, saltando los que ya existen para ahorrar ancho de banda y tiempo.