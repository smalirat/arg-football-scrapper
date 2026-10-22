# Módulo Football-Data.co.uk: Integración de Cuotas (Odds)

Este módulo enriquece la base existente con las cuotas de apuestas (Odds) históricas de primera división, a partir del CSV de *Football-Data.co.uk*. No crea partidos: solo agrega las cuotas a partidos que ya están en la base, cargados desde Kaggle o FotMob.

## Archivos del Módulo

* `inyect_footballdata.py`: Script ETL principal. Cruza cada fila del CSV con su partido en la base y agrega las cuotas promedio y de Pinnacle a la columna `metadata` (JSONB).
* `check_names.py`: Script de auditoría. Verifica que todos los equipos del CSV estén mapeados y que sus IDs existan en la tabla `equipos`.
* `configs/config_footballdatauk.py`: Contiene `MAPEO_EQUIPOS`, que traduce los nombres del CSV (ej. *Argentinos Jrs*) a los IDs de la base, y las ediciones de primera contra las que se cruza.

## Desafío Técnico: Matchmaking de Entidades

A diferencia de las APIs que proveen IDs únicos, los CSVs de apuestas operan mediante texto plano. Además, la base tiene partidos de dos fuentes, con IDs de equipo distintos:

| Período | Fuente de los partidos | IDs de equipo | ¿Tiene fecha? |
|---|---|---|---|
| hasta 2023 | Kaggle | IDs de Kaggle (ej. Belgrano = 16) | No |
| desde 2024 | FotMob | IDs de FotMob (ej. Belgrano = 10092) | Sí |

El cruce funciona así:
1. **Traducción de Nombres:** `MAPEO_EQUIPOS` le asigna a cada equipo sus dos IDs (`kaggle` y `fotmob`), así el mismo nombre del CSV encuentra partidos de cualquiera de las dos fuentes.
2. **Edición por Temporada:** Se buscan los partidos de esa temporada (`Season` del CSV = `temporada` de la edición) entre las ediciones de primera: *Liga Profesional* y *Copa de la Liga Profesional*, con sus etapas y playoffs.
3. **Triangulación:** El partido tiene que coincidir en local, visitante y resultado exacto (`HG` y `AG`). Si el partido de la base tiene fecha (FotMob), la del CSV puede diferir como mucho un día (el CSV usa hora de Reino Unido y la base UTC).
4. **Solo cruces únicos:** Si no hay un único partido que cumpla todo, la fila no se carga y queda registrada con su motivo.

Las cuotas se **agregan** a la `metadata` existente, sin reemplazarla: no se pierden las estadísticas que FotMob guarda en esa misma columna. Correr el script varias veces no duplica nada.

### Filas que no se cargan

Se registran en `auditoria_completa.log` con uno de estos motivos:

| Motivo | Significa |
|---|---|
| `SIN_MAPEO` | Un equipo del CSV no está en `MAPEO_EQUIPOS` |
| `SIN_PARTIDO` | Ese cruce no existe en la base para esa temporada (por ejemplo, temporadas que todavía no se cargaron) |
| `DISCREPANCIA_GOLES` | El cruce existe, pero con otro resultado |
| `FECHA_DISTINTA` | Coinciden equipos y resultado, pero la fecha difiere en más de un día |
| `AMBIGUO` | Hay más de un partido posible, típico en temporadas de Kaggle (sin fecha) donde el mismo cruce y resultado se dio en la Liga y en la Copa de la Liga |
| `DUPLICADO` | Dos filas del CSV caen en el mismo partido; no se carga ninguna |

## Instrucciones de Uso

1. Asegúrate de tener el dataset histórico en `/data/footballdatauk/ARG.csv`.
2. **Configuración de la Base de Datos:** definí la variable de entorno `ARGSTATS_DB_URL` con la connection string de tu PostgreSQL (ver `.env.example`):
   ```powershell
   $env:ARGSTATS_DB_URL = "postgresql://usuario:contraseña@localhost:5432/nombre_db"
   ```
3. Desde la raíz del repo, ejecutá el validador para asegurarte de que todos los equipos del CSV están mapeados:
   ```bash
   python -m sources.footballDataUk.check_names
   ```
4. Si la validación es exitosa, corré el proceso de inyección:
   ```bash
   python -m sources.footballDataUk.inyect_footballdata
   ```
   Al final muestra cuántos partidos recibieron cuotas y cuántas filas quedaron afuera por cada motivo.

### Agregar un equipo nuevo

Si `check_names` muestra un equipo sin mapeo (por ejemplo, un ascendido), agregalo en `MAPEO_EQUIPOS` con su ID de FotMob (lo encontrás en la tabla `equipos` o en la URL del equipo en FotMob) y `kaggle: None`.
