

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS evaluaciones_unidad (
	clave VARCHAR(180) NOT NULL, 
	unidad_id VARCHAR(100) NOT NULL, 
	semana INTEGER NOT NULL, 
	anio INTEGER NOT NULL, 
	regimen VARCHAR(20) NOT NULL, 
	posible_oclusion BOOLEAN NOT NULL, 
	cobertura_suficiente BOOLEAN NOT NULL, 
	climatologia JSON NOT NULL, 
	fecha TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (clave)
);

CREATE INDEX IF NOT EXISTS ix_evaluaciones_unidad_unidad_id ON evaluaciones_unidad (unidad_id);

CREATE TABLE IF NOT EXISTS eventos_incendio (
	id SERIAL NOT NULL, 
	referencia TIMESTAMP WITH TIME ZONE NOT NULL, 
	inicio TIMESTAMP WITH TIME ZONE NOT NULL, 
	fin TIMESTAMP WITH TIME ZONE NOT NULL, 
	latitude FLOAT NOT NULL, 
	longitude FLOAT NOT NULL, 
	geom geometry(POINT,4326) NOT NULL, 
	sensor_principal VARCHAR(10) NOT NULL, 
	sensores_presentes JSON NOT NULL, 
	en_tunari BOOLEAN NOT NULL, 
	cerca_asentamiento BOOLEAN NOT NULL, 
	distrito INTEGER, 
	subdistrito VARCHAR(100), 
	hex_id VARCHAR(60) NOT NULL, 
	frp_medio FLOAT, 
	frp_max FLOAT, 
	num_detecciones INTEGER NOT NULL, 
	candidata BOOLEAN NOT NULL, 
	posible_oclusion BOOLEAN NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_eventos_incendio_geom ON eventos_incendio USING gist (geom);

CREATE INDEX IF NOT EXISTS ix_eventos_incendio_distrito ON eventos_incendio (distrito);

CREATE INDEX IF NOT EXISTS ix_eventos_incendio_fin ON eventos_incendio (fin);

CREATE INDEX IF NOT EXISTS ix_eventos_incendio_hex_id ON eventos_incendio (hex_id);

CREATE INDEX IF NOT EXISTS ix_eventos_incendio_inicio ON eventos_incendio (inicio);

CREATE INDEX IF NOT EXISTS ix_eventos_incendio_referencia ON eventos_incendio (referencia);

CREATE TABLE IF NOT EXISTS ingestas (
	id SERIAL NOT NULL, 
	clave VARCHAR(100) NOT NULL, 
	fuente VARCHAR(40) NOT NULL, 
	origen VARCHAR(12) NOT NULL, 
	inicio DATE NOT NULL, 
	fin DATE NOT NULL, 
	completa BOOLEAN NOT NULL, 
	filas INTEGER NOT NULL, 
	estado VARCHAR(20) NOT NULL, 
	fecha TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (clave)
);

CREATE TABLE IF NOT EXISTS unidades_espaciales (
	id VARCHAR(100) NOT NULL, 
	clase VARCHAR(25) NOT NULL, 
	nombre VARCHAR(150) NOT NULL, 
	distrito INTEGER, 
	subdistrito VARCHAR(100), 
	verificada BOOLEAN NOT NULL, 
	geom geometry(GEOMETRY,4326) NOT NULL, 
	propiedades JSON NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_unidades_espaciales_geom ON unidades_espaciales USING gist (geom);

CREATE INDEX IF NOT EXISTS ix_unidades_espaciales_clase ON unidades_espaciales (clase);

CREATE TABLE IF NOT EXISTS alertas (
	id SERIAL NOT NULL, 
	clave VARCHAR(180) NOT NULL, 
	unidad_id VARCHAR(100) NOT NULL, 
	evento_id INTEGER, 
	nivel VARCHAR(12) NOT NULL, 
	senal VARCHAR(40) NOT NULL, 
	descripcion VARCHAR(1500) NOT NULL, 
	estado VARCHAR(20) NOT NULL, 
	fecha TIMESTAMP WITH TIME ZONE NOT NULL, 
	actualizada TIMESTAMP WITH TIME ZONE NOT NULL, 
	distrito INTEGER, 
	latitude FLOAT NOT NULL, 
	longitude FLOAT NOT NULL, 
	revision_manual BOOLEAN NOT NULL, 
	notificacion VARCHAR(30) NOT NULL, 
	notificada BOOLEAN NOT NULL, 
	detalle JSON NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (clave), 
	FOREIGN KEY(evento_id) REFERENCES eventos_incendio (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_alertas_estado ON alertas (estado);

CREATE INDEX IF NOT EXISTS ix_alertas_fecha ON alertas (fecha);

CREATE INDEX IF NOT EXISTS ix_alertas_nivel ON alertas (nivel);

CREATE INDEX IF NOT EXISTS ix_alertas_unidad_id ON alertas (unidad_id);

CREATE TABLE IF NOT EXISTS detecciones_raw (
	id SERIAL NOT NULL, 
	clave VARCHAR(64) NOT NULL, 
	sensor VARCHAR(10) NOT NULL, 
	satelite VARCHAR(40) NOT NULL, 
	fuente VARCHAR(40) NOT NULL, 
	origen VARCHAR(12) NOT NULL, 
	fecha TIMESTAMP WITH TIME ZONE NOT NULL, 
	latitude FLOAT NOT NULL, 
	longitude FLOAT NOT NULL, 
	geom geometry(POINT,4326) NOT NULL, 
	resolucion INTEGER NOT NULL, 
	frp FLOAT, 
	confidence VARCHAR(30) NOT NULL, 
	brightness FLOAT, 
	bright_ti4 FLOAT, 
	tipo INTEGER, 
	candidata BOOLEAN NOT NULL, 
	descartada BOOLEAN NOT NULL, 
	revision_manual BOOLEAN NOT NULL, 
	en_tunari BOOLEAN NOT NULL, 
	cerca_asentamiento BOOLEAN NOT NULL, 
	distrito INTEGER, 
	subdistrito VARCHAR(100), 
	hex_id VARCHAR(60) NOT NULL, 
	evento_id INTEGER, 
	original JSON NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (clave), 
	FOREIGN KEY(evento_id) REFERENCES eventos_incendio (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_detecciones_raw_geom ON detecciones_raw USING gist (geom);

CREATE INDEX IF NOT EXISTS ix_detecciones_raw_distrito ON detecciones_raw (distrito);

CREATE INDEX IF NOT EXISTS ix_detecciones_raw_evento_id ON detecciones_raw (evento_id);

CREATE INDEX IF NOT EXISTS ix_detecciones_raw_fecha ON detecciones_raw (fecha);

CREATE INDEX IF NOT EXISTS ix_detecciones_raw_hex_id ON detecciones_raw (hex_id);

CREATE INDEX IF NOT EXISTS ix_detecciones_raw_sensor ON detecciones_raw (sensor);

ALTER TABLE detecciones_raw ADD COLUMN IF NOT EXISTS producto VARCHAR(40);
ALTER TABLE detecciones_raw ADD COLUMN IF NOT EXISTS brightness_k FLOAT;
ALTER TABLE detecciones_raw ADD COLUMN IF NOT EXISTS confidence_score FLOAT;
ALTER TABLE detecciones_raw ADD COLUMN IF NOT EXISTS posible_oclusion BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE ingestas ADD COLUMN IF NOT EXISTS detalle JSON;
