# Módulo Kaggle: Inyección de Datos Históricos

Este módulo está dedicado a la carga masiva de la historia del fútbol argentino (desde 1931 en adelante), utilizando datasets tabulares masivos provenientes de Kaggle.

## Archivos del Módulo

* `inyect_historical_csv.py`: Script ETL de carga. Lee el archivo CSV, normaliza las competiciones, registra los equipos y carga los resultados.

## Desafío Técnico: Colisión de IDs

La base de datos relacional utiliza como *Primary Key* los `partido_id` extraídos de FotMob para el fútbol moderno. Como los archivos CSV históricos carecen de IDs universales, corríamos el riesgo de generar colisiones de llaves primarias en PostgreSQL al generar IDs autonuméricos.

**La solución:** El script inyecta los partidos históricos generando identificadores ficticios en un rango reservado e inalcanzable por las APIs comerciales modernas (ej. `9000000000 + índice de fila`).

## Instrucciones de Uso

1. Asegúrate de tener el dataset histórico en `/data/kaggle/liga_2023.csv`.
2. **Configuración de la Base de Datos:** Antes de ejecutar los scripts, abre los archivos `inyect_kaggle.py` y reemplaza el string de la variable `DB_URL` con las credenciales de tu servidor PostgreSQL local:
   ```python
   # Ejemplo de configuración en el código:
   DB_URL = "postgresql://usuario:contraseña@localhost:5432/nombre_db"
3. Ejecuta el script de inyección:
   ```bash
   python inyect_historical_csv.py
4. El script utilizará el motor de SQLAlchemy dentro de un bloque transaccional (engine.begin()). Primero insertará los equipos únicos detectados, luego las temporadas/ediciones, y finalmente los miles de partidos históricos de forma segura.