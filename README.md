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
* **`/core`**: Utilidades y configuraciones compartidas por todas las fuentes (conexión a base de datos, formateo de fechas, manejo de logs).
* **`/scripts-sql`**: Archivos `.sql` con la definición de la estructura relacional centralizada (DDL).
* **`/data`**: Directorio para almacenar el Data Lake de archivos crudos (JSONs, CSVs). *Nota: Por su peso, el grueso de esta carpeta está ignorado en Git.*

---

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

---

##  Cómo ejecutar este proyecto localmente

### Prerrequisitos
* Python 3.10+
* PostgreSQL 14+
* Google Chrome instalado

### Instalación y Preparación del Entorno

1. Clonar el repositorio e instalar las dependencias:
   ```bash
   git clone [https://github.com/tu-usuario/arg-football-scraper.git](https://github.com/tu-usuario/arg-football-scraper.git)
   cd arg-football-scraper
   pip install -r requirements.txt

2. **Obtener el Data Lake (Opcional pero recomendado):**  
   Si no querés ejecutar el scraper desde cero y prefieres usar el dataset que ya extrajimos, ve a la sección **[Releases](https://github.com/tu-usuario/arg-football-scraper/releases)** de este repositorio. Descargá el archivo `.zip` con los datos crudos y descomprimilo en la raíz del proyecto (quedará en una carpeta llamada `jsons/` o `data/`, la cual está ignorada por Git).

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

