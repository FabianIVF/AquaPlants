-- --------------------------------------------------------
-- Respaldo Estructural y de Datos - AquaPlants (MySQL / MariaDB)
-- Generado sin tablas ni credenciales de usuarios (auth_user / sesiones excluidas)
-- Incluye columna `activo` en telemetria_sensor y mediciones de ejemplo
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

-- Volcando estructura de base de datos para aquaplants_db
CREATE DATABASE IF NOT EXISTS `aquaplants_db` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci */;
USE `aquaplants_db`;

-- Volcando estructura para tabla aquaplants_db.django_content_type
CREATE TABLE IF NOT EXISTS `django_content_type` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `django_content_type` (`id`, `app_label`, `model`) VALUES
	(1, 'admin', 'logentry'),
	(2, 'auth', 'permission'),
	(3, 'auth', 'group'),
	(4, 'auth', 'user'),
	(5, 'contenttypes', 'contenttype'),
	(6, 'sessions', 'session'),
	(7, 'telemetria', 'instalacion'),
	(8, 'telemetria', 'sensor'),
	(9, 'telemetria', 'medicion'),
	(10, 'telemetria', 'reglaalerta'),
	(11, 'telemetria', 'alertagenerada');

-- Volcando estructura para tabla aquaplants_db.auth_permission
CREATE TABLE IF NOT EXISTS `auth_permission` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `content_type_id` int(11) NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=45 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `auth_permission` (`id`, `name`, `content_type_id`, `codename`) VALUES
	(1, 'Can add log entry', 1, 'add_logentry'),
	(2, 'Can change log entry', 1, 'change_logentry'),
	(3, 'Can delete log entry', 1, 'delete_logentry'),
	(4, 'Can view log entry', 1, 'view_logentry'),
	(5, 'Can add permission', 2, 'add_permission'),
	(6, 'Can change permission', 2, 'change_permission'),
	(7, 'Can delete permission', 2, 'delete_permission'),
	(8, 'Can view permission', 2, 'view_permission'),
	(9, 'Can add group', 3, 'add_group'),
	(10, 'Can change group', 3, 'change_group'),
	(11, 'Can delete group', 3, 'delete_group'),
	(12, 'Can view group', 3, 'view_group'),
	(13, 'Can add user', 4, 'add_user'),
	(14, 'Can change user', 4, 'change_user'),
	(15, 'Can delete user', 4, 'delete_user'),
	(16, 'Can view user', 4, 'view_user'),
	(17, 'Can add content type', 5, 'add_contenttype'),
	(18, 'Can change content type', 5, 'change_contenttype'),
	(19, 'Can delete content type', 5, 'delete_contenttype'),
	(20, 'Can view content type', 5, 'view_contenttype'),
	(21, 'Can add session', 6, 'add_session'),
	(22, 'Can change session', 6, 'change_session'),
	(23, 'Can delete session', 6, 'delete_session'),
	(24, 'Can view session', 6, 'view_session'),
	(25, 'Can add instalacion', 7, 'add_instalacion'),
	(26, 'Can change instalacion', 7, 'change_instalacion'),
	(27, 'Can delete instalacion', 7, 'delete_instalacion'),
	(28, 'Can view instalacion', 7, 'view_instalacion'),
	(29, 'Can add sensor', 8, 'add_sensor'),
	(30, 'Can change sensor', 8, 'change_sensor'),
	(31, 'Can delete sensor', 8, 'delete_sensor'),
	(32, 'Can view sensor', 8, 'view_sensor'),
	(33, 'Can add medicion', 9, 'add_medicion'),
	(34, 'Can change medicion', 9, 'change_medicion'),
	(35, 'Can delete medicion', 9, 'delete_medicion'),
	(36, 'Can view medicion', 9, 'view_medicion'),
	(37, 'Can add regla alerta', 10, 'add_reglaalerta'),
	(38, 'Can change regla alerta', 10, 'change_reglaalerta'),
	(39, 'Can delete regla alerta', 10, 'delete_reglaalerta'),
	(40, 'Can view regla alerta', 10, 'view_reglaalerta'),
	(41, 'Can add alerta generada', 11, 'add_alertagenerada'),
	(42, 'Can change alerta generada', 11, 'change_alertagenerada'),
	(43, 'Can delete alerta generada', 11, 'delete_alertagenerada'),
	(44, 'Can view alerta generada', 11, 'view_alertagenerada');

-- Volcando estructura para tabla aquaplants_db.auth_group
CREATE TABLE IF NOT EXISTS `auth_group` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `auth_group` (`id`, `name`) VALUES
	(1, 'Administrador'),
	(2, 'Encargado de cultivo'),
	(3, 'Supervisor'),
	(4, 'Dispositivo IoT');

-- Volcando estructura para tabla aquaplants_db.auth_group_permissions
CREATE TABLE IF NOT EXISTS `auth_group_permissions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `group_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `auth_group_permissions` (`id`, `group_id`, `permission_id`) VALUES
	-- Administrador (CRUD total del dominio)
	(1, 1, 25), (2, 1, 26), (3, 1, 27), (4, 1, 28),
	(5, 1, 29), (6, 1, 30), (7, 1, 31), (8, 1, 32),
	(9, 1, 33), (10, 1, 34), (11, 1, 35), (12, 1, 36),
	(13, 1, 37), (14, 1, 38), (15, 1, 39), (16, 1, 40),
	(17, 1, 41), (18, 1, 42), (19, 1, 43), (20, 1, 44),
	-- Encargado de cultivo (Lectura completa + CRUD reglas de alerta + marcar alertas)
	(21, 2, 28), (22, 2, 32), (23, 2, 36), (24, 2, 40), (25, 2, 44),
	(26, 2, 37), (27, 2, 38), (28, 2, 39), (29, 2, 42),
	-- Supervisor (Solo lectura estricta)
	(30, 3, 28), (31, 3, 32), (32, 3, 36), (33, 3, 40), (34, 3, 44),
	-- Dispositivo IoT (Ingesta de mediciones + consulta de sensores/instalaciones)
	(35, 4, 28), (36, 4, 32), (37, 4, 33);

-- Volcando estructura para tabla aquaplants_db.django_migrations
CREATE TABLE IF NOT EXISTS `django_migrations` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=22 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `django_migrations` (`id`, `app`, `name`, `applied`) VALUES
	(1, 'contenttypes', '0001_initial', '2026-11-07 20:02:00.671270'),
	(2, 'auth', '0001_initial', '2026-11-07 20:02:01.249749'),
	(3, 'admin', '0001_initial', '2026-11-07 20:02:01.366705'),
	(4, 'admin', '0002_logentry_remove_auto_add', '2026-11-07 20:02:01.373214'),
	(5, 'admin', '0003_logentry_add_action_flag_choices', '2026-11-07 20:02:01.379239'),
	(6, 'contenttypes', '0002_remove_content_type_name', '2026-11-07 20:02:01.463167'),
	(7, 'auth', '0002_alter_permission_name_max_length', '2026-11-07 20:02:01.516264'),
	(8, 'auth', '0003_alter_user_email_max_length', '2026-11-07 20:02:01.552224'),
	(9, 'auth', '0004_alter_user_username_opts', '2026-11-07 20:02:01.560696'),
	(10, 'auth', '0005_alter_user_last_login_null', '2026-11-07 20:02:01.609560'),
	(11, 'auth', '0006_require_contenttypes_0002', '2026-11-07 20:02:01.611725'),
	(12, 'auth', '0007_alter_validators_add_error_messages', '2026-11-07 20:02:01.619254'),
	(13, 'auth', '0008_alter_user_username_max_length', '2026-11-07 20:02:01.654482'),
	(14, 'auth', '0009_alter_user_last_name_max_length', '2026-11-07 20:02:01.689746'),
	(15, 'auth', '0010_alter_group_name_max_length', '2026-11-07 20:02:01.724500'),
	(16, 'auth', '0011_update_proxy_permissions', '2026-11-07 20:02:01.731487'),
	(17, 'auth', '0012_alter_user_first_name_max_length', '2026-11-07 20:02:01.765617'),
	(18, 'sessions', '0001_initial', '2026-11-07 20:02:01.819611'),
	(19, 'telemetria', '0001_initial', '2026-11-07 20:02:02.051860'),
	(20, 'telemetria', '0002_reglaalerta_alertagenerada', '2026-11-07 20:02:02.250377'),
	(21, 'telemetria', '0003_sensor_activo_alter_sensor_tipo', '2026-11-08 04:55:10.120000');

-- Volcando estructura para tabla aquaplants_db.telemetria_instalacion
CREATE TABLE IF NOT EXISTS `telemetria_instalacion` (
  `id` uuid NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `ubicacion` varchar(200) NOT NULL,
  `activa` tinyint(1) NOT NULL DEFAULT 1,
  `fecha_creacion` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `telemetria_instalacion` (`id`, `nombre`, `ubicacion`, `activa`, `fecha_creacion`) VALUES
	('0db4cda7-1631-489a-b022-e3dadd297fd9', 'Huerto Hidroponico Norte', 'Invernadero Sector A', 1, '2026-11-07 20:04:58.775015'),
	('a1b2c3d4-1111-4444-8888-1234567890ab', 'Torre Vertical Experimental', 'Laboratorio INACAP', 1, '2026-11-10 14:30:00.000000');

-- Volcando estructura para tabla aquaplants_db.telemetria_sensor (incluye columna `activo`)
CREATE TABLE IF NOT EXISTS `telemetria_sensor` (
  `id` uuid NOT NULL,
  `tipo` varchar(50) NOT NULL,
  `modelo_hardware` varchar(100) NOT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT 1,
  `instalacion_id` uuid NOT NULL,
  PRIMARY KEY (`id`),
  KEY `telemetria_sensor_instalacion_id_b00d380f_fk_telemetri` (`instalacion_id`),
  CONSTRAINT `telemetria_sensor_instalacion_id_b00d380f_fk_telemetri` FOREIGN KEY (`instalacion_id`) REFERENCES `telemetria_instalacion` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `telemetria_sensor` (`id`, `tipo`, `modelo_hardware`, `activo`, `instalacion_id`) VALUES
	('590d5414-2e4a-4525-a863-ae80715368a0', 'temperatura_agua', 'Sonda Sumergible DS18B20', 1, '0db4cda7-1631-489a-b022-e3dadd297fd9'),
	('66128b04-7c15-407e-94da-52eb744aaddb', 'humedad', 'Sensor de Humedad DHT22', 1, '0db4cda7-1631-489a-b022-e3dadd297fd9'),
	('f4e111ad-6f9b-46a8-8bc5-d86913f691d5', 'ph', 'Sonda pH Analogica V1.1', 1, '0db4cda7-1631-489a-b022-e3dadd297fd9'),
	('9c46b79c-10ac-4640-bf06-4745f5d1cc85', 'caudal', 'Flujometro YF-S201', 1, '0db4cda7-1631-489a-b022-e3dadd297fd9'),
	('b7e21030-9f1a-4c32-9c2d-112233445566', 'co2', 'Sensor NDIR MH-Z19B', 0, '0db4cda7-1631-489a-b022-e3dadd297fd9'),
	('c8d32141-0a2b-4d43-8d3e-223344556677', 'temperatura_aire', 'Sensor Ambiental DHT22 / BME280', 1, 'a1b2c3d4-1111-4444-8888-1234567890ab'),
	('d9e43252-1b3c-4e54-9e4f-334455667788', 'nivel_estanque', 'Sensor Ultrasonico HC-SR04 / Nivel Liquido', 1, 'a1b2c3d4-1111-4444-8888-1234567890ab');

-- Volcando estructura para tabla aquaplants_db.telemetria_medicion
CREATE TABLE IF NOT EXISTS `telemetria_medicion` (
  `id` uuid NOT NULL,
  `valor` decimal(8,2) NOT NULL,
  `timestamp` datetime(6) NOT NULL,
  `estado_conexion` tinyint(1) NOT NULL DEFAULT 1,
  `sensor_id` uuid NOT NULL,
  PRIMARY KEY (`id`),
  KEY `telemetria_medicion_timestamp_1696ebaf` (`timestamp`),
  KEY `telemetria__sensor__c11693_idx` (`sensor_id`,`timestamp` DESC),
  CONSTRAINT `telemetria_medicion_sensor_id_e46d961e_fk_telemetria_sensor_id` FOREIGN KEY (`sensor_id`) REFERENCES `telemetria_sensor` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `telemetria_medicion` (`id`, `valor`, `timestamp`, `estado_conexion`, `sensor_id`) VALUES
	('11111111-1111-4111-8111-000000000001', 21.40, '2026-11-15 18:00:00.000000', 1, '590d5414-2e4a-4525-a863-ae80715368a0'),
	('11111111-1111-4111-8111-000000000002', 21.65, '2026-11-15 18:05:00.000000', 1, '590d5414-2e4a-4525-a863-ae80715368a0'),
	('11111111-1111-4111-8111-000000000003', 27.80, '2026-11-15 18:10:00.000000', 1, '590d5414-2e4a-4525-a863-ae80715368a0'),
	('11111111-1111-4111-8111-000000000004', 65.20, '2026-11-15 18:00:05.000000', 1, '66128b04-7c15-407e-94da-52eb744aaddb'),
	('11111111-1111-4111-8111-000000000005', 66.10, '2026-11-15 18:05:05.000000', 1, '66128b04-7c15-407e-94da-52eb744aaddb'),
	('11111111-1111-4111-8111-000000000006', 6.10,  '2026-11-15 18:00:10.000000', 1, 'f4e111ad-6f9b-46a8-8bc5-d86913f691d5'),
	('11111111-1111-4111-8111-000000000007', 6.15,  '2026-11-15 18:05:10.000000', 1, 'f4e111ad-6f9b-46a8-8bc5-d86913f691d5'),
	('11111111-1111-4111-8111-000000000008', 6.08,  '2026-11-15 18:10:10.000000', 1, 'f4e111ad-6f9b-46a8-8bc5-d86913f691d5'),
	('11111111-1111-4111-8111-000000000009', 2.45,  '2026-11-15 18:00:15.000000', 1, '9c46b79c-10ac-4640-bf06-4745f5d1cc85'),
	('11111111-1111-4111-8111-000000000010', 0.00,  '2026-11-15 18:05:15.000000', 0, '9c46b79c-10ac-4640-bf06-4745f5d1cc85'),
	('11111111-1111-4111-8111-000000000011', 23.50, '2026-11-15 18:00:20.000000', 1, 'c8d32141-0a2b-4d43-8d3e-223344556677'),
	('11111111-1111-4111-8111-000000000012', 24.10, '2026-11-15 18:05:20.000000', 1, 'c8d32141-0a2b-4d43-8d3e-223344556677'),
	('11111111-1111-4111-8111-000000000013', 78.50, '2026-11-15 18:00:25.000000', 1, 'd9e43252-1b3c-4e54-9e4f-334455667788'),
	('11111111-1111-4111-8111-000000000014', 22.00, '2026-11-15 18:10:25.000000', 1, 'd9e43252-1b3c-4e54-9e4f-334455667788');

-- Volcando estructura para tabla aquaplants_db.telemetria_reglaalerta
CREATE TABLE IF NOT EXISTS `telemetria_reglaalerta` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `limite_minimo` double DEFAULT NULL,
  `limite_maximo` double DEFAULT NULL,
  `activa` tinyint(1) NOT NULL DEFAULT 1,
  `sensor_id` uuid NOT NULL,
  PRIMARY KEY (`id`),
  KEY `telemetria_reglaaler_sensor_id_3bf04f11_fk_telemetri` (`sensor_id`),
  CONSTRAINT `telemetria_reglaaler_sensor_id_3bf04f11_fk_telemetri` FOREIGN KEY (`sensor_id`) REFERENCES `telemetria_sensor` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `telemetria_reglaalerta` (`id`, `limite_minimo`, `limite_maximo`, `activa`, `sensor_id`) VALUES
	(1, 5.5, 6.8, 1, 'f4e111ad-6f9b-46a8-8bc5-d86913f691d5'),
	(2, 50.0, 80.0, 1, '66128b04-7c15-407e-94da-52eb744aaddb'),
	(3, 18.0, 24.0, 1, '590d5414-2e4a-4525-a863-ae80715368a0'),
	(4, 1.5, 4.0, 1, '9c46b79c-10ac-4640-bf06-4745f5d1cc85'),
	(5, 30.0, 95.0, 1, 'd9e43252-1b3c-4e54-9e4f-334455667788');

-- Volcando estructura para tabla aquaplants_db.telemetria_alertagenerada
CREATE TABLE IF NOT EXISTS `telemetria_alertagenerada` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `mensaje` varchar(200) NOT NULL,
  `leida` tinyint(1) NOT NULL DEFAULT 0,
  `fecha_generacion` datetime(6) NOT NULL,
  `medicion_id` uuid NOT NULL,
  `regla_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `telemetria_alertagen_medicion_id_be847e7e_fk_telemetri` (`medicion_id`),
  KEY `telemetria_alertagen_regla_id_e556724c_fk_telemetri` (`regla_id`),
  CONSTRAINT `telemetria_alertagen_medicion_id_be847e7e_fk_telemetri` FOREIGN KEY (`medicion_id`) REFERENCES `telemetria_medicion` (`id`) ON DELETE CASCADE,
  CONSTRAINT `telemetria_alertagen_regla_id_e556724c_fk_telemetri` FOREIGN KEY (`regla_id`) REFERENCES `telemetria_reglaalerta` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `telemetria_alertagenerada` (`id`, `mensaje`, `leida`, `fecha_generacion`, `medicion_id`, `regla_id`) VALUES
	(1, '¡ALERTA ROJA! Temperatura del Agua / Solución ALTO: 27.80°C (Límite: 24.0°C)', 0, '2026-11-15 18:10:00.050000', '11111111-1111-4111-8111-000000000003', 3),
	(2, '¡ALERTA AZUL! Nivel del Estanque BAJO: 22.00% (Límite: 30.0%)', 0, '2026-11-15 18:10:25.050000', '11111111-1111-4111-8111-000000000014', 5);

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;
