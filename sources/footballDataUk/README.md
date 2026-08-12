# Módulo Football-Data.co.uk: Integración de Cuotas (Odds)

Este módulo se encarga de enriquecer la base de datos existente inyectando información de apuestas deportivas (Odds) históricas provenientes de los datasets en formato CSV de *Football-Data.co.uk*.

## Archivos del Módulo

* `inyect_footballdata.py`: Script ETL principal. Cruza los partidos del CSV con los partidos ya existentes en la base de datos y actualiza la columna `metadata` (JSONB) para agregar las cuotas promedio y de Pinnacle.
* `validator.py`: Script de auditoría. Compara los nombres de los equipos en el CSV contra la base de datos para detectar discrepancias antes de la inyección.
* `footballdata_config.py`: Archivo vital que contiene el diccionario `MAPEO_EQUIPOS`, el cual traduce los nombres en inglés/formato apuestas (ej. *Argentinos Jrs*) a los IDs internos de nuestra base de datos.

## Desafío Técnico: Matchmaking de Entidades

A diferencia de las APIs que proveen IDs únicos, los CSVs de apuestas operan mediante texto plano. Este módulo resuelve el problema mediante:
1. **Traducción de Nombres:** Uso del diccionario de mapeo estricto.
2. **Triangulación Temporal:** Si los nombres coinciden, el script valida la edición (torneo y año) y el resultado exacto de goles (`HG` y `AG`) para asegurarse de que está inyectando la cuota en el `partido_id` correcto de FotMob o Kaggle.
3. **Manejo de Discrepancias:** Si un partido existe en el CSV pero no en la base de datos, el script lo inserta como un nuevo evento base de "Fase Regular".

## Instrucciones de Uso

1. Coloca tu archivo CSV en la ruta `/data/footballdatauk/ARG.csv`.
2. Ejecuta el validador para asegurarte de que todos los equipos del CSV están mapeados en tu configuración:
   ```bash
   python validator.py
3. Si la validación es exitosa, corre el proceso de inyección:
    ```bash
    python inyect_footballdata.py