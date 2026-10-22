# Módulo Kaggle: Inyección de Datos Históricos

Este módulo está dedicado a la carga masiva de la historia del fútbol argentino (desde 1931 en adelante), utilizando datasets tabulares masivos provenientes de Kaggle.

## Archivos del Módulo

* `inyect_kaggle.py`: Script ETL de carga. Lee el archivo CSV, normaliza las competiciones, registra los equipos y carga los resultados.

## Desafío Técnico: Colisión de IDs

La base de datos relacional utiliza como *Primary Key* los `partido_id` extraídos de FotMob para el fútbol moderno. Como los archivos CSV históricos carecen de IDs universales, corríamos el riesgo de generar colisiones de llaves primarias en PostgreSQL al generar IDs autonuméricos.

**La solución:** El script inyecta los partidos históricos generando identificadores ficticios en un rango reservado e inalcanzable por las APIs comerciales modernas (ej. `9000000000 + índice de fila`).

## IDs de equipos: uno solo por club

El CSV numera los equipos del 0 al 95, y FotMob usa sus propios IDs para los mismos clubes. Si se cargaran los dos tal cual, cada club quedaría duplicado (Boca con el ID 17 del CSV y con el 10077 de FotMob).

Por eso el script traduce cada ID del CSV al de FotMob antes de escribir, con la tabla de `configs/equipos_kaggle.py`. Los clubes que FotMob no tiene (Mandiyú, Loma Negra, etc.) se cargan con su ID del CSV. La misma tabla la usa `sources/footballDataUk` para cruzar las cuotas con los partidos históricos.

## Instrucciones de Uso

1. Asegúrate de tener el dataset histórico en `/data/kaggle/liga_2023.csv`.
2. **Configuración de la Base de Datos:** definí la variable de entorno `ARGSTATS_DB_URL` con la connection string de tu PostgreSQL (ver `.env.example`):
   ```powershell
   $env:ARGSTATS_DB_URL = "postgresql://usuario:contraseña@localhost:5432/nombre_db"
   ```
3. Ejecuta el script de inyección:
   ```bash
   python sources/kaggle/inyect_kaggle.py
4. El script utilizará el motor de SQLAlchemy dentro de un bloque transaccional (engine.begin()). Primero insertará los equipos únicos detectados, luego las temporadas/ediciones, y finalmente los miles de partidos históricos de forma segura.