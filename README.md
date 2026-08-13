# ARG-FOOTBALL-SCRAPER

Este proyecto open source es un ecosistema modular de recolección y procesamiento de datos diseñado para centralizar información histórica y en tiempo real del fútbol argentino. 

En lugar de depender de una única API, el proyecto actúa como un agregador: recopila, cruza y limpia información de múltiples proveedores y fuentes crudas (FotMob, Kaggle, Football-Data.co.uk, entre otros) para construir una base de datos relacional robusta, unificada y agnóstica a la fuente en PostgreSQL.

---

## Arquitectura del Proyecto

El sistema está diseñado con una arquitectura modular orientada a dominios (fuentes), lo que permite escalar y conectar nuevos proveedores sin afectar el flujo de los demás:

1. **Scraping Dinámico & Bypass:** Motores de extracción en Python adaptados a cada fuente. Incluye evasión de protecciones modernas (como Cloudflare/Turnstile) utilizando navegadores automatizados.
2. **Transformación Específica (ETL):** Cada fuente tiene su propio módulo de normalización para manejar asimetrías (ej. unificar los distintos IDs o nombres que cada proveedor usa para un mismo equipo).
3. **Carga Centralizada (Load):** Inyección a un esquema unificado en PostgreSQL utilizando operaciones idempotentes (`Upserts`) para evitar duplicados y fusionar datos de distintas fuentes sin colisiones.

---

## Estructura del Repositorio

El proyecto aísla la lógica compartida de la lógica específica de cada proveedor:

* **`/sources`**: El núcleo del agregador. Contiene subcarpetas por cada proveedor (`/fotmob`, `/footballdatauk`, `/kaggle`, etc.). Cada una encapsula sus propios scrapers, scripts ETL y configuraciones de mapeo.
* **`/scripts-sql`**: Archivos `.sql` con la definición de la estructura relacional centralizada (DDL).
* **`/data`**: Directorio para almacenar el Data Lake de archivos crudos (JSONs, CSVs). *Nota: Por su peso, el grueso de esta carpeta está ignorado en Git.*

### Configuración de la Base de Datos

Para almacenar la información recolectada, el sistema utiliza una base de datos relacional unificada (por defecto, PostgreSQL). Para inicializarla:

1. Crea una base de datos vacía en tu gestor preferido (ej. pgAdmin, DBeaver, DataGrip) o mediante la línea de comandos.
2. Ejecuta el script de creación inicial para construir las tablas y el esquema relacional:
   ```bash
   psql -U tu_usuario -d nombre_de_tu_db -f scripts-sql/creacion-inicial.sql

(Nota: Si deseas migrar a otro motor de base de datos como MySQL o MariaDB, deberás modificar la cadena de conexión de SQLAlchemy por la correspondiente a tu gestor, y adaptar ligeramente el archivo creacion-inicial.sql, especialmente los campos nativos de Postgres como JSONB).

### Documentación por Fuente (Módulos)
El grueso de la lógica de extracción de este proyecto hoy en día se encuentra en la integración con FotMob, pero el sistema soporta de forma modular a otros proveedores. Podés consultar las instrucciones de ejecución detalladas, prerrequisitos y particularidades de cada módulo en sus respectivos manuales:

Módulo FotMob: Manual de extracción masiva de JSONs, generación de perfiles de Chrome para evasión de Turnstile y carga de Big Data.

Módulo Football-Data.co.uk: Manual para integrar datos de cuotas de apuestas (Odds) históricas.

Módulo Kaggle (Histórico): Manual para la inyección de datos históricos mediante archivos CSV.

