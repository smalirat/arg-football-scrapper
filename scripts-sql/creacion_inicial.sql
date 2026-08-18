
CREATE TABLE IF NOT EXISTS equipos (
    equipo_id BIGINT PRIMARY KEY,
    nombre_fuente VARCHAR(255) NOT NULL,
    nombre_corto VARCHAR(100),
    es_fusion BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS jugadores (
    jugador_id BIGINT PRIMARY KEY,
    nombre_completo VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS ediciones (
    edicion_id SERIAL PRIMARY KEY,
    nombre_torneo VARCHAR(255) NOT NULL,
    temporada VARCHAR(50) NOT NULL,
    UNIQUE (nombre_torneo, temporada)
);


CREATE TABLE IF NOT EXISTS posiciones (
    edicion_id INT REFERENCES ediciones(edicion_id) ON DELETE CASCADE,
    equipo_id BIGINT REFERENCES equipos(equipo_id) ON DELETE CASCADE,
    zona VARCHAR(100),
    posicion INT,
    partidos_jugados INT DEFAULT 0,
    victorias INT DEFAULT 0,
    empates INT DEFAULT 0,
    derrotas INT DEFAULT 0,
    goles_favor INT DEFAULT 0,
    goles_contra INT DEFAULT 0,
    diferencia_gol INT DEFAULT 0,
    puntos INT DEFAULT 0,
    PRIMARY KEY (edicion_id, equipo_id)
);

CREATE TABLE IF NOT EXISTS transferencias (
    transferencia_id SERIAL PRIMARY KEY,
    jugador_id BIGINT REFERENCES jugadores(jugador_id) ON DELETE CASCADE,
    fecha VARCHAR(50), -- Se usa VARCHAR ya que las APIs suelen mandar formatos variables o incompletos
    equipo_origen_id BIGINT REFERENCES equipos(equipo_id) ON DELETE SET NULL,
    equipo_destino_id BIGINT REFERENCES equipos(equipo_id) ON DELETE SET NULL,
    tipo_transferencia VARCHAR(100)
);


CREATE TABLE IF NOT EXISTS partidos (
    partido_id BIGINT PRIMARY KEY, 
    edicion_id INT REFERENCES ediciones(edicion_id) ON DELETE CASCADE,
    equipo_local_id BIGINT REFERENCES equipos(equipo_id) ON DELETE CASCADE,
    equipo_visitante_id BIGINT REFERENCES equipos(equipo_id) ON DELETE CASCADE,
    fecha_utc VARCHAR(100),
    ronda VARCHAR(100),
    etapa_id INT, 
    goles_local INT,
    goles_visitante INT,
    penales_local INT,
    penales_visitante INT,
    estado VARCHAR(50),
    metadata JSONB 
);


CREATE TABLE IF NOT EXISTS stats_jugador_partido (
    partido_id BIGINT REFERENCES partidos(partido_id) ON DELETE CASCADE,
    jugador_id BIGINT REFERENCES jugadores(jugador_id) ON DELETE CASCADE,
    equipo_id BIGINT REFERENCES equipos(equipo_id) ON DELETE CASCADE,
    minutos_jugados INT DEFAULT 0,
    rating VARCHAR(50),
    goles INT DEFAULT 0,
    asistencias INT DEFAULT 0,
    xg NUMERIC(5,2) DEFAULT 0.0,
    xa NUMERIC(5,2) DEFAULT 0.0,
    tarjeta_amarilla BOOLEAN DEFAULT FALSE,
    tarjeta_roja BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (partido_id, jugador_id)
);

CREATE TABLE IF NOT EXISTS alineaciones (
    partido_id BIGINT REFERENCES partidos(partido_id) ON DELETE CASCADE,
    equipo_id BIGINT REFERENCES equipos(equipo_id) ON DELETE CASCADE,
    jugador_id BIGINT REFERENCES jugadores(jugador_id) ON DELETE CASCADE,
    es_titular BOOLEAN NOT NULL,
    dorsal INT,
    posicion VARCHAR(50),
    PRIMARY KEY (partido_id, jugador_id)
);

CREATE TABLE IF NOT EXISTS eventos (
    evento_id BIGINT PRIMARY KEY,
    partido_id BIGINT REFERENCES partidos(partido_id) ON DELETE CASCADE,
    equipo_id BIGINT REFERENCES equipos(equipo_id) ON DELETE SET NULL,
    jugador_id BIGINT REFERENCES jugadores(jugador_id) ON DELETE SET NULL,
    minuto INT,
    tipo_evento VARCHAR(100),
    detalle VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS tiros (
    tiro_id BIGINT PRIMARY KEY,
    partido_id BIGINT REFERENCES partidos(partido_id) ON DELETE CASCADE,
    equipo_id BIGINT REFERENCES equipos(equipo_id) ON DELETE SET NULL,
    jugador_id BIGINT REFERENCES jugadores(jugador_id) ON DELETE SET NULL,
    minuto INT,
    x NUMERIC(6,3),
    y NUMERIC(6,3),
    xg NUMERIC(5,3),
    xgot NUMERIC(5,3),
    tipo_tiro VARCHAR(100),
    resultado VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS momentum (
    partido_id BIGINT REFERENCES partidos(partido_id) ON DELETE CASCADE,
    minuto INT,
    valor NUMERIC(8,2),
    PRIMARY KEY (partido_id, minuto)
);