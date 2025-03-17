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
        





    def run_extraction(self):
        """
        Ejecuta el proceso completo de extracción
        
        Este método coordina todo el flujo de extracción, desde la conexión
        con el navegador hasta la obtención de los datos.
        
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

            # Obtener valores de cliente y proyecto - APLICAR TRIM PARA ELIMINAR ESPACIOS
            erp_number = self.client_var.get().strip() if hasattr(self, 'client_var') and self.client_var else ""
            project_id = self.project_var.get().strip() if hasattr(self, 'project_var') and self.project_var else ""

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
                    if hasattr(self.browser, '_use_ui5_javascript'):
                        if self.browser._use_ui5_javascript(erp_number):
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
                            time.sleep(3)  # Dar tiempo para que se procese la selección
            
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
            
            # Hacer clic en el botón de búsqueda
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set("Realizando búsqueda...")
                
            # Hacer clic en búsqueda utilizando el nuevo método
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
            
            # Esperar a que se carguen los resultados de la búsqueda
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set("Esperando resultados de búsqueda...")
                
            # Esperar resultados utilizando el nuevo método
            if not self.browser.wait_for_search_results():
                logger.warning("No se pudo confirmar la carga de resultados")
                # Dar tiempo adicional y continuar de todos modos
                time.sleep(5)
            
            # Continuar con la detección y extracción de issues
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set("Navegando a la pestaña Issues...")
            
            # Navegar a la pestaña Issues
            if not self.navigate_to_issues_tab():
                logger.warning("No se pudo navegar automáticamente a la pestaña Issues")
                if hasattr(self, 'root') and self.root:
                    messagebox.showwarning("Navegación Manual Requerida", 
                        "Por favor, navegue manualmente a la pestaña 'Issues' y luego haga clic en Continuar.")
                    result = messagebox.askokcancel("Confirmación", "¿Ha navegado a la pestaña Issues?")
                    if not result:
                        return False
            
            # PASO OBLIGATORIO: Hacer clic en el botón de ajustes
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set("Accediendo a ajustes...")
                
            # Intentar hacer clic en ajustes de forma automática
            if not self.browser.click_settings_button():
                logger.warning("No se pudo hacer clic automáticamente en el botón de ajustes")
                # Solicitar acción manual ya que este paso es obligatorio
                if hasattr(self, 'root') and self.root:
                    messagebox.showwarning("Acción Manual Requerida", 
                        "No se pudo hacer clic en el botón de ajustes automáticamente.\n\n"
                        "Por favor, haga clic manualmente en el botón de ajustes (engranaje) ubicado en la esquina inferior derecha.")
                    result = messagebox.askokcancel("Confirmación", "¿Ha hecho clic en el botón de ajustes?")
                    if not result:
                        logger.error("Usuario canceló después de no poder hacer clic en ajustes")
                        if hasattr(self, 'status_var') and self.status_var:
                            self.status_var.set("Proceso cancelado: No se pudo acceder a ajustes")
                        return False
            
            # Esperar un momento para que se abra el panel de ajustes
            time.sleep(2)
            
            # Realizar la extracción
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
                    time.sleep(3)
                    return True
            except:
                pass
                
            logger.warning("No se pudo navegar a la pestaña Issues")
            return False
            
        except Exception as e:
            logger.error(f"Error al navegar a la pestaña Issues: {e}")
            return False
    
    
    
    
    
    
    
    def perform_extraction(self):
        """
        Método principal para ejecutar el proceso de extracción.
        
        Este método coordina la extracción de datos una vez que la navegación
        y selección de cliente/proyecto ha sido completada.
        
        Returns:
            bool: True si la extracción fue exitosa, False en caso contrario
        """
        try:
            # Marcar como procesando
            self.processing = True
            
            logger.info("Comenzando proceso de extracción...")
            
            # Actualizar la interfaz si existe
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set("Comenzando proceso de extracción...")
                if self.root:
                    self.root.update()
            
            # Verificación de si estamos en la página correcta
            in_issues_page = False
            
            # Estrategia 1: Buscar el texto "Issues (número)"
            try:
                issues_title_elements = self.driver.find_elements(
                    By.XPATH, 
                    "//div[contains(text(), 'Issues') and contains(text(), '(')]"
                )
                if issues_title_elements:
                    logger.info(f"Página de Issues detectada por título: {issues_title_elements[0].text}")
                    in_issues_page = True
            except Exception as e:
                logger.debug(f"No se pudo detectar título de Issues: {e}")
            
            # Estrategia 2: Verificar si hay filas de datos visibles
            if not in_issues_page:
                issue_rows = self.browser.find_table_rows(highlight=False)
                if len(issue_rows) > 0:
                    logger.info(f"Se detectaron {len(issue_rows)} filas de datos que parecen issues")
                    in_issues_page = True
            
            # Estrategia 3: Verificar encabezados de columna típicos
            if not in_issues_page:
                try:
                    column_headers = self.driver.find_elements(
                        By.XPATH,
                        "//div[text()='Title'] | //div[text()='Type'] | //div[text()='Priority'] | //div[text()='Status']"
                    )
                    if len(column_headers) >= 3:
                        logger.info(f"Se detectaron encabezados de columna típicos de issues: {len(column_headers)}")
                        in_issues_page = True
                except Exception as e:
                    logger.debug(f"No se pudieron detectar encabezados de columna: {e}")
            
            # Si aún no estamos seguros, intentar hacer clic en la pestaña Issues
            if not in_issues_page:
                logger.warning("No se detectó la página de Issues. Intentando hacer clic en la pestaña...")
                
                if not self.navigate_to_issues_tab():
                    logger.warning("No se pudo navegar a la pestaña de Issues")
                else:
                    in_issues_page = True
                    
                # Esperar a que cargue la página
                time.sleep(3)
            
            # ====== NOVEDAD: SELECCIÓN DE TODAS LAS COLUMNAS ======
            # Seleccionar todas las columnas disponibles para maximizar datos extraídos
            if hasattr(self.browser, 'select_all_visible_columns'):
                logger.info("Intentando seleccionar todas las columnas disponibles...")
                
                # Actualizar la interfaz si existe
                if hasattr(self, 'status_var') and self.status_var:
                    self.status_var.set("Configurando columnas visibles...")
                    if self.root:
                        self.root.update()
                        
                columns_configured = self.browser.select_all_visible_columns()
                
                if columns_configured:
                    logger.info("✅ Columnas configuradas correctamente para extracción completa")
                    
                    # Esperar a que se recargue la tabla con las nuevas columnas
                    time.sleep(3)
                else:
                    logger.warning("⚠️ No se pudieron configurar todas las columnas")
            else:
                logger.warning("La función de selección de columnas no está disponible")
            
            # Intentar extracción con reintentos
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    logger.info(f"Intento de extracción {attempt+1}/{max_attempts}")
                    
                    # Actualizar la interfaz si existe
                    if hasattr(self, 'status_var') and self.status_var:
                        self.status_var.set(f"Intento de extracción {attempt+1}/{max_attempts}...")
                    
                    issues_data = self.browser.extract_issues_data()
                    
                    if issues_data:
                        logger.info(f"Extracción exitosa: {len(issues_data)} issues encontrados")
                        
                        # Actualizar Excel con los datos extraídos
                        if self.excel_file_path:
                            self.update_excel(issues_data)
                        else:
                            logger.warning("No se ha seleccionado archivo Excel para guardar los datos")
                            
                            if hasattr(self, 'status_var') and self.status_var:
                                self.status_var.set("Advertencia: No se ha seleccionado archivo Excel")
                            
                            if self.root:
                                excel_path = self.choose_excel_file()
                                if excel_path:
                                    self.update_excel(issues_data)
                        
                        self.processing = False
                        return True
                    else:
                        logger.warning(f"No se encontraron issues en el intento {attempt+1}")
                        
                        # Si no es el último intento, esperar y reintentar
                        if attempt < max_attempts - 1:
                            logger.info("Esperando antes de reintentar...")
                            time.sleep(5)
                        else:
                            logger.error("Todos los intentos de extracción fallaron")
                            
                            if hasattr(self, 'status_var') and self.status_var:
                                self.status_var.set("Error: No se encontraron issues después de varios intentos")
                            
                            if self.root:
                                messagebox.showerror(
                                    "Error de Extracción", 
                                    "No se pudieron encontrar issues después de varios intentos. Verifique que está en la página correcta y que existen issues para extraer."
                                )
                            
                            self.processing = False
                            return False
                except Exception as e:
                    logger.error(f"Error en el intento {attempt+1}: {e}")
                    
                    # Si no es el último intento, esperar y reintentar
                    if attempt < max_attempts - 1:
                        logger.info("Esperando antes de reintentar...")
                        time.sleep(5)
                    else:
                        logger.error(f"Todos los intentos de extracción fallaron: {e}")
                        
                        if hasattr(self, 'status_var') and self.status_var:
                            self.status_var.set(f"Error de extracción: {e}")
                        
                        if self.root:
                            messagebox.showerror(
                                "Error de Extracción", 
                                f"Se produjo un error durante la extracción: {e}"
                            )
                        
                        self.processing = False
                        return False
            
            # Si llegamos aquí, todos los intentos fallaron
            logger.error("Extracción fallida después de varios intentos")
            
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set("Error: Extracción fallida")
            
            self.processing = False
            return False
            
        except Exception as e:
            logger.error(f"Error general en el proceso de extracción: {e}")
            
            # Actualizar la interfaz si existe
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set(f"Error: {e}")
            
            self.processing = False
            return False







    def _fill_fields_and_extract(self, erp_number, project_id):
        """
        Rellena los campos y luego ejecuta la extracción
        
        Este método se ejecuta en un hilo separado para no bloquear la interfaz
        gráfica durante el proceso de extracción.
        
        Args:
            erp_number (str): Número ERP del cliente
            project_id (str): ID del proyecto
            
        Returns:
            bool: True si la extracción fue exitosa, False en caso contrario
        """
        try:
            # Actualizar la interfaz
            if hasattr(self, 'status_var'):
                self.status_var.set("Seleccionando cliente...")
                if self.root:
                    self.root.update()
            
            # 1. Seleccionar cliente
            client_selected = False
            if not self.browser.select_customer_automatically(erp_number):
                try:
                    customer_field = self.driver.find_element(By.XPATH, "//input[contains(@placeholder, 'Customer')]")
                    if customer_field:
                        customer_field.clear()
                        customer_field.send_keys(erp_number)
                        time.sleep(1)
                        
                        # Intento directo con teclas DOWN y ENTER
                        customer_field.send_keys(Keys.DOWN)
                        time.sleep(0.5)
                        customer_field.send_keys(Keys.ENTER)
                        time.sleep(1)
                        
                        # Verificar si funcionó
                        if self.browser._verify_client_selection_strict(erp_number):
                            logger.info("Cliente seleccionado con método directo de teclas")
                            client_selected = True
                        # Si no, intentar con el método de dropdown
                        elif hasattr(self.browser, '_interact_with_dropdown'):
                            if self.browser._interact_with_dropdown(customer_field, erp_number):
                                logger.info("Cliente seleccionado con método específico para dropdown")
                                client_selected = True
                except Exception as e:
                    logger.debug(f"Error al intentar método alternativo de dropdown: {e}")
                    
                if not client_selected:
                    logger.warning("No se pudo seleccionar cliente automáticamente")
                    # Mostrar mensaje al usuario
                    if self.root:
                        self.root.after(0, lambda: messagebox.showwarning(
                            "Selección Manual Requerida", 
                            "No se pudo seleccionar el cliente automáticamente.\n\n"
                            "Por favor, seleccione manualmente el cliente."
                        ))
                        # Esperar confirmación del usuario
                        result = messagebox.askokcancel("Confirmación", "¿Ha seleccionado el cliente?")
                        if not result:
                            return False
                        client_selected = True  # El usuario confirmó que seleccionó manualmente
                        time.sleep(3)  # Dar tiempo para que se procese la selección
            else:
                logger.info(f"Cliente {erp_number} seleccionado con éxito")
                client_selected = True
            
            # Actualizar la interfaz
            if hasattr(self, 'status_var'):
                self.status_var.set("Seleccionando proyecto automáticamente...")
                if self.root:
                    self.root.update()
            
            # 2. Implementar reintentos para la selección de proyecto
            logger.info("Esperando a que cargue la lista de proyectos...")
            time.sleep(5)  # Espera inicial más larga

            max_attempts = 3
            project_selected = False

            for attempt in range(max_attempts):
                logger.info(f"Intento {attempt+1}/{max_attempts} de selección de proyecto")
                
                if self.browser.select_project_automatically(project_id):
                    logger.info(f"Proyecto {project_id} seleccionado con éxito en el intento {attempt+1}")
                    project_selected = True
                    break
                else:
                    logger.warning(f"Intento {attempt+1} fallido, esperando antes de reintentar...")
                    time.sleep(3)  # Esperar entre reintentos

            if not project_selected:
                logger.warning("No se pudo seleccionar proyecto automáticamente después de varios intentos")
                # Mostrar mensaje al usuario
                if self.root:
                    self.root.after(0, lambda: messagebox.showwarning(
                        "Selección Manual Requerida", 
                        "No se pudo seleccionar el proyecto automáticamente.\n\n"
                        "Por favor, seleccione manualmente el proyecto."
                    ))
                    result = messagebox.askokcancel("Confirmación", "¿Ha seleccionado el proyecto?")
                    if not result:
                        return False
                    time.sleep(3)  # Dar tiempo para selección manual
            
            # 3. Hacer clic en el botón de búsqueda
            if hasattr(self, 'status_var'):
                self.status_var.set("Realizando búsqueda...")
                if self.root:
                    self.root.update()
            
            time.sleep(1)
            self.browser.click_search_button()
            
            # 4. Continuar con la extracción
            logger.info("Iniciando proceso de extracción")
            if hasattr(self, 'status_var'):
                self.status_var.set("Extrayendo datos...")
                if self.root:
                    self.root.update()
            
            self.perform_extraction()
            
        except Exception as e:
            logger.error(f"Error al rellenar campos y extraer: {e}")
            if hasattr(self, 'status_var'):
                self.status_var.set(f"Error: {e}")
            
            if self.root:
                self.root.after(0, lambda: messagebox.showerror(
                    "Error", 
                    f"Error al rellenar campos: {e}"
                ))
                
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
            self.client_var.set(erp_number)
            logger.info(f"Cliente seleccionado: {erp_number}")
            
            # Actualizar inmediatamente la interfaz para confirmar el cambio
            if self.root:
                self.root.update_idletasks()
            
            # Actualizar la lista de proyectos para este cliente
            projects = self.db_manager.get_projects(erp_number)
            self.project_combo['values'] = projects
            
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
            
            # Establecer el valor en el Entry
            self.project_var.set(project_id)
            logger.info(f"Proyecto seleccionado: {project_id}")
            
            # Actualizar inmediatamente la interfaz para confirmar el cambio
            if self.root:
                self.root.update_idletasks()
            
            # Actualizar el uso de este proyecto
            self.db_manager.update_project_usage(project_id)
            self.save_config()
        except Exception as e:
            logger.error(f"Error al seleccionar proyecto: {e}")
            
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
        
        Presenta un mensaje con información sobre el cliente y proyecto actuales,
        y guía al usuario sobre los siguientes pasos.
        """
        # Obtener valores actuales
        erp_number = self.client_var.get()
        project_id = self.project_var.get()
        
        instructions = f"""
        La aplicación ha navegado automáticamente a la página de SAP con:
        
        Cliente: {erp_number}
        Proyecto: {project_id}
        
        Por favor:
        1. Verifique que ha iniciado sesión correctamente
        2. Compruebe que se muestran los issues del proyecto
        3. Cuando esté listo, haga clic en 'Iniciar Extracción'
        """
        
        messagebox.showinfo("Instrucciones de Extracción", instructions)
    
    def start_extraction(self):
        """
        Inicia el proceso de extracción desde la interfaz gráfica
        
        Realiza validaciones iniciales y ejecuta la extracción en un hilo
        separado para no bloquear la interfaz gráfica.
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
                
            # Obtener valores de cliente y proyecto
            erp_number = self.client_var.get()
            project_id = self.project_var.get()
            
            # Iniciar extracción en un hilo separado para no bloquear la GUI
            threading.Thread(
                target=self._fill_fields_and_extract, 
                args=(erp_number, project_id),
                daemon=True
            ).start()
            
        except Exception as e:
            logger.error(f"Error al iniciar extracción: {e}")
            self.status_var.set(f"Error: {e}")
            messagebox.showerror("Error", f"Error al iniciar extracción: {e}")

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
            
    def save_config(self):
        """
        Guarda la configuración actual en un archivo JSON
        
        Almacena los valores actuales de cliente, proyecto y ruta del archivo Excel
        para restaurarlos en futuras ejecuciones.
        """
        try:
            config = {
                'client': self.client_var.get(),
                'project': self.project_var.get(),
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
                        self.client_var.set(config['client'].strip())
                        
                    if 'project' in config and config['project']:
                        self.project_var.set(config['project'].strip())
                        
                    if 'excel_path' in config and os.path.exists(config['excel_path']):
                        self.excel_file_path = config['excel_path']
                        self.excel_manager.file_path = config['excel_path']
                        if hasattr(self, 'excel_filename_var') and self.excel_filename_var:
                            self.excel_filename_var.set(f"Archivo: {os.path.basename(config['excel_path'])}")
                        
                    logger.info("Configuración cargada correctamente")
        except Exception as e:
            logger.error(f"Error al cargar configuración: {e}")
            
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
                
    def create_gui(self):
        """
        Crea la interfaz gráfica completa de la aplicación
        
        Este método configura la ventana principal, los paneles, controles y
        eventos de la interfaz gráfica de usuario.
        
        La implementación detallada de este método debería estar en el módulo ui/main_window.py,
        pero aquí se mantiene una versión simplificada para compatibilidad.
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
    erp_number = input("Introduzca el número ERP del cliente (Ej: 1025541): ").strip()
    extractor.client_var = type('obj', (object,), {'get': lambda: erp_number})
    
    # Proyecto
    project_id = input("Introduzca el ID del proyecto (Ej: 20096444): ").strip()
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
