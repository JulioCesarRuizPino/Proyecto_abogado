CREATE DATABASE  IF NOT EXISTS `asesoria_juridica` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `asesoria_juridica`;
-- MySQL dump 10.13  Distrib 8.0.45, for Win64 (x86_64)
--
-- Host: localhost    Database: asesoria_juridica
-- ------------------------------------------------------
-- Server version	8.0.45

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `consultas`
--

DROP TABLE IF EXISTS `consultas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `consultas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `titulo` varchar(200) DEFAULT NULL,
  `descripcion` text,
  `usuario_id` int DEFAULT NULL,
  `abogado_id` int DEFAULT NULL,
  `especialidad_detectada` varchar(80) DEFAULT NULL,
  `pdf_respaldo` varchar(255) DEFAULT NULL,
  `estado` varchar(50) DEFAULT NULL,
  `fecha` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `usuario_id` (`usuario_id`),
  KEY `fk_consultas_abogado` (`abogado_id`),
  CONSTRAINT `consultas_ibfk_1` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`),
  CONSTRAINT `consultas_ibfk_2` FOREIGN KEY (`abogado_id`) REFERENCES `usuarios` (`id`),
  CONSTRAINT `fk_consultas_abogado` FOREIGN KEY (`abogado_id`) REFERENCES `usuarios` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `consultas`
--

LOCK TABLES `consultas` WRITE;
/*!40000 ALTER TABLE `consultas` DISABLE KEYS */;
INSERT INTO `consultas` VALUES (7,'Consulta de prueba','Esto es una consulta de prueba\r\n',8,10,NULL,'case_pdfs/consulta_7.pdf','pendiente','2026-05-11 17:53:23');
/*!40000 ALTER TABLE `consultas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `mensajes_chat`
--

DROP TABLE IF EXISTS `mensajes_chat`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mensajes_chat` (
  `id` int NOT NULL AUTO_INCREMENT,
  `consulta_id` int NOT NULL,
  `remitente_id` int NOT NULL,
  `mensaje` text NOT NULL,
  `creado_en` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_chat_consulta` (`consulta_id`),
  KEY `fk_chat_remitente` (`remitente_id`),
  CONSTRAINT `fk_chat_consulta` FOREIGN KEY (`consulta_id`) REFERENCES `consultas` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_chat_remitente` FOREIGN KEY (`remitente_id`) REFERENCES `usuarios` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `mensajes_chat`
--

LOCK TABLES `mensajes_chat` WRITE;
/*!40000 ALTER TABLE `mensajes_chat` DISABLE KEYS */;
INSERT INTO `mensajes_chat` VALUES (3,7,10,'Mensaje de prueba 1','2026-05-17 01:41:02');
/*!40000 ALTER TABLE `mensajes_chat` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `notificaciones`
--

DROP TABLE IF EXISTS `notificaciones`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `notificaciones` (
  `id` int NOT NULL AUTO_INCREMENT,
  `usuario_id` int NOT NULL,
  `titulo` varchar(255) NOT NULL,
  `mensaje` text NOT NULL,
  `link` varchar(255) DEFAULT NULL,
  `leida` tinyint(1) NOT NULL DEFAULT '0',
  `creado_en` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_notificacion_usuario` (`usuario_id`),
  CONSTRAINT `fk_notificacion_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `notificaciones`
--

LOCK TABLES `notificaciones` WRITE;
/*!40000 ALTER TABLE `notificaciones` DISABLE KEYS */;
INSERT INTO `notificaciones` VALUES (8,8,'Solicitud creada','Se registro tu solicitud \"Consulta de prueba\".','/consultas/7/chat',1,'2026-05-11 17:53:23'),(9,8,'Abogado asignado','Se asigno manualmente a Abogado Ejemplo en tu caso \"Consulta de prueba\".','/consultas/7/chat',0,'2026-05-17 01:39:32'),(10,10,'Nuevo caso asignado','Recibiste el caso \"Consulta de prueba\" del cliente Cliente.','/consultas/7/chat',1,'2026-05-17 01:39:32'),(11,8,'Nuevo mensaje en el chat','Hay un nuevo mensaje en el caso \"Consulta de prueba\".','/consultas/7/chat',0,'2026-05-17 01:41:02');
/*!40000 ALTER TABLE `notificaciones` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `usuarios`
--

DROP TABLE IF EXISTS `usuarios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `usuarios` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `password` varchar(255) DEFAULT NULL,
  `tipo` enum('cliente','abogado','dueno') NOT NULL,
  `especialidades` text,
  `foto_url` varchar(255) DEFAULT NULL,
  `bio` text,
  `universidad` varchar(255) DEFAULT NULL,
  `experiencia` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `usuarios`
--

LOCK TABLES `usuarios` WRITE;
/*!40000 ALTER TABLE `usuarios` DISABLE KEYS */;
INSERT INTO `usuarios` VALUES (7,'Julio Ruiz','Julio@gmail.com','scrypt:32768:8:1$FJsv9I5x7mx6Pl51$aa26708b93843c818d99613c85ec8925fe54077156396c957a6954d65b7ef4331ffbdad446d125752d2f0b6cf1bf4a8d357305319b97acb3f4907f892e1fb4d6','cliente','','','','',''),(8,'Cliente','Cliente@ejemplo.com','scrypt:32768:8:1$TudGIm6F1LaQwNAS$d0e60155bd5c19d2e17682e8b57237db9326ba11596549e67701cbdf9b242278e962cc57046fc2f6dfe3d1e67863b33c38faee8340f8871c4cbdb2aa236d1236','cliente','','','','',''),(9,'Julio Ruiz','dueno@ejemplo.com','scrypt:32768:8:1$g4AyWD8TfhgKU9JB$a1c435854c3f68a7f18c71e78ca7c46dcccbfebaa8a0cecc112401fbf4af5756f20f1295efd484c34ba258f603c1f8a48df31e85744a9defb45c2fb8e4892908','dueno',NULL,NULL,NULL,NULL,NULL),(10,'Abogado Ejemplo','abogado@gmail.com','scrypt:32768:8:1$cBvxJloUjhDVmaSk$302483c36d501c514a46d989178745159b2f9f0968bf691bde6ee86df28ec5bb6e6fb25166e8061c29fc9be5f7c70255665356673225c801258d6c1ea8def705','abogado','familia, laboral, civil, penal, comercial, inmobiliario, migratorio','','','Universidad de Chile.','Abogado Independiente (2019 – Actualidad)');
/*!40000 ALTER TABLE `usuarios` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping routines for database 'asesoria_juridica'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-07-03 19:10:26
