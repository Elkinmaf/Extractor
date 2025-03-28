#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
IssuesExtractor - Módulo principal para coordinación del proceso de extracción

Este módulo define la clase IssuesExtractor que coordina el proceso completo
de extracción de issues de SAP, utilizando los otros componentes:
- SAPBrowser: Para la automatización del navegador
- DatabaseManager: Para gestionar clientes y proyectos
- ExcelManager: Para manejar los archivos Excel de salida

La clase proporciona métodos para ejecutar el proceso de extracción con o sin
interfaz gráfica, y permite al usuario seleccionar clientes, proyectos y 
archivos Excel destino para los datos.
"""

import os
import sys
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import json
import logging
import base64
import sqlite3
from io import BytesIO
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# Importaciones de otros módulos del proyecto
from utils.logger_config import setup_logger
from data.database_manager import DatabaseManager
from data.excel_manager import ExcelManager
from browser.sap_browser import SAPBrowser
from config.settings import SAP_COLORS

# Configurar logger
logger = logging.getLogger(__name__)

# Verificar disponibilidad de PIL para funciones gráficas
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class IssuesExtractor:
    """
    Clase principal para extraer issues de SAP con interfaz gráfica y base de datos
    
    Esta clase coordina todo el proceso de extracción, desde la conexión
    con el navegador, la selección de clientes y proyectos, hasta la extracción
    de datos y su almacenamiento en archivos Excel.
    """

    def __init__(self):
        """Inicializa la clase con sus componentes y variables necesarias"""
        self.excel_file_path = None
        self.driver = None
        
        # Inicializar root primero (si se va a usar GUI)
        self.root = None
        
        # Variables que dependen de Tkinter - inicializar como None
        self.status_var = None
        self.client_var = None
        self.project_var = None
        self.project_combo = None
        self.log_text = None
        self.excel_filename_var = None
        self.processing = False
        self.left_panel = None
        self.header_frame = None
        self.client_combo = None
        self.image_cache = {}
        
        # Componentes
        self.db_manager = DatabaseManager()
        self.excel_manager = ExcelManager()
        self.browser = SAPBrowser()
        
        # Configurar referencias cruzadas para que el navegador pueda acceder a UI
        self.setup_browser_ui_references()
    
    def setup_browser_ui_references(self):
        """
        Configura las referencias a la interfaz de usuario en el navegador.
        Esto permite que el navegador actualice directamente la interfaz.
        """
        # Asignar referencias a la UI si existen
        self.browser.root = self.root
        self.browser.status_var = self.status_var
        
        # Agregar logger a ambos componentes para registrar eventos
        logger.debug("Referencias cruzadas de UI configuradas en el navegador")
    
    def configure_columns_after_settings(self):
        """
        Método auxiliar para configurar todas las columnas después de abrir el panel de ajustes.
        Este método debe ser llamado después de hacer clic en el botón de ajustes.
        
        Utiliza la implementación robusta de selección de columnas que sigue
        la secuencia de teclas verificada en las pruebas.
        
        Returns:
            bool: True si el proceso fue exitoso, False en caso contrario
        """
        try:
            logger.info("Configurando columnas después de abrir panel de ajustes...")
            
            # Verificar que tenemos acceso al navegador
            if not self.browser or not self.driver:
                logger.error("No hay navegador inicializado")
                return False
            
            # Ejecutar la selección de columnas usando el método robusto
            # Este método utiliza una secuencia específica de teclas (Tab, flechas, Enter)
            # que ha sido verificada en pruebas
            result = self.browser.select_all_visible_columns()
            
            if result:
                logger.info("[OK] Columnas configuradas correctamente")
            else:
                logger.warning("[ERROR] No se pudo completar la configuración de columnas")
                
            return result
        except Exception as e:
            logger.error(f"Error al configurar columnas: {e}")
            return False
            
    def choose_excel_file(self):
        """Permite al usuario elegir un archivo Excel existente o crear uno nuevo"""
        file_path = self.excel_manager.select_file()
        self.excel_file_path = file_path
        self.excel_manager.file_path = file_path
        
        # Actualizar la interfaz si existe
        if hasattr(self, 'status_var') and self.status_var:
            self.status_var.set(f"Archivo Excel seleccionado: {os.path.basename(file_path)}")
        
        # Actualizar el nombre del archivo en la etiqueta
        if hasattr(self, 'excel_filename_var') and self.excel_filename_var:
            self.excel_filename_var.set(f"Archivo: {os.path.basename(file_path)}")
            
        return file_path
        
    def connect_to_browser(self):
        """Conecta con el navegador y devuelve el éxito de la conexión"""
        result = self.browser.connect()
        self.driver = self.browser.driver
        # Actualizar referencias UI después de tener el driver
        self.setup_browser_ui_references()
        return result
        
    def update_excel(self, issues_data):
        """
        Actualiza el archivo Excel con los datos extraídos
        
        Args:
            issues_data (list): Lista de diccionarios con datos de issues
            
        Returns:
            tuple: (success, new_items, updated_items)
        """
        success, new_items, updated_items = self.excel_manager.update_with_issues(issues_data)
        
        # Actualizar la interfaz si existe
        if hasattr(self, 'status_var') and self.status_var:
            if success:
                self.status_var.set(f"Excel actualizado: {new_items} nuevos, {updated_items} actualizados")
            else:
                self.status_var.set("Error al actualizar Excel")
                
        # Mostrar mensaje de éxito
        if success and self.root:
            messagebox.showinfo(
                "Proceso Completado", 
                f"El archivo Excel ha sido actualizado correctamente.\n\n"
                f"Se han agregado {new_items} nuevos issues y actualizado {updated_items} issues existentes."
            )
            
        return success, new_items, updated_items
    
    
    
    
    def extract_sap_issues(self, erp_number, project_id):
        """
        Método principal para la extracción completa de issues de SAP.
        
        Args:
            erp_number (str): Número ERP para selección del cliente
            project_id (str): ID del proyecto a consultar
            
        Returns:
            list: Lista de issues extraídos
            bool: True si la operación fue exitosa
        """
        try:
            logger.info(f"Iniciando extracción de issues para proyecto {project_id}")
            
            # 1. Conectar navegador y navegar a la página de SAP
            self.browser.connect()
            result = self.browser.navigate_to_sap(erp_number, project_id)
            if not result:
                logger.error("No se pudo navegar a la página de SAP")
                return [], False
                
            # 2. Seleccionar cliente y proyecto
            if not self.browser.select_customer_automatically(erp_number):
                logger.error(f"No se pudo seleccionar el cliente {erp_number}")
                return [], False
                
            if not self.browser.select_project_automatically(project_id):
                logger.error(f"No se pudo seleccionar el proyecto {project_id}")
                return [], False
                
            # 3. Realizar búsqueda
            if not self.browser.click_search_button():
                logger.error("No se pudo hacer clic en el botón de búsqueda")
                return [], False
                
            # 4. Esperar a que carguen los resultados iniciales
            if not self.browser.wait_for_search_results(timeout=30):
                logger.warning("Posible problema al cargar resultados iniciales")
                # Continuamos de todos modos, ya que algunos resultados podrían estar disponibles
            
            # 5. Extraer todos los issues con el método mejorado de extracción robusta
            logger.info("Iniciando extracción completa de issues con método robusto")
            all_issues = self.browser.extract_all_issues_robust()  # Usar el método robusto
            
            # 6. Validar resultados
            if not all_issues or len(all_issues) == 0:
                logger.error("No se encontraron issues para extraer")
                return [], False
                
            # 7. Actualizar base de datos con los issues extraídos
            logger.info(f"Actualizando base de datos con {len(all_issues)} issues")
            self.db_manager.save_issues(all_issues, project_id)
            
            # 8. Actualizar Excel con los datos extraídos
            logger.info("Actualizando archivos Excel")
            self.update_excel(all_issues)
                
            logger.info(f"Extracción completa finalizada: {len(all_issues)} issues procesados")
            return all_issues, True
            
        except Exception as e:
            logger.error(f"Error en extract_sap_issues: {e}")
            return [], False
        finally:
            # Cerramos el navegador solo si está configurado para ello
            if hasattr(self, 'config') and self.config.get("close_browser_after_extraction", True):
                self.browser.close()


    def run_extraction(self):
        """
        Ejecuta el proceso completo de extracción para modo GUI y consola.
        
        Este método se ha actualizado para usar las mejoras en la extracción
        y proporciona un flujo más robusto para el usuario.
        
        Returns:
            bool: True si la extracción fue exitosa, False en caso contrario
        """
        try:
            if not self.connect_to_browser():
                logger.error("Error al conectar con el navegador")
                
                # Actualizar la interfaz si existe
                if hasattr(self, 'status_var') and self.status_var:
                    self.status_var.set("Error al conectar con el navegador")
                    
                return False

            # Obtener valores de cliente y proyecto - MODIFICADO PARA EXTRAER EL NÚMERO DE ID
            full_client = self.client_var.get().strip() if hasattr(self, 'client_var') and self.client_var else ""
            full_project = self.project_var.get().strip() if hasattr(self, 'project_var') and self.project_var else ""
            
            # Extraer solo el número de ID de las cadenas completas
            erp_number = full_client.split(" - ")[0].strip() if " - " in full_client else full_client
            project_id = full_project.split(" - ")[0].strip() if " - " in full_project else full_project

            # Validar que tenemos valores no vacíos
            if not erp_number:
                logger.warning("ERP number está vacío")
                if hasattr(self, 'root') and self.root:
                    messagebox.showwarning("Datos incompletos", "Debe especificar un número ERP de cliente")
                return False
                    
            if not project_id:
                logger.warning("Project ID está vacío")
                if hasattr(self, 'root') and self.root:
                    messagebox.showwarning("Datos incompletos", "Debe especificar un ID de proyecto")
                return False
                                
            logger.info(f"Iniciando extracción para cliente: {erp_number}, proyecto: {project_id}")
        
            # Navegar a la URL inicial especificada
            logger.info("Navegando a la URL de SAP con parámetros específicos...")
            
            # Actualizar la interfaz si existe
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set("Navegando a SAP...")
                
            if not self.browser.navigate_to_sap(erp_number, project_id):
                logger.error("Error al navegar a la URL de SAP")
                return False
            
            # Manejar autenticación si es necesario
            if not self.browser.handle_authentication():
                logger.error("Error en el proceso de autenticación")
                return False
                
            # Estrategia mejorada con múltiples intentos para seleccionar cliente
            client_selected = False
            
            # Método 1: Verificar si los campos ya tienen los valores correctos
            if self.browser.verify_fields_have_expected_values(erp_number, project_id):
                logger.info("Los campos ya contienen los valores correctos, omitiendo selección")
                client_selected = True
            
            # Si no están los valores correctos, intentar seleccionar automáticamente
            if not client_selected:
                # Actualizar la interfaz si existe
                if hasattr(self, 'status_var') and self.status_var:
                    self.status_var.set("Seleccionando cliente automáticamente...")
                
                # Método 2: Usar la función mejorada de selección automática
                if self.browser.select_customer_automatically(erp_number):
                    logger.info("Cliente seleccionado con método principal")
                    client_selected = True
                else:
                    # Método 3: Usar JavaScript UI5 si los métodos anteriores fallan
                    if hasattr(self.browser, 'select_customer_ui5_direct'):
                        if self.browser.select_customer_ui5_direct(erp_number):
                            logger.info("Cliente seleccionado con JavaScript UI5")
                            client_selected = True
                    
                    # Método 4: Solicitar intervención manual si todo lo anterior falla
                    if not client_selected:
                        logger.warning("No se pudo seleccionar cliente automáticamente")
                        # Solicitar selección manual si es necesario
                        if hasattr(self, 'root') and self.root:
                            messagebox.showwarning("Selección Manual Requerida", 
                                "No se pudo seleccionar el cliente automáticamente.\n\n"
                                "Por favor, seleccione manualmente el cliente y haga clic en Continuar.")
                            result = messagebox.askokcancel("Confirmación", "¿Ha seleccionado el cliente?")
                            if not result:
                                return False
                            client_selected = True  # El usuario confirmó que seleccionó manualmente
                            time.sleep(1)  # Dar tiempo para que se procese la selección
                        else:
                            # En modo consola
                            print("\n⚠️ No se pudo seleccionar el cliente automáticamente.")
                            input("➡️ Por favor, seleccione manualmente el cliente y presione Enter para continuar...")
                            client_selected = True

            # Actualizar la interfaz
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set("Seleccionando proyecto automáticamente...")
            
            # Seleccionar proyecto con reintentos
            project_selected = False
            max_attempts = 3
            
            for attempt in range(max_attempts):
                logger.info(f"Intento {attempt+1}/{max_attempts} de selección de proyecto")
                
                # Esperar un poco más antes de cada intento
                if attempt > 0:
                    time.sleep(3)
                    
                if self.browser.select_project_automatically(project_id):
                    logger.info(f"Proyecto {project_id} seleccionado con éxito en el intento {attempt+1}")
                    project_selected = True
                    break
                else:
                    logger.warning(f"Intento {attempt+1} de selección de proyecto fallido")
            
            # Si no se pudo seleccionar automáticamente, solicitar selección manual
            if not project_selected:
                logger.warning("No se pudo seleccionar proyecto automáticamente")
                # Solicitar selección manual si es necesario
                if hasattr(self, 'root') and self.root:
                    messagebox.showwarning("Selección Manual Requerida", 
                        "No se pudo seleccionar el proyecto automáticamente.\n\n"
                        "Por favor, seleccione manualmente el proyecto y haga clic en Continuar.")
                    result = messagebox.askokcancel("Confirmación", "¿Ha seleccionado el proyecto?")
                    if not result:
                        return False
                    project_selected = True
                else:
                    # En modo consola
                    print("\n⚠️ No se pudo seleccionar el proyecto automáticamente.")
                    input("➡️ Por favor, seleccione manualmente el proyecto y presione Enter para continuar...")
                    project_selected = True
            
            # Hacer clic en el botón de búsqueda
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set("Realizando búsqueda...")
                
            # Hacer clic en búsqueda utilizando el método mejorado
            if not self.browser.click_search_button():
                logger.warning("Error al hacer clic en el botón de búsqueda automáticamente")
                # Solicitar acción manual
                if hasattr(self, 'root') and self.root:
                    messagebox.showwarning("Acción Manual Requerida", 
                        "No se pudo hacer clic en el botón de búsqueda automáticamente.\n\n"
                        "Por favor, haga clic manualmente en el botón de búsqueda.")
                    result = messagebox.askokcancel("Confirmación", "¿Ha hecho clic en el botón de búsqueda?")
                    if not result:
                        return False
                else:
                    # En modo consola
                    print("\n⚠️ No se pudo hacer clic en el botón de búsqueda automáticamente.")
                    input("➡️ Por favor, haga clic manualmente en el botón de búsqueda y presione Enter para continuar...")
            
            # Esperar a que se carguen los resultados de la búsqueda
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set("Esperando resultados de búsqueda...")
                
            # Esperar resultados utilizando el método mejorado
            if not self.browser.wait_for_search_results():
                logger.warning("No se pudo confirmar la carga de resultados")
                # Dar tiempo adicional y continuar de todos modos
                time.sleep(5)
            
            # MÉTODO AUTOMATIZADO DE NAVEGACIÓN POR TECLADO
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set("Iniciando navegación por teclado...")

            # Usar el método mejorado que maneja toda la navegación después de seleccionar cliente y proyecto
            # con la secuencia exacta de teclas especificada
            if self.browser.navigate_post_selection():
                logger.info("✅ Navegación post-selección completada con éxito")
                
                # Esperar a que se recargue la tabla con las nuevas columnas
                time.sleep(1)
            else:
                logger.warning("❌ La navegación automática por teclado falló")
                
                # Si falla la navegación automática, intentar el método anterior
                if hasattr(self, 'status_var') and self.status_var:
                    self.status_var.set("Intentando método alternativo...")
                    
                # Intentar hacer clic en ajustes manualmente
                if not self.browser.navigate_keyboard_sequence():
                    logger.warning("No se pudo completar la secuencia de navegación por teclado")
                    
                    if hasattr(self, 'root') and self.root:
                        messagebox.showwarning("Acción Manual Requerida", 
                            "La navegación automática ha fallado.\n\n"
                            "Por favor, realice estos pasos manualmente:\n"
                            "1. Haga clic en el título 'Issues and Actions Overview'\n"
                            "2. Pulse Tab 18 veces\n"
                            "3. Pulse Enter (para ajustes)\n"
                            "4. Pulse Tab 3 veces\n" 
                            "5. Pulse flecha derecha 2 veces\n"
                            "6. Pulse Enter (para columnas)\n"
                            "7. Pulse Tab 3 veces\n"
                            "8. Pulse Enter (para Select All)\n"
                            "9. Pulse Tab 2 veces\n"
                            "10. Pulse Enter (para OK)")
                        
                        result = messagebox.askokcancel("Confirmación", 
                                                    "¿Ha completado los pasos manualmente?")
                        if not result:
                            logger.error("Usuario canceló después de fallo en navegación automática")
                            if hasattr(self, 'status_var') and self.status_var:
                                self.status_var.set("Proceso cancelado por el usuario")
                            return False
                    else:
                        # En modo consola
                        print("\n⚠️ La navegación automática ha fallado.")
                        print("Por favor, realice estos pasos manualmente:")
                        print("1. Haga clic en el título 'Issues and Actions Overview'")
                        print("2. Pulse Tab 18 veces")
                        print("3. Pulse Enter (para ajustes)")
                        print("4. Pulse Tab 3 veces")
                        print("5. Pulse flecha derecha 2 veces")
                        print("6. Pulse Enter (para columnas)")
                        print("7. Pulse Tab 3 veces")
                        print("8. Pulse Enter (para Select All)")
                        print("9. Pulse Tab 2 veces")
                        print("10. Pulse Enter (para OK)")
                        input("➡️ Después de completar los pasos, presione Enter para continuar...")
            
            # Realizar la extracción con el método mejorado
            return self.perform_extraction()
                
        except Exception as e:
            logger.error(f"Error en el proceso de extracción: {e}")
            
            # Actualizar la interfaz si existe
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set(f"Error: {e}")
                
            return False        
        
        
        
        
        
        
        
        
    def navigate_to_issues_tab(self):
        """
        Navega a la pestaña 'Issues' una vez seleccionado el proyecto.
        
        Returns:
            bool: True si la navegación fue exitosa, False en caso contrario
        """
        try:
            logger.info("Intentando navegar a la pestaña Issues...")
            
            # Esperar a que cargue la página del proyecto
            time.sleep(3)
            
            # Buscar la pestaña de Issues por diferentes selectores
            issues_tab_selectors = [
                "//div[contains(text(), 'Issues')] | //span[contains(text(), 'Issues')]",
                "//li[@role='tab']//div[contains(text(), 'Issues')]",
                "//a[contains(text(), 'Issues')]",
                "//div[contains(@class, 'sapMITBItem')]//span[contains(text(), 'Issues')]"
            ]
            
            for selector in issues_tab_selectors:
                try:
                    issues_tabs = self.driver.find_elements(By.XPATH, selector)
                    if issues_tabs:
                        for tab in issues_tabs:
                            try:
                                # Verificar si es visible
                                if tab.is_displayed():
                                    # Hacer scroll hasta el elemento
                                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tab)
                                    time.sleep(0.5)
                                    
                                    # Intentar clic
                                    self.driver.execute_script("arguments[0].click();", tab)
                                    logger.info("Clic en pestaña Issues realizado")
                                    time.sleep(3)  # Esperar a que cargue
                                    return True
                            except:
                                continue
                except:
                    continue
            
            logger.warning("No se encontró la pestaña Issues por selectores directos")
            
            # Intentar buscar por posición relativa (generalmente la tercera pestaña)
            try:
                tabs = self.driver.find_elements(By.XPATH, "//li[@role='tab'] | //div[@role='tab']")
                if len(tabs) >= 3:  # Asumiendo que Issues es la tercera pestaña
                    third_tab = tabs[2]  # Índice 2 para el tercer elemento
                    self.driver.execute_script("arguments[0].click();", third_tab)
                    logger.info("Clic en tercera pestaña realizado")
                    time.sleep(1) #Modificado de 3 a 1
                    return True
            except:
                pass
                
            logger.warning("No se pudo navegar a la pestaña Issues")
            return False
            
        except Exception as e:
            logger.error(f"Error al navegar a la pestaña Issues: {e}")
            return False
            
    def _verify_issues_page(self):
        """
        Verifica si estamos en la página de Issues correcta.
        
        Returns:
            bool: True si estamos en la página de Issues, False en caso contrario
        """
        try:
            # Estrategia 1: Buscar el texto "Issues (número)"
            try:
                issues_title_elements = self.driver.find_elements(
                    By.XPATH, 
                    "//div[contains(text(), 'Issues') and contains(text(), '(')]"
                )
                if issues_title_elements:
                    logger.info(f"Página de Issues detectada por título: {issues_title_elements[0].text}")
                    return True
            except Exception as e:
                logger.debug(f"No se pudo detectar título de Issues: {e}")
            
            # Estrategia 2: Verificar si hay filas de datos visibles
            # Usar el método de browser para encontrar filas
            issue_rows = self.browser.find_table_rows(highlight=False)
            if len(issue_rows) > 0:
                logger.info(f"Se detectaron {len(issue_rows)} filas de datos que parecen issues")
                return True
            
            # Estrategia 3: Verificar encabezados de columna típicos
            try:
                column_headers = self.driver.find_elements(
                    By.XPATH,
                    "//div[text()='Title'] | //div[text()='Type'] | //div[text()='Priority'] | //div[text()='Status']"
                )
                if len(column_headers) >= 3:
                    logger.info(f"Se detectaron encabezados de columna típicos de issues: {len(column_headers)}")
                    return True
            except Exception as e:
                logger.debug(f"No se pudieron detectar encabezados de columna: {e}")
            
            # Si no se detecta ninguna de las condiciones anteriores
            logger.warning("No se detectó la página de Issues")
            return False
        
        except Exception as e:
            logger.error(f"Error al verificar página de Issues: {e}")
            return False
        
        
        
        
        
        
        
        
    def perform_extraction(self):
        """
        Método principal para ejecutar el proceso de extracción.
        
        Utiliza el método mejorado extract_all_issues_robust para obtener
        datos de forma más confiable y completa.
        
        Returns:
            bool: True si la extracción fue exitosa, False en caso contrario
        """
        try:
            # Marcar como procesando
            self.processing = True
            
            logger.info("MÉTODO: perform_extraction - Comenzando proceso de extracción mejorado")
            
            # Actualizar la interfaz si existe
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set("Comenzando extracción de datos...")
                if self.root:
                    self.root.update()
            
            # Verificar que tenemos un archivo Excel configurado
            if not self.excel_file_path:
                logger.warning("No se ha seleccionado archivo Excel para guardar los datos")
                if hasattr(self, 'root') and self.root:
                    excel_path = self.choose_excel_file()
                    if not excel_path:
                        logger.error("No se seleccionó archivo Excel")
                        self.processing = False
                        return False
            
            # Usar el método robusto mejorado para extraer datos
            logger.info("Iniciando extracción robusta de issues...")
            
            # Actualizar la interfaz
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set("Extrayendo datos con método mejorado...")
                if self.root:
                    self.root.update()
            
            # Llamar al método de extracción robusto
            issues_data = self.browser.extract_all_issues_robust()
            
            # Verificar si se obtuvieron datos
            if not issues_data or len(issues_data) == 0:
                logger.error("No se encontraron issues para extraer")
                
                if hasattr(self, 'status_var') and self.status_var:
                    self.status_var.set("Error: No se encontraron issues para extraer")
                
                if self.root:
                    messagebox.showerror(
                        "Error de Extracción", 
                        "No se pudieron encontrar issues para extraer. Verifique que está en la página correcta."
                    )
                
                self.processing = False
                return False
            
            # Actualizar la interfaz
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set(f"Guardando {len(issues_data)} issues en Excel...")
                if self.root:
                    self.root.update()
            
            # Actualizar Excel con los datos extraídos
            success, new_items, updated_items = self.update_excel(issues_data)
            
            # Verificar resultado de la actualización
            if success:
                logger.info(f"Excel actualizado: {new_items} nuevos items, {updated_items} actualizados")
                
                if hasattr(self, 'status_var') and self.status_var:
                    self.status_var.set(f"Excel actualizado: {new_items} nuevos, {updated_items} actualizados")
                
                if self.root:
                    messagebox.showinfo(
                        "Proceso Completado", 
                        f"El archivo Excel ha sido actualizado correctamente.\n\n"
                        f"Se han agregado {new_items} nuevos issues y actualizado {updated_items} issues existentes."
                    )
            else:
                logger.error("Error al actualizar Excel")
                
                if hasattr(self, 'status_var') and self.status_var:
                    self.status_var.set("Error al actualizar Excel")
                
                if self.root:
                    messagebox.showerror(
                        "Error al Actualizar Excel", 
                        "No se pudo actualizar el archivo Excel.\n\n"
                        "Verifique que el archivo no esté abierto en otra aplicación."
                    )
            
            self.processing = False
            return success
            
        except Exception as e:
            logger.error(f"Error general en el proceso de extracción: {e}")
            
            # Actualizar la interfaz
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set(f"Error: {e}")
            
            self.processing = False
            return False



    def start_extraction(self):
        """
        Inicia el proceso de extracción de issues con método mejorado.
        Prepara la interfaz y ejecuta la extracción en un hilo separado.
        """
        try:
            # Verificar si hay un proceso en curso
            if self.processing:
                messagebox.showwarning("Proceso en curso", "Hay un proceso de extracción en curso.")
                return
                
            # Verificar que existe un archivo Excel seleccionado
            if not self.excel_file_path:
                messagebox.showwarning("Archivo Excel no seleccionado", "Debe seleccionar o crear un archivo Excel primero.")
                return
                    
            # Verificar que el navegador está abierto
            if not self.driver:
                messagebox.showwarning("Navegador no iniciado", "Debe iniciar el navegador primero.")
                return
            
            # Marcar como procesando
            self.processing = True
            
            # Actualizar la interfaz
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set("Iniciando extracción de issues...")
                if self.root:
                    self.root.update()
            
            # Ejecutar la extracción en un hilo separado para no bloquear la GUI
            def extraction_thread():
                try:
                    # Usar el método de extracción mejorado
                    success = self.perform_extraction()
                    
                    if not success:
                        logger.warning("La extracción no fue exitosa")
                        if hasattr(self, 'status_var') and self.status_var and self.root:
                            self.root.after(0, lambda: self.status_var.set("Extracción no completada"))
                    
                except Exception as e:
                    logger.error(f"Error en el hilo de extracción: {e}")
                    if hasattr(self, 'status_var') and self.status_var and self.root:
                        self.root.after(0, lambda: self.status_var.set(f"Error: {e}"))
                        
                    # Mostrar mensaje de error en el hilo principal
                    if self.root:
                        self.root.after(0, lambda: messagebox.showerror("Error", f"Error durante la extracción: {e}"))
                finally:
                    # Restablecer estado de procesamiento
                    self.processing = False
                    if hasattr(self, 'status_var') and self.status_var and self.root:
                        self.root.after(0, lambda: self.status_var.set("Extracción finalizada"))
            
            # Iniciar el hilo de extracción
            threading.Thread(target=extraction_thread, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Error al iniciar extracción: {e}")
            if self.root:
                messagebox.showerror("Error", f"Error al iniciar extracción: {e}")
            self.processing = False





    
    
    def setup_gui_logger(self):
        """
        Configura el logger para que también escriba en la GUI
        
        Crea un handler personalizado que redirige los mensajes de log
        al widget Text de la interfaz gráfica.
        """
        class TextHandler(logging.Handler):
            def __init__(self, text_widget):
                logging.Handler.__init__(self)
                self.text_widget = text_widget
            
            def emit(self, record):
                msg = self.format(record)
                def append():
                    self.text_widget.configure(state='normal')
                    
                    # Agregar marca de tiempo y nivel con color
                    time_str = msg.split(' - ')[0] + ' - '
                    level_str = record.levelname + ' - '
                    msg_content = msg.split(' - ', 2)[2] if len(msg.split(' - ')) > 2 else ""
                    
                    self.text_widget.insert(tk.END, time_str, "INFO")
                    self.text_widget.insert(tk.END, level_str, record.levelname)
                    self.text_widget.insert(tk.END, msg_content + '\n', record.levelname)
                    
                    self.text_widget.configure(state='disabled')
                    self.text_widget.yview(tk.END)
                    
                    # Limitar tamaño del log
                    self.limit_log_length()
                    
                # Llamar a append desde el hilo principal
                self.text_widget.after(0, append)
                
            def limit_log_length(self):
                """Limita la longitud del log para evitar consumo excesivo de memoria"""
                if float(self.text_widget.index('end-1c').split('.')[0]) > 1000:
                    self.text_widget.configure(state='normal')
                    self.text_widget.delete('1.0', '500.0')
                    self.text_widget.configure(state='disabled')
        
        # Solo configurar si hay un widget de texto disponible
        if hasattr(self, 'log_text') and self.log_text:
            # Crear handler para el widget Text
            text_handler = TextHandler(self.log_text)
            text_handler.setLevel(logging.INFO)
            text_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            
            # Añadir el handler al logger
            logger.addHandler(text_handler)
            
            # Deshabilitar el widget
            self.log_text.configure(state='disabled')
            
    def exit_app(self):
        """
        Cierra la aplicación de forma controlada
        
        Solicita confirmación si hay un proceso en curso, cierra el navegador
        si el usuario lo desea, y guarda la configuración antes de salir.
        """
        try:
            # Verificar si hay un proceso en curso
            if self.processing:
                confirm_exit = messagebox.askyesno(
                    "Proceso en curso", 
                    "Hay un proceso de extracción en curso. ¿Realmente desea salir?",
                    icon='warning'
                )
                if not confirm_exit:
                    return
                    
            if self.driver:
                try:
                    close_browser = messagebox.askyesno(
                        "Cerrar navegador", 
                        "¿Desea cerrar también el navegador?",
                        icon='question'
                    )
                    if close_browser:
                        self.browser.close()
                        logger.info("Navegador cerrado correctamente")
                except:
                    logger.warning("No se pudo cerrar el navegador correctamente")
            
            # Guardar configuración antes de salir
            self.save_config()
            
            if self.root:
                self.root.destroy()
        except Exception as e:
            logger.error(f"Error al cerrar la aplicación: {e}")
            # En caso de error, forzar cierre
            if self.root:
                self.root.destroy()











    def add_new_client(self):
        """
        Muestra un diálogo para añadir un nuevo cliente a la base de datos.
        Solicita solo el número ERP y nombre del cliente, eliminando el campo Business Partner.
        """
        try:
            # Crear una ventana de diálogo personalizada
            dialog = tk.Toplevel(self.root)
            dialog.title("Añadir Nuevo Cliente")
            dialog.geometry("400x150")  # Reduzco el tamaño ya que eliminamos un campo
            dialog.resizable(False, False)
            dialog.grab_set()  # Modal window
            dialog.focus_set()
            
            # Configurar el diálogo
            dialog.grid_columnconfigure(1, weight=1)
            
            # Variables para los campos
            erp_var = tk.StringVar()
            name_var = tk.StringVar()
            
            # Etiquetas y campos de entrada
            ttk.Label(dialog, text="ERP Customer Number:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
            erp_entry = ttk.Entry(dialog, textvariable=erp_var, width=15)
            erp_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
            
            ttk.Label(dialog, text="Nombre del Cliente:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
            name_entry = ttk.Entry(dialog, textvariable=name_var, width=30)
            name_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
            
            # Marco para botones
            button_frame = ttk.Frame(dialog)
            button_frame.grid(row=3, column=0, columnspan=2, pady=15)
            
            # Función para guardar el cliente
            def save_client():
                erp = erp_var.get().strip()
                name = name_var.get().strip()
                
                # Validaciones
                if not erp:
                    messagebox.showerror("Error", "El número ERP es obligatorio", parent=dialog)
                    return
                    
                if not name:
                    messagebox.showerror("Error", "El nombre del cliente es obligatorio", parent=dialog)
                    return
                    
                # Validar que el ERP sea numérico
                if not erp.isdigit():
                    messagebox.showerror("Error", "El número ERP debe contener solo dígitos", parent=dialog)
                    return
                    
                # Guardar en la base de datos - ya no pasamos business_partner
                if self.db_manager.save_client(erp, name):
                    messagebox.showinfo("Éxito", f"Cliente {erp} - {name} añadido correctamente", parent=dialog)
                    
                    # Actualizar la lista de clientes en el combobox
                    clients = self.db_manager.get_clients()
                    self.client_combo['values'] = clients
                    
                    # Ajustar el ancho del dropdown para los clientes
                    from ui.main_window import adjust_combobox_dropdown_width
                    adjust_combobox_dropdown_width(self.client_combo)
                    
                    # Seleccionar el nuevo cliente con formato "ID - NOMBRE"
                    full_client = f"{erp} - {name}"
                    for i, client in enumerate(clients):
                        if client.startswith(erp):
                            self.client_combo.current(i)
                            self.select_client(client)
                            break
                    
                    dialog.destroy()
                else:
                    messagebox.showerror("Error", "No se pudo guardar el cliente", parent=dialog)
            
            # Botones
            ttk.Button(button_frame, text="Guardar", command=save_client).grid(row=0, column=0, padx=10)
            ttk.Button(button_frame, text="Cancelar", command=dialog.destroy).grid(row=0, column=1, padx=10)
            
            # Poner el foco en el primer campo
            erp_entry.focus_set()
            
            # Centrar diálogo en la ventana principal
            dialog.update_idletasks()
            width = dialog.winfo_width()
            height = dialog.winfo_height()
            x = (self.root.winfo_width() // 2) - (width // 2) + self.root.winfo_x()
            y = (self.root.winfo_height() // 2) - (height // 2) + self.root.winfo_y()
            dialog.geometry(f"{width}x{height}+{x}+{y}")
            
            # Esperar a que se complete el diálogo
            dialog.wait_window()
            
        except Exception as e:
            logger.error(f"Error al añadir nuevo cliente: {e}")
            if hasattr(self, 'root') and self.root:
                messagebox.showerror("Error", f"No se pudo añadir el cliente: {e}")











    def add_new_project(self):
        """
        Muestra un diálogo para añadir un nuevo proyecto a la base de datos.
        Solicita solo el ID de proyecto, cliente asociado y nombre, eliminando el campo Engagement Case.
        """
        try:
            # Verificar que hay clientes disponibles
            clients = self.db_manager.get_clients()
            if not clients:
                messagebox.showwarning("No hay clientes", "Debe añadir al menos un cliente antes de crear un proyecto.")
                return
            
            # Crear una ventana de diálogo personalizada
            dialog = tk.Toplevel(self.root)
            dialog.title("Añadir Nuevo Proyecto")
            dialog.geometry("450x200")  # Reduzco el tamaño ya que eliminamos un campo
            dialog.resizable(False, False)
            dialog.grab_set()  # Modal window
            dialog.focus_set()
            
            # Configurar el diálogo
            dialog.grid_columnconfigure(1, weight=1)
            
            # Variables para los campos
            project_id_var = tk.StringVar()
            client_var = tk.StringVar()
            name_var = tk.StringVar()
            
            # Si hay un cliente seleccionado, usarlo como valor predeterminado
            current_client_string = self.client_var.get() if hasattr(self, 'client_var') else ""
            current_client_id = current_client_string.split(" - ")[0] if " - " in current_client_string else current_client_string
            
            if current_client_id:
                # Buscar el cliente completo (con nombre) en la lista
                for client in clients:
                    if client.startswith(current_client_id):
                        client_var.set(client)
                        break
            
            # Etiquetas y campos de entrada
            ttk.Label(dialog, text="Case ID o Número de Proyecto:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
            project_entry = ttk.Entry(dialog, textvariable=project_id_var, width=15)
            project_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
            
            ttk.Label(dialog, text="Cliente:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
            client_combo = ttk.Combobox(dialog, textvariable=client_var, values=clients, width=30, state="readonly")
            client_combo.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
            
            ttk.Label(dialog, text="Nombre del Proyecto:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
            name_entry = ttk.Entry(dialog, textvariable=name_var, width=30)
            name_entry.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
            
            # Marco para botones
            button_frame = ttk.Frame(dialog)
            button_frame.grid(row=4, column=0, columnspan=2, pady=15)
            
            # Función para guardar el proyecto
            def save_project():
                project_id = project_id_var.get().strip()
                selected_client = client_var.get().strip()
                name = name_var.get().strip()
                
                # Validaciones
                if not project_id:
                    messagebox.showerror("Error", "El ID de proyecto es obligatorio", parent=dialog)
                    return
                    
                if not selected_client:
                    messagebox.showerror("Error", "Debes seleccionar un cliente", parent=dialog)
                    return
                    
                if not name:
                    messagebox.showerror("Error", "El nombre del proyecto es obligatorio", parent=dialog)
                    return
                    
                # Validar que el ID de proyecto sea numérico
                if not project_id.isdigit():
                    messagebox.showerror("Error", "El ID de proyecto debe contener solo dígitos", parent=dialog)
                    return
                    
                # Extraer el ERP number del cliente seleccionado (formato: "1025541 - Nombre")
                client_erp = selected_client.split(" - ")[0].strip()
                
                # Guardar en la base de datos - ya no pasamos engagement_case (cadena vacía)
                if self.db_manager.save_project(project_id, client_erp, name):
                    messagebox.showinfo("Éxito", f"Proyecto {project_id} - {name} añadido correctamente", parent=dialog)
                    
                    # Actualizar la lista de proyectos en el combobox
                    projects = self.db_manager.get_projects(client_erp)
                    self.project_combo['values'] = projects
                    
                    # Ajustar el ancho del dropdown para los proyectos
                    from ui.main_window import adjust_combobox_dropdown_width
                    adjust_combobox_dropdown_width(self.project_combo)
                    
                    # Seleccionar el nuevo proyecto con formato "ID - NOMBRE"
                    full_project = f"{project_id} - {name}"
                    for i, project in enumerate(projects):
                        if project.startswith(project_id):
                            self.project_combo.current(i)
                            self.select_project(project)
                            break
                    
                    dialog.destroy()
                else:
                    messagebox.showerror("Error", "No se pudo guardar el proyecto", parent=dialog)
            
            # Botones
            ttk.Button(button_frame, text="Guardar", command=save_project).grid(row=0, column=0, padx=10)
            ttk.Button(button_frame, text="Cancelar", command=dialog.destroy).grid(row=0, column=1, padx=10)
            
            # Poner el foco en el primer campo
            project_entry.focus_set()
            
            # Centrar diálogo en la ventana principal
            dialog.update_idletasks()
            width = dialog.winfo_width()
            height = dialog.winfo_height()
            x = (self.root.winfo_width() // 2) - (width // 2) + self.root.winfo_x()
            y = (self.root.winfo_height() // 2) - (height // 2) + self.root.winfo_y()
            dialog.geometry(f"{width}x{height}+{x}+{y}")
            
            # Esperar a que se complete el diálogo
            dialog.wait_window()
            
        except Exception as e:
            logger.error(f"Error al añadir nuevo proyecto: {e}")
            if hasattr(self, 'root') and self.root:
                messagebox.showerror("Error", f"No se pudo añadir el proyecto: {e}")











    def select_client(self, client_string):
        """
        Maneja la selección de un cliente desde el combobox
        
        Args:
            client_string (str): String en formato "1025541 - Nombre del cliente"
        """
        try:
            if not client_string or len(client_string) < 3:
                return
                    
            # Extraer el ERP number del string "1025541 - Nombre del cliente"
            parts = client_string.split(" - ")
            erp_number = parts[0].strip()
            
            # Establecer el valor en el Entry
            self.client_var.set(client_string)
            logger.info(f"Cliente seleccionado: {client_string}")
            
            # Actualizar inmediatamente la interfaz para confirmar el cambio
            if self.root:
                self.root.update_idletasks()
            
            # Actualizar la lista de proyectos para este cliente
            projects = self.db_manager.get_projects(erp_number)
            self.project_combo['values'] = projects
            
            # Ajustar el ancho del dropdown para los proyectos
            from ui.main_window import adjust_combobox_dropdown_width
            adjust_combobox_dropdown_width(self.project_combo)
            
            # Si hay proyectos disponibles, seleccionar el primero
            if projects:
                self.project_combo.current(0)
                self.select_project(projects[0])
                        
            # Actualizar el uso de este cliente
            self.db_manager.update_client_usage(erp_number)
            self.save_config()
        except Exception as e:
            logger.error(f"Error al seleccionar cliente: {e}")









    def select_project(self, project_string):
        """
        Maneja la selección de un proyecto desde el combobox
        
        Args:
            project_string (str): String en formato "20096444 - Nombre del proyecto"
        """
        try:
            if not project_string or len(project_string) < 3:
                return
                    
            # Extraer el ID del proyecto del string "20096444 - Nombre del proyecto"
            parts = project_string.split(" - ")
            project_id = parts[0].strip()
            
            # Establecer el valor en el Entry - AQUÍ ESTÁ EL CAMBIO
            # En lugar de solo establecer el ID, mantener todo el string con nombre
            self.project_var.set(project_string)
            logger.info(f"Proyecto seleccionado: {project_string}")
            
            # Actualizar inmediatamente la interfaz para confirmar el cambio
            if self.root:
                self.root.update_idletasks()
            
            # Actualizar el uso de este proyecto
            self.db_manager.update_project_usage(project_id)
            self.save_config()
        except Exception as e:
            logger.error(f"Error al seleccionar proyecto: {e}")











    def _replace_standard_messageboxes(self):
        """
        Reemplaza los messagebox estándar por nuestros diálogos personalizados
        con mejor formato y alineación de texto.
        
        Este método modifica el comportamiento de messagebox para usar nuestros
        diálogos personalizados que manejan mejor la alineación del texto.
        """
        try:
            # Intentar importar los diálogos personalizados
            from ui.custom_dialogs import (
                show_info, show_warning, show_error, show_question
            )
            
            # Guardar referencia a funciones originales
            self._original_showinfo = messagebox.showinfo
            self._original_showwarning = messagebox.showwarning
            self._original_showerror = messagebox.showerror
            self._original_askokcancel = messagebox.askokcancel
            
            # Reemplazar con las versiones mejoradas pero preservando la interfaz original
            def custom_showinfo(title, message, **kwargs):
                if self.root:
                    return show_info(self.root, title, message)
                else:
                    return self._original_showinfo(title, message, **kwargs)
                    
            def custom_showwarning(title, message, **kwargs):
                if self.root:
                    return show_warning(self.root, title, message)
                else:
                    return self._original_showwarning(title, message, **kwargs)
                    
            def custom_showerror(title, message, **kwargs):
                if self.root:
                    return show_error(self.root, title, message)
                else:
                    return self._original_showerror(title, message, **kwargs)
                    
            def custom_askokcancel(title, message, **kwargs):
                # Para diálogos que requieren respuesta, todavía usamos los originales
                # ya que nuestros personalizados no tienen esa funcionalidad aún
                return self._original_askokcancel(title, message, **kwargs)
            
            # Aplicar los reemplazos a nivel global
            messagebox.showinfo = custom_showinfo
            messagebox.showwarning = custom_showwarning
            messagebox.showerror = custom_showerror
            # No reemplazamos askokcancel ya que necesitamos su funcionalidad de respuesta
            
            return True
            
        except ImportError:
            logger.debug("Diálogos personalizados no disponibles, usando messagebox estándar")
            return False
        except Exception as e:
            logger.error(f"Error al reemplazar messageboxes: {e}")
            return False












    def start_browser(self):
        """
        Inicia el navegador desde la interfaz gráfica
        
        Este método prepara la interfaz y ejecuta la inicialización del navegador
        en un hilo separado para no bloquear la interfaz.
        """
        try:
            # Verificar si hay un proceso en curso
            if self.processing:
                messagebox.showwarning("Proceso en curso", "Hay un proceso de extracción en curso.")
                return
                
            # Asegurarse de que no haya un navegador ya abierto
            if self.driver:
                messagebox.showinfo("Navegador ya iniciado", "El navegador ya está iniciado.")
                return
                
            # Actualizar la interfaz para mostrar que se está iniciando el navegador
            self.status_var.set("Iniciando navegador...")
            if self.root:
                self.root.update()
            
            # Iniciar el navegador en un hilo separado
            threading.Thread(target=self._start_browser_thread, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Error al iniciar el navegador: {e}")
            self.status_var.set(f"Error: {e}")
            messagebox.showerror("Error", f"Error al iniciar el navegador: {e}")









    def _start_browser_thread(self):
        """
        Método para ejecutar la inicialización del navegador en un hilo separado
        
        Realiza la conexión con el navegador y navega a la URL inicial de SAP.
        """
        try:
            if self.connect_to_browser():
                logger.info("Navegador iniciado")
                
                # Actualizar la interfaz en el hilo principal
                if self.root:
                    self.root.after(0, lambda: self.status_var.set("Navegador iniciado. Navegando a SAP..."))
                
                # Obtener valores de cliente y proyecto
                erp_number = self.client_var.get() if hasattr(self, 'client_var') and self.client_var else "1025541"
                project_id = self.project_var.get() if hasattr(self, 'project_var') and self.project_var else "20096444"
                
                # Navegar a la URL de SAP con parámetros específicos
                self.browser.navigate_to_sap(erp_number, project_id)
                
                # Esperar a que se cargue completamente la página y maneje autenticación si es necesario
                self.browser.handle_authentication()
                time.sleep(3)  # Dar tiempo para que la interfaz se estabilice
                
                # NUEVA SECUENCIA: Configurar columnas después de navegación
                # Actualizar la interfaz en el hilo principal
                if self.root:
                    self.root.after(0, lambda: self.status_var.set("Configurando columnas visibles..."))
                
                # 1. Hacer clic en el botón de ajustes usando el método mejorado
                if self.browser.enhanced_click_settings_button():
                    logger.info("✅ Botón de ajustes pulsado correctamente")
                    
                    # Esperar a que se abra el panel de ajustes
                    time.sleep(1) #Modificado de 2 a 1 segundo
                    
                    # 2. Usar el nuevo método de secuencia exacta de teclas
                    if self.browser.perform_exact_keyboard_sequence():
                        logger.info("✅ Columnas configuradas correctamente mediante secuencia exacta de teclas")
                        
                        # Esperar a que se recargue la tabla con las nuevas columnas
                        time.sleep(1) #Modificado de 3 a 1 segundo
                    else:
                        logger.warning("⚠️ No se pudieron configurar todas las columnas")
                        
                        # Informar al usuario en el hilo principal
                        if self.root:
                            self.root.after(0, lambda: messagebox.showinfo(
                                "Configuración manual",
                                "No se pudieron configurar todas las columnas automáticamente.\n\n"
                                "Por favor, realice estos pasos manualmente:\n"
                                "1. 5 tabs\n"
                                "2. 2 flechas a la derecha\n"
                                "3. Enter (para Select Columns)\n"
                                "4. 3 tabs\n"
                                "5. Enter (para Select All)\n"
                                "6. 2 tabs\n"
                                "7. Enter (para OK)"
                            ))
                else:
                    logger.warning("⚠️ No se pudo hacer clic en el botón de ajustes")
                    
                    # Informar al usuario en el hilo principal
                    if self.root:
                        self.root.after(0, lambda: messagebox.showwarning(
                            "Acción Manual Requerida",
                            "No se pudo hacer clic en el botón de ajustes automáticamente.\n\n"
                            "Por favor, haga clic manualmente en el botón de ajustes (engranaje) ubicado en la esquina inferior derecha."
                        ))
                
                # Mostrar instrucciones en el hilo principal
                if self.root:
                    self.root.after(0, lambda: self.status_var.set("Navegación completada. Inicie la extracción cuando esté listo."))
                    self.root.after(0, self._show_extraction_instructions)
            else:
                if self.root:
                    self.root.after(0, lambda: self.status_var.set("Error al iniciar el navegador"))
                    self.root.after(0, lambda: messagebox.showerror("Error", "No se pudo iniciar el navegador. Revise el log para más detalles."))
        except Exception as e:
            logger.error(f"Error en hilo de navegador: {e}")
            if self.root:
                self.root.after(0, lambda: self.status_var.set(f"Error: {e}"))
                self.root.after(0, lambda: messagebox.showerror("Error", f"Error al iniciar el navegador: {e}"))





    def _show_extraction_instructions(self):
        """
        Muestra instrucciones para la extracción después de la navegación automática
        utilizando el diálogo personalizado con mejor formato.
        
        Presenta un mensaje con información sobre el cliente y proyecto actuales,
        incluyendo sus nombres, y guía al usuario sobre los siguientes pasos.
        """
        # Obtener valores actuales
        erp_number = self.client_var.get()
        project_id = self.project_var.get()
        
        # Obtener nombres de cliente y proyecto desde la base de datos
        client_name = ""
        project_name = ""
        
        # Buscar el nombre del cliente
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            # Consultar nombre del cliente
            cursor.execute("SELECT name FROM clients WHERE erp_number = ?", (erp_number,))
            client_result = cursor.fetchone()
            if client_result:
                client_name = client_result[0]
                
            # Consultar nombre del proyecto
            cursor.execute("SELECT name FROM projects WHERE project_id = ?", (project_id,))
            project_result = cursor.fetchone()
            if project_result:
                project_name = project_result[0]
                
        except Exception as e:
            logger.error(f"Error al obtener nombres de cliente/proyecto: {e}")
        finally:
            if conn:
                conn.close()
        
        # Formatear la información con los nombres
        client_info = f"{erp_number}"
        if client_name:
            client_info += f" - {client_name}"
            
        project_info = f"{project_id}"
        if project_name:
            project_info += f" - {project_name}"
        
        try:
            # Intentar usar el diálogo personalizado si está disponible
            from ui.custom_dialogs import show_extraction_instructions
            show_extraction_instructions(self.root, client_info, project_info)
        except ImportError:
            # Fallback a messagebox estándar si no está disponible el diálogo personalizado
            instructions = f"""
    La aplicación ha navegado automáticamente a la página de SAP con:

    Cliente: {client_info}
    Proyecto: {project_info}

    Por favor:
    1. Verifica que has iniciado sesión correctamente
    2. Comprueba que puedes ver las recomendaciones para el cliente
    3. Cuando quieras comenzar, haz clic en 'Iniciar Extracción'
            """
            
            messagebox.showinfo("Instrucciones de Extracción", instructions)



    def load_config(self):
        """
        Carga la configuración guardada desde un archivo JSON
        
        Restaura los valores de cliente, proyecto y ruta del archivo Excel
        de ejecuciones anteriores.
        """
        try:
            config_path = os.path.join('config', 'config.json')
            
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                        
                    if 'client' in config and config['client']:
                        client_id = config['client'].strip()
                        
                        # Buscar el cliente completo (con nombre) en la base de datos
                        found = False
                        clients = self.db_manager.get_clients()
                        for client in clients:
                            if client.startswith(client_id):
                                self.client_var.set(client)
                                found = True
                                break
                        
                        # Si no se encuentra, usar solo el ID
                        if not found:
                            self.client_var.set(client_id)
                            
                    if 'project' in config and config['project']:
                        project_id = config['project'].strip()
                        
                        # Buscar el proyecto completo (con nombre) en la base de datos
                        found = False
                        client_id = self.client_var.get().split(" - ")[0] if " - " in self.client_var.get() else self.client_var.get()
                        projects = self.db_manager.get_projects(client_id)
                        for project in projects:
                            if project.startswith(project_id):
                                self.project_var.set(project)
                                found = True
                                break
                        
                        # Si no se encuentra, usar solo el ID
                        if not found:
                            self.project_var.set(project_id)
                            
                    if 'excel_path' in config and os.path.exists(config['excel_path']):
                        self.excel_file_path = config['excel_path']
                        self.excel_manager.file_path = config['excel_path']
                        if hasattr(self, 'excel_filename_var') and self.excel_filename_var:
                            self.excel_filename_var.set(f"Archivo: {os.path.basename(config['excel_path'])}")
                            
                    logger.info("Configuración cargada correctamente")
        except Exception as e:
            logger.error(f"Error al cargar configuración: {e}")




    def save_config(self):
        """
        Guarda la configuración actual en un archivo JSON
        
        Almacena los valores actuales de cliente, proyecto y ruta del archivo Excel
        para restaurarlos en futuras ejecuciones.
        """
        try:
            # Extraer los IDs de cliente y proyecto (solo los números)
            client_string = self.client_var.get()
            project_string = self.project_var.get()
            
            client_id = client_string.split(" - ")[0] if " - " in client_string else client_string
            project_id = project_string.split(" - ")[0] if " - " in project_string else project_string
            
            config = {
                'client': client_id,
                'project': project_id,
                'excel_path': self.excel_file_path
            }
            
            config_dir = "config"
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
                    
            config_path = os.path.join(config_dir, 'config.json')
            
            with open(config_path, 'w') as f:
                json.dump(config, f)
                    
            logger.debug("Configuración guardada correctamente")
        except Exception as e:
            logger.error(f"Error al guardar configuración: {e}")





    def create_gui(self):
        """
        Crea la interfaz gráfica completa de la aplicación
        
        Este método configura la ventana principal, los paneles, controles y
        eventos de la interfaz gráfica de usuario. También inicializa los
        diálogos personalizados para mejor formato de texto.
        """
        from ui.main_window import MainWindow
        
        # Crear la ventana principal
        self.root = tk.Tk()
        
        # Inicializar variables
        self.client_var = tk.StringVar(value="1025541") 
        self.project_var = tk.StringVar(value="20096444")
        
        # Crear la interfaz utilizando la clase MainWindow
        main_window = MainWindow(self.root, self)
        main_window.setup_ui()
        
        # Configurar logger GUI y carga de configuración
        self.setup_gui_logger()
        self.load_config()
        
        # Reemplazar los messagebox estándar con nuestros diálogos personalizados
        self._replace_standard_messageboxes()






    def main_gui(self):
        """
        Punto de entrada principal con interfaz gráfica
        
        Crea la interfaz y ejecuta el bucle principal de eventos.
        """
        self.create_gui()
        if self.root:
            self.root.mainloop()






# Métodos para ejecución en modo consola
def run_console_mode():
    """
    Ejecuta la aplicación en modo consola sin interfaz gráfica
    
    Returns:
        bool: True si la extracción fue exitosa, False en caso contrario
    """
    extractor = IssuesExtractor()
    
    # Solicitar información al usuario
    print("\n===== SAP Issues Extractor - Modo Consola =====\n")
    
    # Cliente
    erp_number = input("Ingresa el ERP Customer Number (Ej: 1025541): ").strip()
    extractor.client_var = type('obj', (object,), {'get': lambda: erp_number})
    
    # Proyecto
    project_id = input("Ingresa el Case ID o número del proyecto (Ej: 20096444): ").strip()
    extractor.project_var = type('obj', (object,), {'get': lambda: project_id})
    
    # Archivo Excel
    print("\nSeleccione un archivo Excel para guardar los resultados:")
    extractor.choose_excel_file()
    
    # Confirmar y ejecutar
    print(f"\nConfiguración actual:")
    print(f"  - Cliente: {erp_number}")
    print(f"  - Proyecto: {project_id}")
    print(f"  - Archivo Excel: {os.path.basename(extractor.excel_file_path)}")
    
    confirm = input("\n¿Desea iniciar la extracción? (S/N): ").strip().upper()
    if confirm != 'S':
        print("Extracción cancelada por el usuario.")
        return False
    
    print("\nIniciando proceso de extracción...\n")
    result = extractor.run_extraction()
    
    if result:
        print("\n¡Extracción completada con éxito!")
    else:
        print("\nLa extracción falló. Revise el log para más detalles.")
    
    return result