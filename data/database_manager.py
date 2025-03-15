"""
Módulo para la gestión de la base de datos SQLite para clientes y proyectos.
"""

import os
import re
import sqlite3
from utils.logger_config import logger
from config.settings import DB_PATH

class DatabaseManager:
    """Clase dedicada al manejo de la base de datos de clientes y proyectos"""
    
    def __init__(self, db_path=None):
        """
        Inicializa el administrador de base de datos
        
        Args:
            db_path (str, optional): Ruta al archivo de base de datos. Si es None, 
                                     se utiliza la ruta predeterminada en DB_PATH.
        """
        if db_path is None:
            db_path = DB_PATH
            
        self.db_path = db_path
        self.setup_database()
    
    def setup_database(self):
        """
        Configura la estructura de la base de datos
        
        Returns:
            bool: True si la configuración fue exitosa, False en caso contrario
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Crear tablas si no existen
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                erp_number TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                business_partner TEXT,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                project_id TEXT PRIMARY KEY,
                client_erp TEXT NOT NULL,
                name TEXT NOT NULL,
                engagement_case TEXT,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_erp) REFERENCES clients(erp_number)
            )
            ''')

            conn.commit()
            logger.debug("Base de datos configurada correctamente")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error al configurar la base de datos: {e}")
            return False
        finally:
            if conn:
                conn.close()

        
    def get_clients(self):
        """
        Obtiene la lista de clientes ordenados por último uso
        
        Returns:
            list: Lista de strings con formato "erp_number - name"
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT erp_number, name FROM clients ORDER BY last_used DESC")
            clients = cursor.fetchall()

            return [f"{erp} - {name}" for erp, name in clients]
        except sqlite3.Error as e:
            logger.error(f"Error al obtener clientes: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def get_projects(self, client_erp):
        """
        Obtiene la lista de proyectos para un cliente específico
        
        Args:
            client_erp (str): Número ERP del cliente
            
        Returns:
            list: Lista de strings con formato "project_id - name"
        """
        if not client_erp:
            return []
        
        conn = None
        try:    
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT project_id, name 
                FROM projects 
                WHERE client_erp = ? 
                ORDER BY last_used DESC
            """, (client_erp,))

            projects = cursor.fetchall()
            return [f"{pid} - {name}" for pid, name in projects]
        except sqlite3.Error as e:
            logger.error(f"Error al obtener proyectos: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def save_client(self, erp_number, name, business_partner=""):
        """
        Guarda o actualiza un cliente en la base de datos
        
        Args:
            erp_number (str): Número ERP del cliente
            name (str): Nombre del cliente
            business_partner (str, optional): Socio de negocio
            
        Returns:
            bool: True si la operación fue exitosa, False en caso contrario
        """
        # Validación preliminar de todos los argumentos
        if not self.validate_input(erp_number, "erp"):
            logger.error(f"Número ERP inválido: {erp_number}")
            return False
            
        if not name or not isinstance(name, str):
            logger.error(f"Nombre de cliente inválido: {name}")
            return False
        
        # Limpiar y truncar datos si son demasiado largos
        name = name.strip()[:100]  # Limitar longitud para prevenir ataques
        business_partner = (business_partner or "").strip()[:50]
        
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA foreign_keys = ON")  # Asegurar que se verifican las claves foráneas
            cursor = conn.cursor()

            # Verificar si el cliente ya existe
            cursor.execute("SELECT erp_number FROM clients WHERE erp_number = ?", (erp_number,))
            existing = cursor.fetchone()

            if existing:
                # Actualizar cliente existente
                cursor.execute("""
                    UPDATE clients 
                    SET name = ?, business_partner = ?, last_used = CURRENT_TIMESTAMP 
                    WHERE erp_number = ?
                """, (name, business_partner, erp_number))
                logger.info(f"Cliente actualizado: {erp_number} - {name}")
            else:
                # Insertar nuevo cliente
                cursor.execute("""
                    INSERT INTO clients (erp_number, name, business_partner, last_used) 
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (erp_number, name, business_partner))
                logger.info(f"Nuevo cliente creado: {erp_number} - {name}")

            conn.commit()
            return True
        except sqlite3.IntegrityError as ie:
            logger.error(f"Error de integridad de datos al guardar cliente: {ie}")
            if conn:
                conn.rollback()
            return False
        except sqlite3.Error as e:
            logger.error(f"Error SQL al guardar cliente: {e}")
            if conn:
                conn.rollback()
            return False
        except Exception as e:
            logger.error(f"Error general al guardar cliente: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
                
    def save_project(self, project_id, client_erp, name, engagement_case=""):
        """
        Guarda o actualiza un proyecto en la base de datos
        
        Args:
            project_id (str): ID del proyecto
            client_erp (str): Número ERP del cliente
            name (str): Nombre del proyecto
            engagement_case (str, optional): Caso de compromiso
            
        Returns:
            bool: True si la operación fue exitosa, False en caso contrario
        """
        if not self.validate_input(project_id, "project") or not self.validate_input(client_erp, "erp"):
            logger.error(f"ID de proyecto o cliente inválido: {project_id}, {client_erp}")
            return False
        
        conn = None
        try:    
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Verificar si el proyecto ya existe
            cursor.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,))
            existing = cursor.fetchone()

            if existing:
                # Actualizar proyecto existente
                cursor.execute("""
                    UPDATE projects 
                    SET client_erp = ?, name = ?, engagement_case = ?, last_used = CURRENT_TIMESTAMP 
                    WHERE project_id = ?
                """, (client_erp, name, engagement_case, project_id))
            else:
                # Insertar nuevo proyecto
                cursor.execute("""
                    INSERT INTO projects (project_id, client_erp, name, engagement_case, last_used) 
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (project_id, client_erp, name, engagement_case))

            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error al guardar proyecto en BD: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
    
    def update_client_usage(self, erp_number):
        """
        Actualiza la fecha de último uso de un cliente
        
        Args:
            erp_number (str): Número ERP del cliente
            
        Returns:
            bool: True si la actualización fue exitosa, False en caso contrario
        """
        if not self.validate_input(erp_number, "erp"):
            return False
        
        conn = None
        try:    
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE clients 
                SET last_used = CURRENT_TIMESTAMP 
                WHERE erp_number = ?
            """, (erp_number,))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error al actualizar uso de cliente: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
    
    def update_project_usage(self, project_id):
        """
        Actualiza la fecha de último uso de un proyecto
        
        Args:
            project_id (str): ID del proyecto
            
        Returns:
            bool: True si la actualización fue exitosa, False en caso contrario
        """
        if not self.validate_input(project_id, "project"):
            return False
        
        conn = None
        try:    
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE projects 
                SET last_used = CURRENT_TIMESTAMP 
                WHERE project_id = ?
            """, (project_id,))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error al actualizar uso de proyecto: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
    
    @staticmethod
    def validate_input(input_str, input_type="general"):
        """
        Valida las entradas para prevenir inyecciones SQL
        
        Args:
            input_str (str): String a validar
            input_type (str): Tipo de input ("erp", "project", "path", "general")
            
        Returns:
            bool: True si la validación es exitosa, False en caso contrario
        """
        if input_type == "erp":
            # Solo permitir dígitos para ERP
            return bool(re.match(r'^\d+$', str(input_str)))
        elif input_type == "project":
            # Solo permitir dígitos para ID de proyecto
            return bool(re.match(r'^\d+$', str(input_str)))
        elif input_type == "path":
            # Validar ruta de archivo
            return os.path.isabs(input_str) and not any(c in input_str for c in '<>:|?*')
        return True
