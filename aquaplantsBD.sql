-- --------------------------------------------------------
-- Host:                         127.0.0.1
-- Versión del servidor:         12.3.3-MariaDB - MariaDB Server
-- SO del servidor:              Win64
-- HeidiSQL Versión:             12.20.0.7320
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

-- Volcando estructura para tabla aquaplants_db.auth_group
CREATE TABLE IF NOT EXISTS `auth_group` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Volcando datos para la tabla aquaplants_db.auth_group: ~0 rows (aproximadamente)

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Volcando datos para la tabla aquaplants_db.auth_group_permissions: ~0 rows (aproximadamente)

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

-- Volcando datos para la tabla aquaplants_db.auth_permission: ~44 rows (aproximadamente)
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

-- Volcando estructura para tabla aquaplants_db.auth_user
CREATE TABLE IF NOT EXISTS `auth_user` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) NOT NULL,
  `first_name` varchar(150) NOT NULL,
  `last_name` varchar(150) NOT NULL,
  `email` varchar(254) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Volcando datos para la tabla aquaplants_db.auth_user: ~1 rows (aproximadamente)
INSERT INTO `auth_user` (`id`, `password`, `last_login`, `is_superuser`, `username`, `first_name`, `last_name`, `email`, `is_staff`, `is_active`, `date_joined`) VALUES
	(1, 'pbkdf2_sha256$1000000$gdfP5mwNwwHJUliMlvRKZW$AF4CFglZnAbswdMYOcFA9I3u3hW66Ayl1fcDKxSwE1I=', '2026-11-07 20:04:35.422588', 1, 'fbi', '', '', 'fbi@gmail.com', 1, 1, '2026-11-07 20:04:01.724578');

-- Volcando estructura para tabla aquaplants_db.auth_user_groups
CREATE TABLE IF NOT EXISTS `auth_user_groups` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `group_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_groups_user_id_group_id_94350c0c_uniq` (`user_id`,`group_id`),
  KEY `auth_user_groups_group_id_97559544_fk_auth_group_id` (`group_id`),
  CONSTRAINT `auth_user_groups_group_id_97559544_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Volcando datos para la tabla aquaplants_db.auth_user_groups: ~0 rows (aproximadamente)

-- Volcando estructura para tabla aquaplants_db.auth_user_user_permissions
CREATE TABLE IF NOT EXISTS `auth_user_user_permissions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` (`user_id`,`permission_id`),
  KEY `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Volcando datos para la tabla aquaplants_db.auth_user_user_permissions: ~0 rows (aproximadamente)

-- Volcando estructura para tabla aquaplants_db.django_admin_log
CREATE TABLE IF NOT EXISTS `django_admin_log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext DEFAULT NULL,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint(5) unsigned NOT NULL CHECK (`action_flag` >= 0),
  `change_message` longtext NOT NULL,
  `content_type_id` int(11) DEFAULT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_auth_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=22 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Volcando datos para la tabla aquaplants_db.django_admin_log: ~0 rows (aproximadamente)
INSERT INTO `django_admin_log` (`id`, `action_time`, `object_id`, `object_repr`, `action_flag`, `change_message`, `content_type_id`, `user_id`) VALUES
	(1, '2026-11-07 20:04:58.776017', '0db4cda7-1631-489a-b022-e3dadd297fd9', 'Instalacion1', 1, '[{"added": {}}]', 7, 1),
	(2, '2026-11-07 20:05:30.331718', 'f6192b23-fdc6-4c69-9c3b-3879cc05cc61', 'Instalacion2', 1, '[{"added": {}}]', 7, 1),
	(3, '2026-11-07 20:05:39.949524', 'd98cbba2-076c-4e6f-9f96-9588a174f201', 'Instalacion3', 1, '[{"added": {}}]', 7, 1),
	(4, '2026-11-07 20:05:57.579245', 'cdc445d8-c0d2-40ae-908b-c4d24cfde71f', 'temperatura - Instalacion1', 1, '[{"added": {}}]', 8, 1),
	(5, '2026-11-07 20:07:50.681452', '4829d758-4ffe-421f-a539-a2565518f902', 'humedad - Instalacion1', 1, '[{"added": {}}]', 8, 1),
	(6, '2026-11-07 20:08:19.107215', '3e415d44-4f2b-49cc-9b53-13711098abde', 'ph - Instalacion1', 1, '[{"added": {}}]', 8, 1),
	(7, '2026-11-07 20:08:31.712573', 'd82659d6-b842-49e2-aebe-b3f59fc9e68f', 'caudal - Instalacion1', 1, '[{"added": {}}]', 8, 1),
	(8, '2026-11-07 20:11:00.768600', '1', 'Regla de alerta para el sensor: ph - Instalacion1', 1, '[{"added": {}}]', 10, 1),
	(9, '2026-11-07 20:11:51.667014', '2', 'Regla de alerta para el sensor: humedad - Instalacion1', 1, '[{"added": {}}]', 10, 1),
	(10, '2026-11-07 20:12:20.024497', '3', 'Regla de alerta para el sensor: temperatura - Instalacion1', 1, '[{"added": {}}]', 10, 1),
	(11, '2026-11-07 20:12:42.263637', '4', 'Regla de alerta para el sensor: caudal - Instalacion1', 1, '[{"added": {}}]', 10, 1),
	(12, '2026-11-07 20:13:58.738778', '590d5414-2e4a-4525-a863-ae80715368a0', 'temperatura - Instalacion1', 1, '[{"added": {}}]', 8, 1),
	(13, '2026-11-07 20:14:05.612894', '66128b04-7c15-407e-94da-52eb744aaddb', 'humedad - Instalacion1', 1, '[{"added": {}}]', 8, 1),
	(14, '2026-11-07 20:14:09.209794', 'f4e111ad-6f9b-46a8-8bc5-d86913f691d5', 'ph - Instalacion1', 1, '[{"added": {}}]', 8, 1),
	(15, '2026-11-07 20:14:14.241519', '9c46b79c-10ac-4640-bf06-4745f5d1cc85', 'caudal - Instalacion1', 1, '[{"added": {}}]', 8, 1),
	(16, '2026-11-07 20:17:25.556091', 'd82659d6-b842-49e2-aebe-b3f59fc9e68f', 'caudal - Instalacion1', 3, '', 8, 1),
	(17, '2026-11-07 20:17:29.554199', '4829d758-4ffe-421f-a539-a2565518f902', 'humedad - Instalacion1', 3, '', 8, 1),
	(18, '2026-11-07 20:17:32.814455', 'cdc445d8-c0d2-40ae-908b-c4d24cfde71f', 'temperatura - Instalacion1', 3, '', 8, 1),
	(19, '2026-11-07 20:17:39.461410', '3e415d44-4f2b-49cc-9b53-13711098abde', 'ph - Instalacion1', 3, '', 8, 1),
	(20, '2026-11-07 20:19:22.819519', 'd98cbba2-076c-4e6f-9f96-9588a174f201', 'Instalacion3', 3, '', 7, 1),
	(21, '2026-11-07 20:19:26.765913', 'f6192b23-fdc6-4c69-9c3b-3879cc05cc61', 'Instalacion2', 3, '', 7, 1);

-- Volcando estructura para tabla aquaplants_db.django_content_type
CREATE TABLE IF NOT EXISTS `django_content_type` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Volcando datos para la tabla aquaplants_db.django_content_type: ~11 rows (aproximadamente)
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

-- Volcando estructura para tabla aquaplants_db.django_migrations
CREATE TABLE IF NOT EXISTS `django_migrations` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Volcando datos para la tabla aquaplants_db.django_migrations: ~20 rows (aproximadamente)
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
	(20, 'telemetria', '0002_reglaalerta_alertagenerada', '2026-11-07 20:02:02.250377');

-- Volcando estructura para tabla aquaplants_db.django_session
CREATE TABLE IF NOT EXISTS `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Volcando datos para la tabla aquaplants_db.django_session: ~0 rows (aproximadamente)
INSERT INTO `django_session` (`session_key`, `session_data`, `expire_date`) VALUES
	('4715drqqlgguij1sc24cwp156cddg8x7', '.eJxVjMsOwiAQRf-FtSEM77p07zeQYQCpGkhKuzL-uzbpQrf3nHNfLOC21rCNvIQ5sTMDdvrdItIjtx2kO7Zb59TbusyR7wo_6ODXnvLzcrh_BxVH_dauUDFOkZi0t14JUIDeojQ52SgcmqQ9SJeV8KSFkMrlQpoKRgANE7H3B8O9NzM:1xPmeR:kd4arMvFn-Kh1u1NqAqClhIl_BzvnIZWugxnCd-D4GU', '2026-11-21 20:04:35.426619');

-- Volcando estructura para tabla aquaplants_db.telemetria_alertagenerada
CREATE TABLE IF NOT EXISTS `telemetria_alertagenerada` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `mensaje` varchar(200) NOT NULL,
  `leida` tinyint(1) NOT NULL,
  `fecha_generacion` datetime(6) NOT NULL,
  `medicion_id` uuid NOT NULL,
  `regla_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `telemetria_alertagen_medicion_id_be847e7e_fk_telemetri` (`medicion_id`),
  KEY `telemetria_alertagen_regla_id_e556724c_fk_telemetri` (`regla_id`),
  CONSTRAINT `telemetria_alertagen_medicion_id_be847e7e_fk_telemetri` FOREIGN KEY (`medicion_id`) REFERENCES `telemetria_medicion` (`id`),
  CONSTRAINT `telemetria_alertagen_regla_id_e556724c_fk_telemetri` FOREIGN KEY (`regla_id`) REFERENCES `telemetria_reglaalerta` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Volcando datos para la tabla aquaplants_db.telemetria_alertagenerada: ~0 rows (aproximadamente)

-- Volcando estructura para tabla aquaplants_db.telemetria_instalacion
CREATE TABLE IF NOT EXISTS `telemetria_instalacion` (
  `id` uuid NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `ubicacion` varchar(200) NOT NULL,
  `activa` tinyint(1) NOT NULL,
  `fecha_creacion` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Volcando datos para la tabla aquaplants_db.telemetria_instalacion: ~0 rows (aproximadamente)
INSERT INTO `telemetria_instalacion` (`id`, `nombre`, `ubicacion`, `activa`, `fecha_creacion`) VALUES
	('0db4cda7-1631-489a-b022-e3dadd297fd9', 'Instalacion1', 'Fila1', 1, '2026-11-07 20:04:58.775015');

-- Volcando estructura para tabla aquaplants_db.telemetria_medicion
CREATE TABLE IF NOT EXISTS `telemetria_medicion` (
  `id` uuid NOT NULL,
  `valor` decimal(8,2) NOT NULL,
  `timestamp` datetime(6) NOT NULL,
  `estado_conexion` tinyint(1) NOT NULL,
  `sensor_id` uuid NOT NULL,
  PRIMARY KEY (`id`),
  KEY `telemetria_medicion_timestamp_1696ebaf` (`timestamp`),
  KEY `telemetria__sensor__c11693_idx` (`sensor_id`,`timestamp` DESC),
  CONSTRAINT `telemetria_medicion_sensor_id_e46d961e_fk_telemetria_sensor_id` FOREIGN KEY (`sensor_id`) REFERENCES `telemetria_sensor` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Volcando datos para la tabla aquaplants_db.telemetria_medicion: ~0 rows (aproximadamente)

-- Volcando estructura para tabla aquaplants_db.telemetria_reglaalerta
CREATE TABLE IF NOT EXISTS `telemetria_reglaalerta` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `limite_minimo` double DEFAULT NULL,
  `limite_maximo` double DEFAULT NULL,
  `activa` tinyint(1) NOT NULL,
  `sensor_id` uuid NOT NULL,
  PRIMARY KEY (`id`),
  KEY `telemetria_reglaaler_sensor_id_3bf04f11_fk_telemetri` (`sensor_id`),
  CONSTRAINT `telemetria_reglaaler_sensor_id_3bf04f11_fk_telemetri` FOREIGN KEY (`sensor_id`) REFERENCES `telemetria_sensor` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Volcando datos para la tabla aquaplants_db.telemetria_reglaalerta: ~4 rows (aproximadamente)

-- Volcando estructura para tabla aquaplants_db.telemetria_sensor
CREATE TABLE IF NOT EXISTS `telemetria_sensor` (
  `id` uuid NOT NULL,
  `tipo` varchar(50) NOT NULL,
  `modelo_hardware` varchar(100) NOT NULL,
  `instalacion_id` uuid NOT NULL,
  PRIMARY KEY (`id`),
  KEY `telemetria_sensor_instalacion_id_b00d380f_fk_telemetri` (`instalacion_id`),
  CONSTRAINT `telemetria_sensor_instalacion_id_b00d380f_fk_telemetri` FOREIGN KEY (`instalacion_id`) REFERENCES `telemetria_instalacion` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Volcando datos para la tabla aquaplants_db.telemetria_sensor: ~4 rows (aproximadamente)
INSERT INTO `telemetria_sensor` (`id`, `tipo`, `modelo_hardware`, `instalacion_id`) VALUES
	('9c46b79c-10ac-4640-bf06-4745f5d1cc85', 'caudal', 'SimuadorIot', '0db4cda7-1631-489a-b022-e3dadd297fd9'),
	('66128b04-7c15-407e-94da-52eb744aaddb', 'humedad', 'SimuadorIot', '0db4cda7-1631-489a-b022-e3dadd297fd9'),
	('590d5414-2e4a-4525-a863-ae80715368a0', 'temperatura', 'SimuadorIot', '0db4cda7-1631-489a-b022-e3dadd297fd9'),
	('f4e111ad-6f9b-46a8-8bc5-d86913f691d5', 'ph', 'SimuadorIot', '0db4cda7-1631-489a-b022-e3dadd297fd9');

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;
