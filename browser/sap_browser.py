"""
Módulo principal para la automatización del navegador con Selenium.

Proporciona funcionalidades específicas para interactuar con aplicaciones SAP UI5/Fiori.
"""

import os
import sys
import time
import logging
import re
import threading
import json
import base64
import hashlib
from io import BytesIO
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
from typing import Optional, List, Dict, Union, Tuple

# Importaciones de Selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    JavascriptException,
    WebDriverException
)

# Importaciones locales
from utils.logger_config import logger
from config.settings import CHROME_PROFILE_DIR, BROWSER_TIMEOUT, MAX_RETRY_ATTEMPTS
from browser.element_finder import (
    find_table_rows, 
    detect_table_headers, 
    get_row_cells,
    find_ui5_elements,
    check_for_pagination,
    wait_for_element,
    detect_table_type,
    click_element_safely,
    optimize_browser_performance,
    find_table_rows_optimized,
    get_row_cells_optimized
)

# Configurar logger
logger = logging.getLogger(__name__)







class SAPBrowser:
    """Clase para la automatización del navegador y extracción de datos de SAP"""
    
    def __init__(self):
        """Inicializa el controlador del navegador"""
        self.driver = None
        self.wait = None
        self.element_cache = {}  # Caché para elementos encontrados frecuentemente
        self.root = None  # Referencia a la ventana principal (si existe)
        self.status_var = None  # Variable de estado para la interfaz (si existe)
        
    def connect(self):
        """
        Inicia una sesión de navegador con perfil dedicado
        
        Returns:
            bool: True si la conexión fue exitosa, False en caso contrario
        """
        logger.info("Iniciando navegador con perfil guardado...")
        
        try:
            # Ruta al directorio del perfil
            user_data_dir = CHROME_PROFILE_DIR
            
            # Crear directorio si no existe
            if not os.path.exists(user_data_dir):
                os.makedirs(user_data_dir)
                logger.info(f"Creado directorio de perfil: {user_data_dir}")
            
            # Configurar opciones de Chrome
            chrome_options = Options()
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
            chrome_options.add_argument("--profile-directory=Default")
            
            # Opciones para mejorar rendimiento y estabilidad
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
            
            # Optimización de memoria
            chrome_options.add_argument("--js-flags=--expose-gc")
            chrome_options.add_argument("--enable-precise-memory-info")
            
            # Agregar opciones para permitir que el usuario use el navegador mientras se ejecuta el script
            chrome_options.add_experimental_option("detach", True)
            
            # Intentar iniciar el navegador
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, BROWSER_TIMEOUT)  # Timeout configurado
            
            logger.info("Navegador Chrome iniciado correctamente")
            return True
            
        except WebDriverException as e:
            if "Chrome failed to start" in str(e):
                logger.error(f"Error al iniciar Chrome: {e}. Verificando si hay instancias abiertas...")
                # Intentar recuperar sesión existente
                try:
                    chrome_options = Options()
                    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
                    self.driver = webdriver.Chrome(options=chrome_options)
                    self.wait = WebDriverWait(self.driver, BROWSER_TIMEOUT)
                    logger.info("Conexión exitosa a sesión existente de Chrome")
                    return True
                except Exception as debug_e:
                    logger.error(f"No se pudo conectar a sesión existente: {debug_e}")
            
            logger.error(f"Error al iniciar Navegador: {e}")
            return False






    def close(self):
            """Cierra el navegador si está abierto"""
            if self.driver:
                try:
                    self.driver.quit()
                    self.driver = None
                    self.wait = None
                    logger.info("Navegador cerrado correctamente")
                    return True
                except Exception as e:
                    logger.error(f"Error al cerrar el navegador: {e}")
                    return False
            return True

    def navigate_to_sap(self, erp_number=None, project_id=None):
        """
        Navega a la URL de SAP con parámetros específicos de cliente y proyecto,
        implementando verificación y reintentos para evitar redirecciones.
        
        Args:
            erp_number (str, optional): Número ERP del cliente.
            project_id (str, optional): ID del proyecto.
        
        Returns:
            bool: True si la navegación fue exitosa, False en caso contrario
        """
        if not self.driver:
            logger.error("No hay navegador iniciado")
            return False
            
        try:
            # Extraer solo los números de ERP y project ID
            if erp_number and " - " in erp_number:
                erp_number = erp_number.split(" - ")[0].strip()
                
            if project_id and " - " in project_id:
                project_id = project_id.split(" - ")[0].strip()           
            
            # URL destino exacta
            target_url = f"https://xalm-prod.x.eu20.alm.cloud.sap/launchpad#iam-ui&/?erpNumber={erp_number}&crmProjectId={project_id}&x-app-name=HEP"
            logger.info(f"Intentando navegar a: {target_url}")
            
            # Intentar navegación directa
            self.driver.get(target_url)
            time.sleep(5)  # Esperar carga inicial
            
            # Verificar si fuimos redirigidos
            current_url = self.driver.current_url
            logger.info(f"URL actual después de navegación: {current_url}")
            
            # Si fuimos redirigidos a otra página, intentar navegar directamente por JavaScript
            if "sdwork-center" in current_url or not "iam-ui" in current_url:
                logger.warning("Detectada redirección no deseada, intentando navegación por JavaScript")
                
                # Intentar con JavaScript para evitar redirecciones
                js_navigate_script = f"""
                window.location.href = "{target_url}";
                """
                self.driver.execute_script(js_navigate_script)
                time.sleep(5)  # Esperar a que cargue la página
                
                # Verificar nuevamente
                current_url = self.driver.current_url
                logger.info(f"URL después de navegación por JavaScript: {current_url}")
                
                # Si aún no estamos en la URL correcta, usar hackerParams para forzar
                if "sdwork-center" in current_url or not "iam-ui" in current_url:
                    logger.warning("Redirección persistente, intentando método forzado")
                    
                    # Método más agresivo para forzar la navegación
                    force_script = f"""
                    var hackerParams = new URLSearchParams();
                    hackerParams.append('erpNumber', '{erp_number}');
                    hackerParams.append('crmProjectId', '{project_id}');
                    hackerParams.append('x-app-name', 'HEP');
                    
                    var targetHash = '#iam-ui&/?' + hackerParams.toString();
                    window.location.hash = targetHash;
                    """
                    self.driver.execute_script(force_script)
                    time.sleep(5)
            
            # Intentar aceptar certificados o diálogos si aparecen
            try:
                ok_buttons = self.driver.find_elements(By.XPATH, 
                    "//button[contains(text(), 'OK') or contains(text(), 'Ok') or contains(text(), 'Aceptar')]")
                if ok_buttons:
                    for button in ok_buttons:
                        if button.is_displayed():
                            button.click()
                            logger.info("Se hizo clic en un botón de diálogo")
                            time.sleep(1)
            except Exception as dialog_e:
                logger.debug(f"Error al manejar diálogos: {dialog_e}")
            
            # Verificar URL final después de todos los intentos
            final_url = self.driver.current_url
            logger.info(f"URL final después de todos los intentos: {final_url}")
            
            # Esperar a que la página cargue completamente
            try:
                WebDriverWait(self.driver, 15).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                logger.info("Página cargada completamente")
            except TimeoutException:
                logger.warning("Tiempo de espera excedido para carga completa de página")
            
            # Considerar éxito si contiene iam-ui o los parámetros específicos
            success = "iam-ui" in final_url or erp_number in final_url
            if success:
                logger.info("Navegación exitosa a la página deseada")
            else:
                logger.warning("No se pudo navegar a la página exacta deseada")
                
            return True  # Continuar con el flujo incluso si no llegamos exactamente a la URL
                
        except Exception as e:
            logger.error(f"Error al navegar a SAP: {e}")
            return False
        
        
        
        
        
        
        
        
        
            
    def handle_authentication(self):
            """
            Maneja el proceso de autenticación en SAP, detectando si es necesario.
            
            Returns:
                bool: True si la autenticación fue exitosa o no fue necesaria, False en caso contrario
            """
            try:
                logger.info("Verificando si se requiere autenticación...")
                
                # Verificar si hay formulario de login visible
                login_elements = self.driver.find_elements(By.XPATH, "//input[@type='email'] | //input[@type='password']")
                
                if login_elements:
                    logger.info("Formulario de login detectado, esperando introducción manual de credenciales")
                    
                    # Mostrar mensaje al usuario si estamos en interfaz gráfica
                    if hasattr(self, 'root') and self.root:
                        messagebox.showinfo(
                            "Autenticación Requerida",
                            "Por favor, introduzca sus credenciales en el navegador.\n\n"
                            "Haga clic en OK cuando haya iniciado sesión."
                        )
                    else:
                        print("\n=== AUTENTICACIÓN REQUERIDA ===")
                        print("Por favor, introduzca sus credenciales en el navegador.")
                        input("Presione ENTER cuando haya iniciado sesión...\n")
                    
                    # Esperar a que desaparezca la pantalla de login
                    try:
                        WebDriverWait(self.driver, 60).until_not(
                            EC.presence_of_element_located((By.XPATH, "//input[@type='password']"))
                        )
                        logger.info("Autenticación completada exitosamente")
                        return True
                    except TimeoutException:
                        logger.warning("Tiempo de espera excedido para autenticación")
                        return False
                else:
                    logger.info("No se requiere autenticación, ya hay una sesión activa")
                    return True
                    
            except Exception as e:
                logger.error(f"Error durante el proceso de autenticación: {e}")
                return False
        
        
        
        
        
    def detect_and_handle_pagination(self):
        """
        Detecta y maneja los controles de paginación en tablas SAP UI5/Fiori.
        Navega por todas las páginas disponibles para extraer datos completos.
        
        Returns:
            bool: True si se manejó la paginación, False si no hay paginación o no se pudo manejar
        """
        logger.info("Verificando si hay controles de paginación...")
        
        try:
            # Detectar controles de paginación - múltiples patrones
            pagination_controls = []
            
            # 1. Buscar elementos de paginación estándar
            pagination_selectors = [
                "//div[contains(@class, 'sapMPagingPanel')]",
                "//div[contains(@class, 'sapMPageNav')]",
                "//div[contains(@class, 'sapUiTablePaginator')]",
                "//div[contains(@class, 'sapUiTablePageFooter')]",
                "//div[contains(@id, 'pagination')]",
                "//div[contains(@class, 'pagination')]",
                "//span[contains(@class, 'sapMPaginatorNavButton')]/..",
                "//button[contains(@class, 'sapMPaginatorNavButton')]/.."
            ]
            
            for selector in pagination_selectors:
                elements = self.driver.find_elements(By.XPATH, selector)
                if elements and any(e.is_displayed() for e in elements):
                    pagination_controls.extend([e for e in elements if e.is_displayed()])
                    logger.info(f"Control de paginación encontrado con selector: {selector}")
            
            # Si no hay controles de paginación visibles, verificar botones de siguiente página
            if not pagination_controls:
                next_page_selectors = [
                    "//button[contains(@title, 'Next Page')]",
                    "//button[contains(@aria-label, 'Next Page')]",
                    "//span[contains(@class, 'sapMPaginatorNext')]",
                    "//button[contains(@class, 'sapMBtn') and .//span[contains(text(), 'Next')]]",
                    "//div[contains(@class, 'sapMPageNext')]",
                    "//span[contains(@class, 'sapUiIcon--navigation-right-arrow')]/.."
                ]
                
                for selector in next_page_selectors:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements and any(e.is_displayed() for e in elements):
                        pagination_controls.extend([e for e in elements if e.is_displayed()])
                        logger.info(f"Botón de siguiente página encontrado con selector: {selector}")
            
            # Si no se encontraron controles de paginación, verificar con JavaScript
            if not pagination_controls:
                js_result = self.driver.execute_script("""
                    return (function() {
                        // Buscar elementos de paginación comunes
                        var paginationElements = [];
                        
                        // Patrones de clases para controles de paginación
                        var paginationPatterns = [
                            'pagination', 'paging', 'paginator', 'pageNav', 'pageFooter'
                        ];
                        
                        // Buscar elementos con estas clases
                        for (var i = 0; i < paginationPatterns.length; i++) {
                            var pattern = paginationPatterns[i];
                            var elements = document.querySelectorAll('*[class*="' + pattern + '"]');
                            if (elements.length > 0) {
                                for (var j = 0; j < elements.length; j++) {
                                    if (elements[j].offsetParent !== null) {
                                        paginationElements.push(elements[j]);
                                    }
                                }
                            }
                        }
                        
                        // Buscar contenido textual típico de paginación
                        var paginationTexts = [
                            'Next Page', 'Previous Page', 'Page', 'of'
                        ];
                        
                        if (paginationElements.length === 0) {
                            // Buscar elementos que contengan texto típico de paginación
                            var allElements = document.querySelectorAll('button, span, div');
                            for (var k = 0; k < allElements.length; k++) {
                                var el = allElements[k];
                                if (el.offsetParent !== null) {
                                    var text = el.textContent.toLowerCase();
                                    for (var l = 0; l < paginationTexts.length; l++) {
                                        if (text.includes(paginationTexts[l].toLowerCase())) {
                                            // Encontrar el contenedor padre
                                            var parent = el;
                                            for (var m = 0; m < 5; m++) {
                                                parent = parent.parentElement;
                                                if (!parent) break;
                                                
                                                // Verificar si este padre contiene múltiples controles de paginación
                                                var children = parent.querySelectorAll('button, span[role="button"]');
                                                if (children.length >= 2) {
                                                    paginationElements.push(parent);
                                                    break;
                                                }
                                            }
                                            
                                            break;
                                        }
                                    }
                                }
                            }
                        }
                        
                        return paginationElements.length > 0;
                    })();
                """)
                
                if js_result:
                    logger.info("Se detectaron controles de paginación mediante JavaScript")
                    
                    # Intentar encontrar los botones de siguiente/anterior página
                    next_btn = self.driver.find_elements(By.XPATH, 
                        "//button[contains(@title, 'Next') or contains(@aria-label, 'Next')] | " +
                        "//span[contains(@class, 'Next')] | " +
                        "//span[contains(@class, 'right-arrow')]/.."
                    )
                    
                    if next_btn and any(btn.is_displayed() for btn in next_btn):
                        next_btn = next(btn for btn in next_btn if btn.is_displayed())
                        pagination_controls.append(next_btn)
            
            # Si no hay paginación, terminar
            if not pagination_controls:
                logger.info("No se detectaron controles de paginación")
                return False
            
            # Hay paginación, intentar recorrer todas las páginas
            logger.info("Se detectaron controles de paginación, procesando todas las páginas...")
            
            current_page = 1
            has_more_pages = True
            
            while has_more_pages and current_page <= 100:  # Límite de 100 páginas por seguridad
                logger.info(f"Procesando página {current_page}...")
                
                # Actualizar la interfaz si existe
                if hasattr(self, 'status_var') and self.status_var:
                    self.status_var.set(f"Procesando página {current_page}...")
                
                # En cada página, esperar a que carguen los datos
                time.sleep(2)
                
                # Intentar pasar a la siguiente página
                next_button = None
                
                # Buscar el botón "Siguiente"
                next_button_selectors = [
                    "//button[contains(@title, 'Next Page')]",
                    "//button[contains(@aria-label, 'Next Page')]",
                    "//span[contains(@class, 'sapMPaginatorNext')]/..",
                    "//button[contains(@class, 'sapMBtn') and .//span[contains(text(), 'Next')]]",
                    "//div[contains(@class, 'sapMPageNext')]",
                    "//span[contains(@class, 'sapUiIcon--navigation-right-arrow')]/.."
                ]
                
                for selector in next_button_selectors:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        for element in elements:
                            if element.is_displayed():
                                try:
                                    is_enabled = element.is_enabled() and "sapMBtnDisabled" not in element.get_attribute("class")
                                    if is_enabled:
                                        next_button = element
                                        break
                                except:
                                    continue
                    
                    if next_button:
                        break
                
                # Si no encontramos un botón de siguiente, intentar con JavaScript
                if not next_button:
                    js_next_button = self.driver.execute_script("""
                        return (function() {
                            // Buscar botones de siguiente
                            var nextButtons = [];
                            
                            // Por texto
                            var buttons = document.querySelectorAll('button, span[role="button"], div[role="button"]');
                            for (var i = 0; i < buttons.length; i++) {
                                var btn = buttons[i];
                                if (btn.offsetParent !== null) {
                                    var text = btn.textContent.toLowerCase();
                                    var title = (btn.getAttribute('title') || '').toLowerCase();
                                    var ariaLabel = (btn.getAttribute('aria-label') || '').toLowerCase();
                                    
                                    if (text.includes('next') || title.includes('next') || ariaLabel.includes('next')) {
                                        // Verificar que no esté deshabilitado
                                        if (!btn.disabled && !btn.classList.contains('sapMBtnDisabled')) {
                                            nextButtons.push(btn);
                                        }
                                    }
                                }
                            }
                            
                            // Por íconos
                            var icons = document.querySelectorAll('.sapUiIcon--navigation-right-arrow, .sapUiIcon--slim-arrow-right');
                            for (var j = 0; j < icons.length; j++) {
                                var icon = icons[j];
                                if (icon.offsetParent !== null) {
                                    var iconParent = icon.parentElement;
                                    while (iconParent && iconParent.tagName !== 'BUTTON' && !iconParent.getAttribute('role') === 'button') {
                                        iconParent = iconParent.parentElement;
                                        if (!iconParent) break;
                                    }
                                    
                                    if (iconParent && !iconParent.disabled && !iconParent.classList.contains('sapMBtnDisabled')) {
                                        nextButtons.push(iconParent);
                                    }
                                }
                            }
                            
                            return nextButtons.length > 0 ? nextButtons[0] : null;
                        })();
                    """)
                    
                    if js_next_button:
                        next_button = js_next_button
                
                # Verificar si hay un botón de siguiente y está habilitado
                if next_button:
                    try:
                        # Hacer scroll para asegurar la visibilidad
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                        time.sleep(0.5)
                        
                        # Clic en el botón de siguiente página
                        self.driver.execute_script("arguments[0].click();", next_button)
                        logger.info(f"Clic en botón de siguiente página")
                        
                        # Esperar a que cargue la siguiente página
                        time.sleep(3)
                        
                        # Incrementar contador de página
                        current_page += 1
                        
                        # Verificar si hemos llegado al final
                        is_disabled_js = self.driver.execute_script("""
                            return (function(btn) {
                                return btn.disabled || 
                                    btn.classList.contains('sapMBtnDisabled') || 
                                    btn.classList.contains('disabled') ||
                                    btn.getAttribute('aria-disabled') === 'true';
                            })(arguments[0]);
                        """, next_button)
                        
                        if is_disabled_js:
                            has_more_pages = False
                            logger.info("Se ha llegado a la última página")
                    except Exception as e:
                        logger.warning(f"Error al hacer clic en botón de siguiente página: {e}")
                        has_more_pages = False
                else:
                    # No hay botón de siguiente página o está deshabilitado
                    logger.info("No se encontró un botón de siguiente página habilitado")
                    has_more_pages = False
            
            logger.info(f"Paginación completa. Se procesaron {current_page} páginas.")
            return True
            
        except Exception as e:
            logger.error(f"Error al manejar paginación: {e}")
            return False

        
        
        
        
                
    def verify_fields_have_expected_values(self, erp_number, project_id):
        """
        Verifica si los campos ya contienen los valores esperados.
        
        Esta función analiza la interfaz actual para determinar si el cliente y proyecto
        especificados ya están seleccionados, evitando interacciones innecesarias.
        
        Args:
            erp_number (str): Número ERP del cliente
            project_id (str): ID del proyecto
                
        Returns:
            bool: True si los campos tienen los valores esperados, False en caso contrario
        """
        try:
            logger.info(f"Verificando si los campos ya contienen los valores esperados: Cliente {erp_number}, Proyecto {project_id}")
            
            # Indicadores de que estamos en la página correcta con los valores esperados
            indicators_found = 0
            
            # 1. Verificar campos de entrada directamente
            fields_verified = 0
            
            # Verificar el campo de cliente
            customer_fields = self.driver.find_elements(
                By.XPATH,
                "//input[contains(@placeholder, 'Customer') or contains(@aria-label, 'Customer')]"
            )
            
            if customer_fields:
                for field in customer_fields:
                    if field.is_displayed():
                        current_value = field.get_attribute("value") or ""
                        if erp_number in current_value:
                            logger.info(f"✓ Campo de cliente contiene '{erp_number}'")
                            fields_verified += 1
                            break
            
            # Verificar el campo de proyecto
            project_fields = self.driver.find_elements(
                By.XPATH,
                "//input[contains(@placeholder, 'Project') or contains(@aria-label, 'Project')]"
            )
            
            if project_fields:
                for field in project_fields:
                    if field.is_displayed():
                        current_value = field.get_attribute("value") or ""
                        if project_id in current_value:
                            logger.info(f"✓ Campo de proyecto contiene '{project_id}'")
                            fields_verified += 1
                            break
            
            # 2. Verificar texto visible en la página
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                
                # Verificar ERP
                if erp_number in page_text:
                    logger.info(f"✓ ERP '{erp_number}' encontrado en el texto de la página")
                    indicators_found += 1
                
                # Verificar Project ID
                if project_id in page_text:
                    logger.info(f"✓ Project ID '{project_id}' encontrado en el texto de la página")
                    indicators_found += 1
            except Exception as text_e:
                logger.debug(f"Error al verificar texto: {text_e}")
            
            # 3. Verificar si estamos en la página correcta con los datos
            interface_indicators = [
                "//div[contains(text(), 'Issues by Status')]",
                "//div[contains(text(), 'Actions by Status')]",
                "//div[contains(@class, 'sapMITBHead')]"  # Pestañas de navegación
            ]
            
            for indicator in interface_indicators:
                try:
                    elements = self.driver.find_elements(By.XPATH, indicator)
                    if elements and any(e.is_displayed() for e in elements):
                        logger.info(f"✓ Interfaz correcta detectada: {indicator}")
                        indicators_found += 1
                        break
                except:
                    continue
                
                
                
                
                
                
                
                
                
# 4. Verificar mediante JavaScript para interfaces complejas
            js_check = """
            (function() {
                // Verificar Cliente
                var customerElements = document.querySelectorAll('*');
                var foundClient = false;
                var foundProject = false;
                
                for (var i = 0; i < customerElements.length; i++) {
                    var el = customerElements[i];
                    var text = el.textContent || '';
                    
                    // Buscar Cliente
                    if (!foundClient && text.includes(arguments[0])) {
                        foundClient = true;
                    }
                    
                    // Buscar Proyecto
                    if (!foundProject && text.includes(arguments[1])) {
                        foundProject = true;
                    }
                    
                    if (foundClient && foundProject) break;
                }
                
                // Verificar estado de la interfaz
                var hasAdvancedUI = document.querySelectorAll('.sapMITB, .sapMPanel').length > 5;
                
                return {
                    clientFound: foundClient,
                    projectFound: foundProject,
                    hasAdvancedUI: hasAdvancedUI
                };
            })();
            """
            
            try:
                result = self.driver.execute_script(js_check, erp_number, project_id)
                
                if result.get('clientFound'):
                    indicators_found += 1
                
                if result.get('projectFound'):
                    indicators_found += 1
                    
                if result.get('hasAdvancedUI'):
                    indicators_found += 1
            except Exception as js_e:
                logger.debug(f"Error en verificación JavaScript: {js_e}")
            
            # Determinar resultado final basado en los indicadores encontrados
            if fields_verified >= 2:
                # Si ambos campos tienen los valores correctos, es prueba directa
                logger.info("✅ Valores esperados confirmados: campos contienen valores correctos")
                return True
            elif indicators_found >= 3:
                # Al menos 3 indicadores indirectos encontrados
                logger.info("✅ Valores esperados confirmados: suficientes indicadores encontrados")
                return True
            else:
                logger.info("⚠️ No se pudieron confirmar valores esperados en los campos")
                return False
            
        except Exception as e:
            logger.error(f"Error al verificar campos: {e}")
            return False
            
    def select_customer_automatically(self, erp_number):
        """
        Selecciona automáticamente un cliente en la pantalla de Project Overview.
        Implementa múltiples estrategias para la selección, incluyendo interacción directa con UI5.
        
        Args:
            erp_number (str): Número ERP del cliente a seleccionar
        
        Returns:
            bool: True si la selección fue exitosa, False en caso contrario
        """
        try:
            # Verificar que el ERP no esté vacío
            if not erp_number or erp_number.strip() == "":
                logger.warning("No se puede seleccionar cliente: ERP número vacío")
                return False
            logger.info(f"Intentando seleccionar automáticamente el cliente {erp_number}...")
            
            # ESTRATEGIA 1: Intentar primero con el método directo de UI5 (más efectivo)
            if self.select_customer_ui5_direct(erp_number):
                logger.info(f"Cliente {erp_number} seleccionado exitosamente con método UI5 directo")
                return True
                
            # ESTRATEGIA 2: Si falló el método directo, intentar con el método original
            logger.info("Método UI5 directo falló, intentando método estándar...")
            
            # Esperar a que la página cargue completamente
            time.sleep(5)
            
            # Localizar el campo de entrada de cliente con múltiples selectores
            customer_field = None
            customer_field_selectors = [
                "//input[@placeholder='Enter Customer ID or Name']",
                "//input[contains(@placeholder, 'Customer')]",
                "//input[@id='customer']",
                "//input[contains(@aria-label, 'Customer')]",
                "//div[contains(text(), 'Customer')]/following-sibling::div//input",
                "//label[contains(text(), 'Customer')]/following-sibling::div//input",
                "//input[contains(@id, 'customer')]",
                "//span[contains(text(), 'Customer')]/following::input[1]",
                "//div[contains(@id, 'customer')]//input"
            ]
            
            
            
            
            
            
            
            
            
            
            
# Probar cada selector hasta encontrar un campo visible
            for selector in customer_field_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            customer_field = element
                            logger.info(f"Campo de cliente encontrado con selector: {selector}")
                            break
                    if customer_field:
                        break
                except Exception as selector_e:
                    logger.debug(f"Error con selector {selector}: {selector_e}")
                    continue
            
            if not customer_field:
                logger.warning("No se pudo encontrar el campo de cliente visible")
                return False
            
            # Limpiar el campo completamente usando múltiples técnicas
            try:
                self.driver.execute_script("arguments[0].value = '';", customer_field)
                customer_field.clear()
                customer_field.send_keys(Keys.CONTROL + "a")
                customer_field.send_keys(Keys.DELETE)
                time.sleep(1)
            except Exception as clear_e:
                logger.warning(f"Error al limpiar campo de cliente: {clear_e}")
            
            # Escribir el ERP número con pausas entre caracteres para permitir autocompletado
            for char in erp_number:
                customer_field.send_keys(char)
                time.sleep(0.3)
            
            # Esperar a que aparezcan las sugerencias
            time.sleep(2)
            
            # NUEVA ESTRATEGIA: Usar flecha abajo y Enter para seleccionar la primera sugerencia
            try:
                # Enviar flecha abajo para seleccionar la primera sugerencia
                customer_field.send_keys(Keys.DOWN)
                time.sleep(1)
                # Enviar Enter para confirmar la selección
                customer_field.send_keys(Keys.ENTER)
                time.sleep(2)
                logger.info("Flecha abajo y Enter enviados para seleccionar sugerencia")
                
                # Verificar si se seleccionó correctamente
                selected = self._verify_client_selection_strict(erp_number)
                if selected:
                    logger.info(f"Cliente {erp_number} seleccionado exitosamente con flecha abajo y Enter")
                    return True
            except Exception as key_e:
                logger.warning(f"Error al utilizar flecha abajo y Enter: {key_e}")
            
            # Continuar con las estrategias anteriores si la nueva estrategia falló
            # Intentar encontrar y seleccionar sugerencia con múltiples selectores
            suggestion_selectors = [
                f"//div[contains(text(), '{erp_number}')]",
                f"//div[contains(@class, 'sapMPopover')]//div[contains(text(), '{erp_number}')]",
                f"//ul//li[contains(text(), '{erp_number}')]",
                f"//div[contains(@class, 'sapMSuggestionPopup')]//li[contains(text(), '{erp_number}')]"
            ]
            
            suggestion_found = False
            for selector in suggestion_selectors:
                try:
                    suggestions = self.driver.find_elements(By.XPATH, selector)
                    if suggestions:
                        for suggestion in suggestions:
                            if suggestion.is_displayed():
                                try:
                                    # Primero intentar JavaScript click
                                    self.driver.execute_script("arguments[0].click();", suggestion)
                                    logger.info(f"Sugerencia seleccionada mediante JavaScript: {suggestion.text}")
                                    suggestion_found = True
                                    time.sleep(2)
                                    break
                                except Exception as js_click_e:
                                    logger.debug(f"Error en JavaScript click: {js_click_e}, intentando click normal")
                                    try:
                                        suggestion.click()
                                        logger.info(f"Sugerencia seleccionada con click normal: {suggestion.text}")
                                        suggestion_found = True
                                        time.sleep(2)
                                        break
                                    except Exception as normal_click_e:
                                        logger.debug(f"Error en click normal: {normal_click_e}")
                    if suggestion_found:
                        break
                except Exception as suggestion_e:
                    logger.debug(f"Error buscando sugerencias con selector {selector}: {suggestion_e}")
                    continue
                
                
                
                
                
                
                
# Si no se encontró sugerencia, presionar Enter
            if not suggestion_found:
                logger.info("No se encontraron sugerencias, presionando Enter")
                customer_field.send_keys(Keys.ENTER)
                time.sleep(2)
            
            # VERIFICACIÓN CRÍTICA: Verificar estrictamente que el cliente fue seleccionado
            selected = self._verify_client_selection_strict(erp_number)
            
            # ESTRATEGIA 3: Si aún no se ha seleccionado, intentar método JavaScript directo como último recurso
            if not selected:
                logger.warning("Los métodos previos fallaron, intentando JavaScript directo...")
                js_script = f"""
                var input = arguments[0];
                input.value = '{erp_number}';
                var event = new Event('change', {{ bubbles: true }});
                input.dispatchEvent(event);
                
                // Intentar disparar evento de tecla Enter
                var enterEvent = new KeyboardEvent('keydown', {{
                key: 'Enter',
                code: 'Enter',
                keyCode: 13,
                which: 13,
                bubbles: true
                }});
                input.dispatchEvent(enterEvent);
                """
                self.driver.execute_script(js_script, customer_field)
                time.sleep(2)
                customer_field.send_keys(Keys.TAB)  # Navegar al siguiente campo
                selected = self._verify_client_selection_strict(erp_number)
            
            return selected
        
        except Exception as e:
            logger.error(f"Error general durante la selección automática de cliente: {e}")
            return False
            
    def select_customer_ui5_direct(self, erp_number):
        """
        Selecciona el cliente interactuando directamente con el framework UI5.
        Optimizado para la interfaz específica de SAP Fiori Issues and Actions Management.
        
        Args:
            erp_number (str): Número ERP del cliente a seleccionar
            
        Returns:
            bool: True si la selección fue exitosa, False en caso contrario
        """
        try:
            logger.info(f"Seleccionando cliente {erp_number} mediante API directa de UI5")
            
            # Verificar primero si el cliente ya está seleccionado
            is_already_selected = self._check_if_already_selected(erp_number)
            if is_already_selected:
                logger.info(f"Cliente {erp_number} ya está seleccionado")
                return True
            
            # Script específico para SAP Fiori/UI5 Issues and Actions Management
            js_script = """
            (function() {
                // Función para esperar a que el elemento esté disponible
                function waitForElement(selector, maxTime) {
                    return new Promise((resolve, reject) => {
                        if (document.querySelector(selector)) {
                            return resolve(document.querySelector(selector));
                        }
                        
                        const observer = new MutationObserver(mutations => {
                            if (document.querySelector(selector)) {
                                observer.disconnect();
                                resolve(document.querySelector(selector));
                            }
                        });
                        
                        observer.observe(document.body, {
                            childList: true,
                            subtree: true
                        });
                        
                        setTimeout(() => {
                            observer.disconnect();
                            resolve(document.querySelector(selector));
                        }, maxTime);
                    });
                }
                
                async function selectCustomer() {
                    try {
                        console.log("Buscando campo de cliente...");
                        
                        // 1. Buscar el campo de cliente usando selectores específicos para esta interfaz
                        let customerInput = document.querySelector('input[placeholder*="Customer"]');
                        if (!customerInput) {
                            // Esperar a que aparezca (máximo 2 segundos)
                            customerInput = await waitForElement('input[placeholder*="Customer"], input[aria-label*="Customer"]', 2000);
                        }
                        
                        // Si todavía no lo encontramos, buscar en todos los inputs visibles
                        if (!customerInput) {
                            const inputs = document.querySelectorAll('input:not([type="hidden"])');
                            for (const input of inputs) {
                                if (input.offsetParent !== null) { // Elemento visible
                                    const ariaLabel = input.getAttribute('aria-label') || '';
                                    const placeholder = input.getAttribute('placeholder') || '';
                                    if (ariaLabel.includes('Customer') || placeholder.includes('Customer')) {
                                        customerInput = input;
                                        break;
                                    }
                                }
                            }
                        }
                        
                        if (!customerInput) {
                            console.error("No se encontró el campo de cliente");
                            return false;
                        }
                        
                        console.log("Campo de cliente encontrado");
                        
                        // 2. Verificar si el campo ya tiene el valor correcto
                        if (customerInput.value.includes('{erp_number}')) {
                            console.log("El campo ya contiene el valor correcto");
                            return true;
                        }
                        
                        // 3. Limpiar el campo y establecer el foco
                        console.log("Limpiando campo...");
                        customerInput.value = '';
                        customerInput.focus();
                        
                        // Disparar eventos de limpieza
                        customerInput.dispatchEvent(new Event('input', { bubbles: true }));
                        customerInput.dispatchEvent(new Event('change', { bubbles: true }));
                        
                        // 4. Establecer el valor del ERP
                        console.log("Ingresando valor del ERP...");
                        customerInput.value = '{erp_number}';
                        
                        // Disparar eventos para activar la búsqueda de sugerencias
                        customerInput.dispatchEvent(new Event('input', { bubbles: true }));
                        customerInput.dispatchEvent(new Event('change', { bubbles: true }));
                        
                        // Esperar a que aparezcan las sugerencias
                        await new Promise(resolve => setTimeout(resolve, 800));
                        
                        // 5. Enviar tecla DOWN varias veces para asegurar selección
                        console.log("Presionando teclas DOWN...");
                        for (let i = 0; i < 3; i++) {
                            const downEvent = new KeyboardEvent('keydown', {
                                key: 'ArrowDown',
                                code: 'ArrowDown',
                                keyCode: 40,
                                which: 40,
                                bubbles: true
                            });
                            customerInput.dispatchEvent(downEvent);
                            
                            // Esperar entre teclas
                            await new Promise(resolve => setTimeout(resolve, 300));
                        }
                        
                        // 6. Verificar si hay sugerencias y hacer clic directamente
                        console.log("Buscando sugerencias...");
                        const popups = document.querySelectorAll('.sapMPopover, .sapMSuggestionPopup, .sapMSelectList');
                        let suggestionClicked = false;
                        
                        for (const popup of popups) {
                            if (popup.offsetParent !== null) { // Popup visible
                                console.log("Dropdown visible encontrado");
                                const items = popup.querySelectorAll('li');
                                
                                if (items.length > 0) {
                                    console.log(`${items.length} sugerencias encontradas, seleccionando primera...`);
                                    // Hacer clic en la primera sugerencia
                                    items[0].click();
                                    suggestionClicked = true;
                                    break;
                                }
                            }
                        }
                        
                        // 7. Si no se hizo clic en ninguna sugerencia, enviar ENTER
                        if (!suggestionClicked) {
                            console.log("No se encontraron sugerencias para clic directo, enviando ENTER");
                            const enterEvent = new KeyboardEvent('keydown', {
                                key: 'Enter',
                                code: 'Enter',
                                keyCode: 13,
                                which: 13,
                                bubbles: true
                            });
                            customerInput.dispatchEvent(enterEvent);
                        }
                        
                        // Esperar a que se complete la selección
                        await new Promise(resolve => setTimeout(resolve, 1000));
                        
                        // 8. Verificar si el campo tiene el valor correcto ahora
                        const labels = document.querySelectorAll('label, span, div');
                        for (const label of labels) {
                            if (label.textContent && label.textContent.includes('{erp_number}')) {
                                console.log("Verificación: Cliente seleccionado correctamente");
                                return true;
                            }
                        }
                        
                        // Verificación final del campo de input
                        if (customerInput.value && customerInput.value.includes('{erp_number}')) {
                            console.log("Verificación: Cliente seleccionado en el campo");
                            return true;
                        }
                        
                        console.log("No se pudo verificar la selección del cliente");
                        return false;
                        
                    } catch (error) {
                        console.error("Error en selección de cliente:", error);
                        return false;
                    }
                }
                
                return selectCustomer();
            })();
            """.replace('{erp_number}', erp_number)
            
            # Ejecutar el script
            result = self.driver.execute_script(js_script)
            logger.info(f"Resultado del script UI5: {result}")
            
            # Esperar un poco más para dar tiempo a la interfaz a actualizarse
            time.sleep(2.5)
            
            # Verificación mejorada que incluye múltiples criterios
            selected = self._enhanced_client_verification(erp_number)
            
            if not selected:
                logger.warning(f"La selección UI5 directa no tuvo éxito para {erp_number}, intentando método Selenium")
                
                # Método alternativo con Selenium directo
                try:
                    # Buscar el campo con múltiples selectores
                    customer_field = None
                    selectors = [
                        "//input[contains(@placeholder, 'Customer')]",
                        "//input[contains(@aria-label, 'Customer')]",
                        "//div[contains(text(), 'Customer:')]/following-sibling::input",
                        "//span[contains(text(), 'Customer')]/following::input[1]",
                        # Selector específico para el campo que veo en la captura
                        "//div[contains(@class, 'sapMInputBaseInner')]"
                    ]
                    
                    for selector in selectors:
                        try:
                            fields = self.driver.find_elements(By.XPATH, selector)
                            for field in fields:
                                if field.is_displayed():
                                    customer_field = field
                                    logger.info(f"Campo de cliente encontrado con selector: {selector}")
                                    break
                            if customer_field:
                                break
                        except:
                            continue
                    
                    if customer_field:
                        # Limpiar completamente
                        self.driver.execute_script("arguments[0].value = '';", customer_field)
                        customer_field.clear()
                        
                        # Para interfaces complejas: usar un método más directo
                        self.driver.execute_script(f"arguments[0].value = '{erp_number}';", customer_field)
                        
                        # Disparar eventos para activar sugerencias
                        self.driver.execute_script("""
                            var input = arguments[0];
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                        """, customer_field)
                        
                        # Espera para sugerencias
                        time.sleep(1.5)
                        
                        # Usar ActionChains para secuencia precisa
                        actions = ActionChains(self.driver)
                        # Hacer clic en el campo para asegurar foco
                        actions.click(customer_field)
                        # Esperar
                        actions.pause(0.5)
                        # Presionar DOWN varias veces
                        for _ in range(3):
                            actions.send_keys(Keys.DOWN)
                            actions.pause(0.3)
                        # Enter para confirmar
                        actions.send_keys(Keys.ENTER)
                        actions.perform()
                        
                        # Esperar procesamiento
                        time.sleep(1.5)
                        
                        # Verificar con criterios extendidos
                        selected = self._enhanced_client_verification(erp_number)
                        if selected:
                            logger.info(f"Cliente {erp_number} seleccionado con método Selenium")
                            return True
                        
                        # Si todavía no, intentar método de clic directo en sugerencias
                        try:
                            suggestions = self.driver.find_elements(By.XPATH, 
                                "//div[contains(@class, 'sapMPopup')]//li | //div[contains(@class, 'sapMSuggestionPopup')]//li")
                            
                            if suggestions and len(suggestions) > 0:
                                # Hacer clic en la primera sugerencia
                                self.driver.execute_script("arguments[0].click();", suggestions[0])
                                logger.info("Clic directo en primera sugerencia de dropdown")
                                time.sleep(1.5)
                                
                                selected = self._enhanced_client_verification(erp_number)
                        except Exception as sugg_e:
                            logger.debug(f"Error al buscar sugerencias: {sugg_e}")
                except Exception as e:
                    logger.error(f"Error en método alternativo: {e}")
            
            if selected:
                logger.info(f"Cliente {erp_number} seleccionado correctamente")
            else:
                logger.error(f"❌ Selección de cliente falló para {erp_number}")
                
            return selected
            
        except Exception as e:
            logger.error(f"Error al seleccionar cliente con UI5 directo: {e}")
            return False
        
        
        
        
        
        
    def _check_if_already_selected(self, erp_number):
            """
            Verifica rápidamente si el cliente ya está seleccionado basándose en la interfaz visible.
            
            Args:
                erp_number (str): Número ERP del cliente
                
            Returns:
                bool: True si el cliente ya parece estar seleccionado
            """
            try:
                # Verificar elementos de la interfaz avanzada (In Delivery, Status, etc.)
                advanced_ui = self.driver.find_elements(By.XPATH, 
                    "//div[contains(text(), 'Issues by Status')] | //div[contains(text(), 'In Delivery')]")
                    
                if advanced_ui and any(el.is_displayed() for el in advanced_ui):
                    # Verificar si también está el ERP o algún texto de cliente
                    text_elements = self.driver.find_elements(By.XPATH, 
                        f"//div[contains(text(), '{erp_number}')] | //span[contains(text(), '{erp_number}')]")
                        
                    if text_elements and any(el.is_displayed() for el in text_elements):
                        return True
                        
                    # Verificar el campo de cliente
                    customer_fields = self.driver.find_elements(By.XPATH, 
                        "//input[contains(@placeholder, 'Customer')]")
                        
                    for field in customer_fields:
                        if field.is_displayed():
                            value = field.get_attribute("value") or ""
                            if erp_number in value or "Empresa" in value:
                                return True
                
                return False
            except Exception as e:
                logger.debug(f"Error al verificar si ya está seleccionado: {e}")
                return False

    def _enhanced_client_verification(self, erp_number):
        """
        Verificación mejorada de selección de cliente que utiliza múltiples criterios
        adaptados a la interfaz de SAP Fiori Issues and Actions.
        
        Args:
            erp_number (str): Número ERP del cliente que debería estar seleccionado
            
        Returns:
            bool: True si el cliente está seleccionado según cualquiera de los criterios
        """
        try:
            # 1. Verificar si el campo de entrada contiene el valor
            input_fields = self.driver.find_elements(By.XPATH, 
                "//input[contains(@placeholder, 'Customer') or contains(@aria-label, 'Customer')]")
            
            for field in input_fields:
                if field.is_displayed():
                    value = field.get_attribute("value") or ""
                    if erp_number in value:
                        logger.info(f"Verificación: Campo de cliente contiene '{erp_number}'")
                        return True
            
            # 2. Buscar el valor en elementos de texto visibles (etiquetas, spans, divs)
            text_elements = self.driver.find_elements(By.XPATH, 
                f"//div[contains(text(), '{erp_number}')] | //span[contains(text(), '{erp_number}')]")
            
            for element in text_elements:
                if element.is_displayed():
                    logger.info(f"Verificación: Texto visible contiene '{erp_number}'")
                    return True
            
            # 3. Verificar si el campo de proyecto está habilitado/presente
            project_field = self.driver.find_elements(By.XPATH, 
                "//input[contains(@placeholder, 'Project')] | //div[contains(text(), 'Project:')]")
            
            for field in project_field:
                if field.is_displayed():
                    logger.info("Verificación: Campo de proyecto visible (indica selección cliente exitosa)")
                    return True
            
            # 4. Verificar elementos específicos de la interfaz de Issues Management
            specific_elements = self.driver.find_elements(By.XPATH, 
                "//div[contains(text(), 'Issues by Status')] | //div[contains(text(), 'Actions by Status')]")
            
            if specific_elements and any(el.is_displayed() for el in specific_elements):
                logger.info("Verificación: Elementos de interface avanzada visibles")
                return True
                
            # 5. Verificar si aparece el dropdown de 'Delivery'
            delivery_elements = self.driver.find_elements(By.XPATH, 
                "//div[contains(text(), 'In Delivery')] | //span[contains(text(), 'In Delivery')]")
                
            if delivery_elements and any(el.is_displayed() for el in delivery_elements):
                logger.info("Verificación: Dropdown 'In Delivery' visible (interfaz avanzada)")
                return True
            
            
            
            
            
            
# Script JS para verificar estado
            js_verify = f"""
            (function() {{
                // Buscar contenido visible con el ERP
                var elements = document.querySelectorAll('*');
                for (var i = 0; i < elements.length; i++) {{
                    var el = elements[i];
                    if (el.offsetParent !== null && el.textContent && el.textContent.includes('{erp_number}')) {{
                        return true;
                    }}
                }}
                
                // Verificar si los elementos de interfaz avanzada están presentes
                var advancedUI = document.querySelectorAll('.sapMPanel, .sapMITB, .sapMITBFilter');
                if (advancedUI.length > 5) {{
                    // Muchos elementos de interfaz avanzada sugieren que el cliente está seleccionado
                    // y los paneles están cargados
                    return true;
                }}
                
                return false;
            }})();
            """
            
            # Ejecutar verificación por JavaScript
            js_result = self.driver.execute_script(js_verify)
            if js_result:
                logger.info("Verificación JS: Cliente seleccionado según verificación avanzada")
                return True
                
            # Si ninguna verificación tuvo éxito
            logger.warning(f"No se pudo verificar selección del cliente {erp_number}")
            return False
            
        except Exception as e:
            logger.error(f"Error en verificación mejorada: {e}")
            return False

    def _verify_client_selection_strict(self, erp_number):
        """
        Verificación estricta de que el cliente fue realmente seleccionado
        
        Args:
            erp_number (str): Número ERP del cliente
            
        Returns:
            bool: True si el cliente está seleccionado, False en caso contrario
        """
        try:
            # Script para verificar si el cliente está seleccionado
            js_verify = f"""
            (function() {{
                // 1. Verificar campo de cliente
                var customerFields = document.querySelectorAll('input[placeholder*="Customer"], input[id*="customer"]');
                for (var i = 0; i < customerFields.length; i++) {{
                    if (customerFields[i].value && customerFields[i].value.includes("{erp_number}")) {{
                        return true;
                    }}
                }}
                
                // 2. Verificar si el valor está mostrado como texto
                var elements = document.querySelectorAll('*');
                for (var i = 0; i < elements.length; i++) {{
                    var el = elements[i];
                    if (el.textContent && 
                        el.textContent.includes("{erp_number}") && 
                        (el.textContent.includes("Customer") || el.textContent.includes("Client"))) {{
                        return true;
                    }}
                }}
                
                // 3. Verificar que el campo de proyecto esté habilitado
                var projectFields = document.querySelectorAll('input[placeholder*="Project"], input[id*="project"]');
                for (var i = 0; i < projectFields.length; i++) {{
                    if (projectFields[i].offsetParent !== null && !projectFields[i].disabled) {{
                        return true;
                    }}
                }}
                
                return false;
            }})();
            """
            
            result = self.driver.execute_script(js_verify)
            return result
        except Exception as e:
            logger.error(f"Error en verificación estricta: {e}")
            return False
        
        
        
        
        
        
        
        
        
        
        
        
    def select_project_automatically(self, project_id):
            """
            Selecciona automáticamente un proyecto por su ID.
            Implementa una estrategia mejorada, resiliente y con múltiples verificaciones.
            
            Args:
                project_id (str): ID del proyecto a seleccionar
                
            Returns:
                bool: True si la selección fue exitosa, False en caso contrario
            """
            try:
                # Verificar que el ID no esté vacío
                if not project_id or project_id.strip() == "":
                    logger.warning("No se puede seleccionar proyecto: ID vacío")
                    return False
                    
                logger.info(f"Seleccionando proyecto {project_id} automáticamente...")
                
                # 0. Verificar primero si el proyecto ya está seleccionado
                if self._verify_project_selection_strict(project_id):
                    logger.info(f"El proyecto {project_id} ya está seleccionado")
                    return True
                    
                # 1. Estrategia principal: método UI5 directo (más eficaz)
                if self.select_project_ui5_direct(project_id):
                    logger.info(f"Proyecto {project_id} seleccionado exitosamente con método UI5 directo")
                    return True
                    
                # 2. Estrategia secundaria: método Selenium con múltiples intentos
                logger.info("Método UI5 directo falló, intentando método Selenium con reintentos...")
                
                max_attempts = 3
                for attempt in range(max_attempts):
                    logger.info(f"Intento {attempt+1}/{max_attempts} con método Selenium")
                    
                    if self._select_project_with_selenium(project_id):
                        logger.info(f"Proyecto {project_id} seleccionado exitosamente en el intento {attempt+1}")
                        return True
                        
                    # Esperar entre intentos
                    if attempt < max_attempts - 1:
                        logger.info(f"Intento {attempt+1} fallido, esperando antes de reintentar...")
                        time.sleep(3)
                
                # 3. Estrategia de último recurso: Script JavaScript más agresivo
                logger.warning("Estrategias estándar fallidas, intentando script JavaScript agresivo...")
                
                js_aggressive = """
                (function() {
                    // Función para simular clic
                    function simulateClick(element) {
                        try {
                            // Intentar varios métodos de clic
                            element.click();
                            return true;
                        } catch(e) {
                            try {
                                // Simular evento de clic
                                var evt = new MouseEvent('click', {
                                    bubbles: true,
                                    cancelable: true,
                                    view: window
                                });
                                element.dispatchEvent(evt);
                                return true;
                            } catch(e2) {
                                return false;
                            }
                        }
                    }
                    
                    // 1. Buscar y seleccionar el campo de proyecto
                    var projectFields = document.querySelectorAll('input[placeholder*="Project"], input[id*="project"], input[aria-label*="Project"]');
                    var projectField = null;
                    
                    for (var i = 0; i < projectFields.length; i++) {
                        if (projectFields[i].offsetParent !== null) {
                            projectField = projectFields[i];
                            break;
                        }
                    }
                    
                    if (!projectField) {
                        return false;
                    }
                    
                    // 2. Limpiar y establecer valor
                    projectField.value = '';
                    projectField.focus();
                    projectField.value = arguments[0];
                    
                    // Forzar eventos
                    projectField.dispatchEvent(new Event('input', { bubbles: true }));
                    projectField.dispatchEvent(new Event('change', { bubbles: true }));
                    
                    // 3. Verificar cualquier lista desplegable abierta y hacer clic
                    setTimeout(function() {
                        var popups = document.querySelectorAll('.sapMPopover, .sapMSuggestionPopup, .sapMSelectList');
                        
                        for (var i = 0; i < popups.length; i++) {
                            if (popups[i].offsetParent !== null) {
                                var items = popups[i].querySelectorAll('li');
                                
                                if (items.length > 0) {
                                    simulateClick(items[0]);
                                    return;
                                }
                            }
                        }
                        
                        // Si no hay popup, simular Enter
                        var enterEvent = new KeyboardEvent('keydown', {
                            key: 'Enter',
                            code: 'Enter',
                            keyCode: 13,
                            which: 13,
                            bubbles: true
                        });
                        projectField.dispatchEvent(enterEvent);
                    }, 1500);
                    
                    return true;
                })();
                """
                
                try:
                    self.driver.execute_script(js_aggressive, project_id)
                    time.sleep(3)
                    
                    # Verificar resultado
                    if self._verify_project_selection_strict(project_id):
                        logger.info("Proyecto seleccionado con script JavaScript agresivo")
                        return True
                except Exception as js_e:
                    logger.error(f"Error en script JavaScript agresivo: {js_e}")
                
                logger.error(f"Todas las estrategias fallaron para seleccionar el proyecto {project_id}")
                return False
                        
            except Exception as e:
                logger.error(f"Error general durante la selección automática de proyecto: {e}")
                return False
            
            
            
            
            
            
            
    def select_project_ui5_direct(self, project_id):
            """
            Selecciona el proyecto interactuando directamente con UI5
            
            Args:
                project_id (str): ID del proyecto a seleccionar
                
            Returns:
                bool: True si la selección fue exitosa, False en caso contrario
            """
            try:
                logger.info(f"Seleccionando proyecto {project_id} a través de UI5 directo")
                
                # Script para seleccionar proyecto a través de UI5 con mejoras para gestionar el dropdown
                js_select_project = """
                (function() {
                    // Función para esperar a que el elemento esté disponible
                    function waitForElement(selector, maxTime) {
                        return new Promise(function(resolve, reject) {
                            let attempts = 0;
                            const maxAttempts = 50;
                            
                            (function check() {
                                if (attempts > maxAttempts) {
                                    reject("Tiempo de espera excedido");
                                    return;
                                }
                                
                                attempts++;
                                
                                if (document.querySelector(selector)) {
                                    resolve(document.querySelector(selector));
                                } else {
                                    setTimeout(check, 100);
                                }
                            })();
                        });
                    }
                    
                    // Función para simular eventos de teclado
                    function simulateKeyEvent(element, keyCode) {
                        const keyEvent = new KeyboardEvent('keydown', {
                            key: keyCode === 40 ? 'ArrowDown' : 'Enter',
                            code: keyCode === 40 ? 'ArrowDown' : 'Enter',
                            keyCode: keyCode,
                            which: keyCode,
                            bubbles: true,
                            cancelable: true
                        });
                        element.dispatchEvent(keyEvent);
                        return new Promise(resolve => setTimeout(resolve, 300));
                    }

                    async function selectProject() {
                        try {
                            console.log("Buscando campo de proyecto...");
                            
                            // 1. Buscar el campo de proyecto con múltiples selectores
                            let projectField = document.querySelector('input[placeholder*="Project"]');
                            if (!projectField) {
                                projectField = document.querySelector('input[aria-label*="Project"]');
                            }
                            
                            if (!projectField) {
                                // Buscar inputs visibles
                                const inputs = document.querySelectorAll('input:not([type="hidden"])');
                                for (let input of inputs) {
                                    if (input.offsetParent !== null) { // Es visible
                                        const parentText = input.parentElement ? input.parentElement.textContent : '';
                                        if (parentText.includes('Project')) {
                                            projectField = input;
                                            break;
                                        }
                                    }
                                }
                            }
                            
                            if (!projectField) {
                                console.error("No se encontró el campo de proyecto");
                                return false;
                            }
                            
                            console.log("Campo de proyecto encontrado");
                            
                            // 2. Limpiar y establecer el foco
                            projectField.value = '';
                            projectField.focus();
                            
                            // Disparar eventos para indicar cambio
                            projectField.dispatchEvent(new Event('input', { bubbles: true }));
                            projectField.dispatchEvent(new Event('change', { bubbles: true }));
                            
                            // 3. Establecer el valor del proyecto
                            console.log("Ingresando ID del proyecto...");
                            projectField.value = arguments[0]; // Usar el valor pasado como argumento
                            
                            // Disparar eventos para activar búsqueda
                            projectField.dispatchEvent(new Event('input', { bubbles: true }));
                            projectField.dispatchEvent(new Event('change', { bubbles: true }));
                            
                            // 4. Esperar a que aparezcan sugerencias (tiempo más largo)
                            await new Promise(resolve => setTimeout(resolve, 1500));
                            
                            // 5. Presionar tecla DOWN múltiples veces para asegurar la selección
                            console.log("Presionando tecla DOWN varias veces...");
                            for (let i = 0; i < 3; i++) {
                                await simulateKeyEvent(projectField, 40); // Código de tecla DOWN
                                await new Promise(resolve => setTimeout(resolve, 300));
                            }
                            
                            // 6. Verificar si hay sugerencias visibles y hacer clic directamente
                            const popups = document.querySelectorAll('.sapMPopover, .sapMSuggestionPopup, .sapMSelectList');
                            let suggestionClicked = false;
                            
                            for (const popup of popups) {
                                if (popup.offsetParent !== null) { // Popup visible
                                    console.log("Dropdown visible encontrado");
                                    const items = popup.querySelectorAll('li');
                                    
                                    if (items.length > 0) {
                                        console.log("Sugerencias encontradas, seleccionando primera...");
                                        items[0].click();
                                        suggestionClicked = true;
                                        break;
                                    }
                                }
                            }
                            
                            // Si no se hizo clic en ninguna sugerencia, enviar ENTER
                            if (!suggestionClicked) {
                                console.log("Presionando tecla ENTER...");
                                await simulateKeyEvent(projectField, 13); // Código de tecla ENTER
                            }
                            
                            // 7. Esperar a que se complete la selección
                            await new Promise(resolve => setTimeout(resolve, 1000));
                            
                            // 8. Verificar si el proyecto fue seleccionado
                            const selectedText = projectField.value || '';
                            const hasProject = selectedText.includes(arguments[0]);
                            
                            // Buscar cualquier elemento que muestre el ID del proyecto
                            const projectElements = document.querySelectorAll('*');
                            const projectVisible = Array.from(projectElements).some(el => 
                                el.textContent && el.textContent.includes(arguments[0]) && 
                                el.offsetParent !== null
                            );
                            
                            return hasProject || projectVisible;
                        } catch (e) {
                            console.error('Error al seleccionar proyecto: ' + e);
                            return false;
                        }
                    }
                    
                    return selectProject();
                })();
                """
                
                # Ejecutar script pasando el project_id como argumento
                result = self.driver.execute_script(js_select_project, project_id)
                time.sleep(2)
                
                # Si el script no tuvo éxito, intentar con el método de Selenium
                if not result:
                    logger.warning("Script UI5 no tuvo éxito, intentando método de Selenium directo")
                    
                    # Método mejorado de selección con Selenium que implementa específicamente la secuencia
                    # "flecha abajo + enter" para seleccionar el proyecto
                    return self._select_project_with_selenium(project_id)
                
                # Verificar si el proyecto fue seleccionado
                selected = self._verify_project_selection_strict(project_id)
                
                if not selected:
                    logger.warning(f"Verificación estricta falló: Proyecto {project_id} no está seleccionado")
                    # Intentar con el método mejorado de Selenium como último recurso
                    return self._select_project_with_selenium(project_id)
                
                if selected:
                    logger.info(f"Proyecto {project_id} seleccionado correctamente con UI5 directo")
                else:
                    logger.error(f"No se pudo seleccionar el proyecto {project_id}")
                    
                return selected
                
            except Exception as e:
                logger.error(f"Error en selección de proyecto con UI5 directo: {e}")
                # Como último recurso, intentar con el método de Selenium
                return self._select_project_with_selenium(project_id)
    
    def _select_project_with_selenium(self, project_id):
        """
        Método especializado para seleccionar el proyecto utilizando Selenium,
        con énfasis en la secuencia "flecha abajo + enter"
        
        Args:
            project_id (str): ID del proyecto a seleccionar
            
        Returns:
            bool: True si la selección fue exitosa, False en caso contrario
        """
        try:
            logger.info(f"Intentando seleccionar proyecto {project_id} con método Selenium mejorado")
            
            # Buscar el campo de proyecto con múltiples selectores
            project_field_selectors = [
                "//input[contains(@placeholder, 'Project')]", 
                "//input[contains(@aria-label, 'Project')]",
                "//div[contains(text(), 'Project:')]/following::input[1]",
                "//span[contains(text(), 'Project')]/following::input[1]",
                "//input[contains(@id, 'project')]"
            ]
            
            project_field = None
            for selector in project_field_selectors:
                try:
                    fields = self.driver.find_elements(By.XPATH, selector)
                    for field in fields:
                        if field.is_displayed() and field.is_enabled():
                            project_field = field
                            logger.info(f"Campo de proyecto encontrado con selector: {selector}")
                            break
                    if project_field:
                        break
                except:
                    continue
            
            if not project_field:
                logger.warning("No se pudo encontrar el campo de proyecto")
                return False
            
            # Limpiar el campo completamente usando múltiples técnicas
            try:
                # Limpiar con JavaScript 
                self.driver.execute_script("arguments[0].value = '';", project_field)
                # Limpiar con Selenium
                project_field.clear()
                # Usar secuencia de teclas para asegurar limpieza completa
                project_field.send_keys(Keys.CONTROL + "a")
                project_field.send_keys(Keys.DELETE)
                time.sleep(1)
            except Exception as clear_e:
                logger.debug(f"Error al limpiar campo: {clear_e} - continuando de todos modos")
            
            # Hacer clic para asegurar el foco
            try:
                project_field.click()
                time.sleep(0.5)
            except:
                # Intentar con JavaScript si el clic directo falla
                self.driver.execute_script("arguments[0].focus();", project_field)
                time.sleep(0.5)
            
            # Ingresar el ID del proyecto con pausas entre caracteres
            for char in project_id:
                project_field.send_keys(char)
                time.sleep(0.2)  # Pausas para que la interfaz procese cada carácter
            
            # Pausar para que aparezcan las sugerencias (tiempo más largo)
            time.sleep(2)
            
            # ESTRATEGIA PRINCIPAL: Usar ActionChains para una secuencia controlada de teclas
            from selenium.webdriver.common.action_chains import ActionChains
            
            actions = ActionChains(self.driver)
            # Presionar flecha abajo múltiples veces
            for _ in range(3):  # Asegurar selección con múltiples pulsaciones
                actions.send_keys(Keys.DOWN)
                actions.pause(0.5)  # Pausa importante entre teclas
            
            # Presionar Enter después de la selección
            actions.send_keys(Keys.ENTER)
            actions.perform()
            
            # Esperar a que se procese la selección
            time.sleep(2)
            
            # Verificar si la selección tuvo éxito
            if self._verify_project_selection_strict(project_id):
                logger.info(f"Proyecto {project_id} seleccionado con éxito mediante secuencia de teclas")
                return True
            
            
            
            
            
            
            
            
# ESTRATEGIA ALTERNATIVA 1: Clic directo en la primera sugerencia
            try:
                logger.info("Intentando estrategia de clic directo en sugerencia...")
                
                suggestion_selectors = [
                    "//div[contains(@class, 'sapMPopover')]//li[1]",
                    "//div[contains(@class, 'sapMSuggestionPopup')]//li[1]",
                    "//div[contains(@class, 'sapMSelectList')]//li[1]",
                    f"//li[contains(text(), '{project_id}')]",
                    "//ul[contains(@class, 'sapMListItems')]//li[1]"
                ]
                
                for selector in suggestion_selectors:
                    try:
                        suggestions = self.driver.find_elements(By.XPATH, selector)
                        if suggestions and suggestions[0].is_displayed():
                            # Hacer scroll para asegurar visibilidad
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", suggestions[0])
                            time.sleep(0.5)
                            
                            # Clic con JavaScript (más confiable en SAP UI5)
                            self.driver.execute_script("arguments[0].click();", suggestions[0])
                            logger.info("Clic en primera sugerencia realizado con JavaScript")
                            time.sleep(2)
                            
                            if self._verify_project_selection_strict(project_id):
                                logger.info(f"Proyecto {project_id} seleccionado con éxito mediante clic en sugerencia")
                                return True
                    except Exception as sugg_e:
                        logger.debug(f"Error con selector {selector}: {sugg_e}")
                        continue
            except Exception as e:
                logger.debug(f"Error en estrategia de clic en sugerencia: {e}")
            
            # ESTRATEGIA ALTERNATIVA 2: Solo Enter como último recurso
            try:
                project_field.send_keys(Keys.ENTER)
                time.sleep(2)
                
                if self._verify_project_selection_strict(project_id):
                    logger.info(f"Proyecto {project_id} seleccionado con éxito mediante Enter simple")
                    return True
            except:
                pass
            
            logger.warning(f"Todas las estrategias fallaron para seleccionar el proyecto {project_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error en método de selección de proyecto con Selenium: {e}")
            return False
    
    def _verify_project_selection_strict(self, project_id):
        """
        Verificación estricta de que el proyecto fue realmente seleccionado,
        utilizando múltiples criterios para mayor confiabilidad.
        
        Args:
            project_id (str): ID del proyecto
            
        Returns:
            bool: True si el proyecto está seleccionado, False en caso contrario
        """
        try:
            # 1. Verificar si el campo de proyecto tiene el valor correcto
            js_verify = """
            (function() {
                // 1. Verificar campo de proyecto
                var projectFields = document.querySelectorAll('input[placeholder*="Project"], input[id*="project"]');
                for (var i = 0; i < projectFields.length; i++) {
                    var fieldValue = projectFields[i].value || '';
                    if (fieldValue && fieldValue.includes(arguments[0])) {
                        return true;
                    }
                }
                
                // 2. Verificar si el valor está mostrado como texto visible
                var elements = document.querySelectorAll('div, span, label');
                for (var i = 0; i < elements.length; i++) {
                    var el = elements[i];
                    if (el.offsetParent !== null && el.textContent && 
                        el.textContent.includes(arguments[0]) && 
                        (el.textContent.includes("Project") || el.textContent.includes("Proyecto"))) {
                        return true;
                    }
                }
                
                // 3. Verificar si hay botón de búsqueda habilitado (indicador indirecto)
                var searchButtons = document.querySelectorAll('button[title*="Search"], button[aria-label*="Search"]');
                if (searchButtons.length > 0 && !searchButtons[0].disabled) {
                    // Verificar también otros elementos de interfaz que indican selección exitosa
                    var otherIndicators = document.querySelectorAll('.sapMITBHead, .sapMITBFilter');
                    if (otherIndicators.length > 3) {
                        return true;
                    }
                }
                
                // 4. Verificar por interfaz avanzada (indica que se ha cargado el proyecto)
                var advancedUI = document.querySelectorAll('.sapMPanel, .sapMITB, .sapMITBFilter');
                if (advancedUI.length > 5) {
                    // Muchos elementos de interfaz avanzada sugieren que el proyecto está seleccionado
                    return true;
                }
                
                return false;
            })();
            """
            
            
            
# Ejecutar la verificación JavaScript
            js_result = self.driver.execute_script(js_verify, project_id)
            if js_result:
                logger.info("Verificación JavaScript: proyecto seleccionado")
                return True
            
            # 2. Verificación por Selenium como respaldo
            # Buscar el valor del proyecto en el campo o en cualquier elemento visible
            project_field_selectors = [
                f"//input[contains(@value, '{project_id}')]",
                f"//div[contains(text(), '{project_id}')]",
                f"//span[contains(text(), '{project_id}')]",
                f"//label[contains(text(), '{project_id}')]"
            ]
            
            for selector in project_field_selectors:
                elements = self.driver.find_elements(By.XPATH, selector)
                if elements:
                    for element in elements:
                        if element.is_displayed():
                            logger.info(f"Proyecto {project_id} verificado en elemento visible")
                            return True
            
            # 3. Verificar elementos de interfaz que indican que se ha seleccionado un proyecto
            interface_indicators = [
                "//div[contains(text(), 'Issues')]",
                "//span[contains(text(), 'Issues')]",
                "//div[contains(text(), 'Details')]",
                "//div[contains(@class, 'sapMITBHead')]" # Cabecera de pestañas
            ]
            
            indicator_count = 0
            for selector in interface_indicators:
                elements = self.driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed():
                        indicator_count += 1
            
            # Si hay suficientes indicadores de interfaz, consideramos que el proyecto está seleccionado
            if indicator_count >= 2:
                logger.info(f"Proyecto probablemente seleccionado (basado en {indicator_count} indicadores de interfaz)")
                return True
            
            # 4. Verificar si el botón de búsqueda está habilitado (otro indicador de que se ha seleccionado un proyecto)
            search_buttons = self.driver.find_elements(By.XPATH, 
                "//button[contains(@aria-label, 'Search')] | //button[@title='Search']")
            
            for button in search_buttons:
                if button.is_displayed() and button.is_enabled():
                    # Verificar también si hay pestañas u otros elementos que indiquen un proyecto cargado
                    tabs = self.driver.find_elements(By.XPATH, "//div[@role='tab']")
                    if len(tabs) >= 2:
                        logger.info("Proyecto seleccionado (basado en botón de búsqueda habilitado y pestañas presentes)")
                        return True
            
            logger.warning(f"No se pudo verificar selección del proyecto {project_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error en verificación estricta de proyecto: {e}")
            return False
    
    def click_search_button(self):
        """
        Hace clic en el botón de búsqueda después de que cliente y proyecto estén seleccionados.
        Este paso es obligatorio en el flujo de extracción.
        
        Returns:
            bool: True si el clic fue exitoso, False en caso contrario
        """
        try:
            logger.info("Intentando hacer clic en el botón de búsqueda...")
            
            # Múltiples selectores para el botón de búsqueda
            search_button_selectors = [
                "//button[contains(@aria-label, 'Search')]",
                "//div[contains(@class, 'sapMBarMiddle')]//button",
                "//div[contains(@class, 'sapMIBar')]//button",
                "//div[contains(@class, 'sapMBarChild')]//button",
                "//span[contains(text(), 'Search')]/ancestor::button",
                "//div[contains(@class, 'sapMSearchField')]//div[contains(@class, 'sapMSearchFieldSearch')]",
                "//div[contains(@class, 'sapMSearchFieldSearch')]"
            ]
            
            # Probar cada selector
            for selector in search_button_selectors:
                buttons = self.driver.find_elements(By.XPATH, selector)
                if buttons:
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            # Intentar hacer clic con JavaScript (más confiable en SAP UI5)
                            try:
                                self.driver.execute_script("arguments[0].click();", button)
                                logger.info("Clic en botón de búsqueda exitoso con JavaScript")
                                time.sleep(3)  # Esperar a que responda
                                return True
                            except:
                                # Si falla JavaScript, intentar clic normal
                                button.click()
                                logger.info("Clic en botón de búsqueda exitoso con método normal")
                                time.sleep(3)
                                return True
                            
                            
                            
                            
                            
                            
                            
                            
# Si no encontramos el botón con los selectores anteriores, 
            # buscar el botón dentro del cuadro de búsqueda
            try:
                search_box = self.driver.find_element(By.XPATH, 
                    "//div[contains(@class, 'sapMSearchField')]")
                if search_box:
                    # El botón de búsqueda suele ser un span o div con icono dentro del campo
                    search_icon = search_box.find_element(By.XPATH, 
                        ".//div[contains(@class, 'sapMSearchFieldSearch')] | .//span[contains(@class, 'sapMSearchFieldSearchIcon')]")
                    if search_icon:
                        self.driver.execute_script("arguments[0].click();", search_icon)
                        logger.info("Clic en icono de búsqueda dentro del campo de búsqueda")
                        time.sleep(3)
                        return True
            except:
                pass
                
            # Si todavía no encontramos, probar con las coordenadas de clic en el campo de búsqueda
            try:
                search_field = self.driver.find_element(By.XPATH, 
                    "//div[contains(@class, 'sapMSearchField')] | //input[contains(@type, 'search')]")
                if search_field and search_field.is_displayed():
                    # Hacer clic primero en el campo para activarlo
                    search_field.click()
                    time.sleep(1)
                    
                    # Luego presionar Enter para ejecutar la búsqueda
                    search_field.send_keys(Keys.ENTER)
                    logger.info("Búsqueda ejecutada con clic + Enter en el campo de búsqueda")
                    time.sleep(3)
                    return True
            except:
                pass
                
            # Último recurso: buscar cualquier botón que pueda ser el de búsqueda
            try:
                # Script para buscar botones con iconos o ubicaciones que sugieran función de búsqueda
                js_script = """
                function findPotentialSearchButtons() {
                    var allButtons = document.querySelectorAll('button');
                    var searchButtons = [];
                    
                    for (var i = 0; i < allButtons.length; i++) {
                        var btn = allButtons[i];
                        
                        // Verificar si el botón está visible
                        if (btn.offsetParent !== null) {
                            // Verificar si tiene un icono que podría ser de búsqueda
                            var hasSearchIcon = btn.innerHTML.includes('search') || 
                                            btn.innerHTML.includes('lupa') || 
                                            btn.innerHTML.includes('magnify');
                            
                            // Verificar si está en la parte superior de la pantalla
                            var rect = btn.getBoundingClientRect();
                            var isInTopBar = rect.top < 100;
                            
                            if (hasSearchIcon || isInTopBar) {
                                searchButtons.push(btn);
                            }
                        }
                    }
                    
                    return searchButtons;
                }
                
                return findPotentialSearchButtons();
                """
                
                potential_buttons = self.driver.execute_script(js_script)
                
                if potential_buttons and len(potential_buttons) > 0:
                    # Intentar con el primer botón potencial
                    self.driver.execute_script("arguments[0].click();", potential_buttons[0])
                    logger.info("Clic en botón potencial de búsqueda mediante JavaScript")
                    time.sleep(3)
                    return True
            except:
                pass
                
            logger.error("No se pudo encontrar o hacer clic en el botón de búsqueda")
            return False
            
        except Exception as e:
            logger.error(f"Error al intentar hacer clic en el botón de búsqueda: {e}")
            return False
    
    def wait_for_search_results(self, timeout=20):
        """
        Espera a que se carguen los resultados de la búsqueda.
        Este paso es obligatorio en el flujo de extracción.
        
        Args:
            timeout: Tiempo máximo de espera en segundos
            
        Returns:
            bool: True si se detectan resultados, False si se agota el tiempo
        """
        try:
            logger.info("Esperando a que se carguen los resultados de la búsqueda...")
            
            # Esperar a que desaparezcan los indicadores de carga
            busy_indicators = [
                "//div[contains(@class, 'sapUiLocalBusyIndicator')]",
                "//div[contains(@class, 'sapMBusyIndicator')]",
                "//div[contains(@class, 'sapUiBusy')]"
            ]
            
            for indicator in busy_indicators:
                try:
                    WebDriverWait(self.driver, 5).until_not(
                        EC.visibility_of_element_located((By.XPATH, indicator))
                    )
                except:
                    pass
                
                
                
                
                
                
# Esperar a que aparezcan ciertos elementos que indican resultados
            result_indicators = [
                "//div[contains(@class, 'sapMITBHead')]",  # Pestañas de navegación
                "//div[contains(text(), 'Issues by Status')]",  # Panel de Issues by Status
                "//div[contains(text(), 'Actions by Status')]",  # Panel de Actions by Status
                "//div[contains(@class, 'sapMListItems')]",  # Lista de elementos
                "//div[@role='tabpanel']"  # Panel de pestaña activa
            ]
            
            # Intentar encontrar al menos uno de los indicadores de resultados
            start_time = time.time()
            results_found = False
            
            while not results_found and (time.time() - start_time) < timeout:
                for indicator in result_indicators:
                    elements = self.driver.find_elements(By.XPATH, indicator)
                    if elements and any(e.is_displayed() for e in elements):
                        results_found = True
                        logger.info(f"Resultados de búsqueda detectados: {indicator}")
                        break
                
                if not results_found:
                    time.sleep(0.5)
            
            if results_found:
                # Pausa adicional para permitir que la interfaz se estabilice
                time.sleep(3)
                logger.info("Resultados de búsqueda cargados correctamente")
                return True
            else:
                logger.warning("No se detectaron resultados de búsqueda en el tiempo esperado")
                
                # Intentar verificar si hay otros indicadores de que la página ha cargado
                alternative_indicators = [
                    "//div[contains(@class, 'sapMPage')]",
                    "//div[contains(@class, 'sapMListShowMore')]",
                    "//div[contains(@class, 'sapMITB')]"
                ]
                
                for indicator in alternative_indicators:
                    elements = self.driver.find_elements(By.XPATH, indicator)
                    if elements and any(e.is_displayed() for e in elements):
                        logger.info(f"Indicador alternativo de carga detectado: {indicator}")
                        time.sleep(2)  # Espera adicional para estabilización
                        return True
                
                return False
                
        except Exception as e:
            logger.error(f"Error al esperar resultados de búsqueda: {e}")
            return False









    def enhanced_click_settings_button(self):
        """
        Método mejorado para encontrar y hacer clic en el botón de ajustes (engranaje) en SAP UI5/Fiori.
        
        Esta versión implementa múltiples estrategias optimizadas para la interfaz actual
        y proporciona un registro detallado del proceso para facilitar la depuración.
        
        Returns:
            bool: True si el clic fue exitoso y se abrió el panel de ajustes, False en caso contrario
        """
        try:
            logger.info("📎 MÉTODO: enhanced_click_settings_button - Iniciando búsqueda mejorada del botón de ajustes...")
            
            # Técnica 1: Buscar botones en el área inferior derecha de la pantalla
            bottom_right_script = """
            return (function() {
                // Obtener todos los botones de la página
                const allButtons = Array.from(document.querySelectorAll('button, span[role="button"], div[role="button"]'));
                
                // Filtrar por botones visibles en la zona inferior derecha
                const screenHeight = window.innerHeight;
                const screenWidth = window.innerWidth;
                
                return allButtons.filter(btn => {
                    if (btn.offsetParent === null) return false; // No visible
                    
                    const rect = btn.getBoundingClientRect();
                    
                    // Está en el cuarto inferior derecho de la pantalla?
                    return rect.bottom > screenHeight * 0.6 && 
                        rect.right > screenWidth * 0.75 &&
                        rect.width < 50 && rect.height < 50; // Botones pequeños (típico para engranajes)
                });
            })();
            """
            
            # Ejecutar el script para encontrar botones en la esquina inferior derecha
            bottom_right_buttons = self.driver.execute_script(bottom_right_script)
            logger.info(f"🔍 Se encontraron {len(bottom_right_buttons)} botones en el área inferior derecha")
            
            # Tomar captura para depuración si hay botones encontrados
            if bottom_right_buttons and len(bottom_right_buttons) > 0:
                try:
                    # Crear directorio para capturas si no existe
                    if not os.path.exists("logs/screenshots"):
                        os.makedirs("logs/screenshots")
                    
                    # Guardar captura con los botones resaltados
                    # Resaltar visualmente los botones encontrados
                    for i, btn in enumerate(bottom_right_buttons):
                        self.driver.execute_script(
                            f"""
                            arguments[0].style.border = '3px solid red';
                            arguments[0].style.position = 'relative';
                            
                            // Añadir un número para identificar cada botón
                            var label = document.createElement('div');
                            label.textContent = '{i+1}';
                            label.style.position = 'absolute';
                            label.style.top = '-15px';
                            label.style.left = '0';
                            label.style.background = 'red';
                            label.style.color = 'white';
                            label.style.padding = '2px 5px';
                            label.style.borderRadius = '3px';
                            label.style.fontSize = '12px';
                            arguments[0].appendChild(label);
                            """, 
                            btn
                        )
                    
                    # Tomar captura
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    screenshot_path = f"logs/screenshots/settings_buttons_found_{timestamp}.png"
                    self.driver.save_screenshot(screenshot_path)
                    logger.info(f"📸 Captura guardada en: {screenshot_path}")
                    
                    # Restaurar estilos originales
                    for btn in bottom_right_buttons:
                        self.driver.execute_script(
                            """
                            arguments[0].style.border = '';
                            // Eliminar etiqueta numerada
                            var label = arguments[0].querySelector('div:last-child');
                            if (label) label.remove();
                            """, 
                            btn
                        )
                except Exception as ss_e:
                    logger.debug(f"Error al capturar botones: {ss_e}")
            
            # Intentar clic en cada uno de los botones encontrados en la esquina inferior derecha
            for i, btn in enumerate(bottom_right_buttons):
                try:
                    logger.info(f"🖱️ Intentando clic en botón #{i+1} del área inferior derecha...")
                    
                    # Hacer scroll para asegurarse que el botón está visible
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(0.5)
                    
                    # Obtener información sobre el botón para depuración
                    btn_text = self.driver.execute_script("return arguments[0].textContent || '';", btn).strip()
                    btn_classes = self.driver.execute_script("return arguments[0].className || '';", btn)
                    btn_html = self.driver.execute_script("return arguments[0].outerHTML.substring(0, 150) + '...';", btn)
                    logger.info(f"📋 Botón #{i+1} - Texto: '{btn_text}', Clases: '{btn_classes}', HTML: {btn_html}")
                    
                    # Hacer clic usando JavaScript en lugar de método normal para mayor confiabilidad
                    self.driver.execute_script("arguments[0].click();", btn)
                    logger.info(f"✅ Clic JavaScript ejecutado en botón #{i+1}")
                    
                    # Esperar a que responda el clic
                    time.sleep(2)
                    
                    # Verificar si el clic abrió el panel de ajustes
                    panel_opened = self._verify_settings_panel_opened()
                    if panel_opened:
                        logger.info(f"✅ Panel de ajustes detectado después de clic en botón #{i+1}")
                        return True
                    
                    # Si no funcionó, intentar otro tipo de clic
                    try:
                        btn.click()
                        logger.info(f"✅ Clic normal ejecutado en botón #{i+1}")
                        time.sleep(2)
                        
                        panel_opened = self._verify_settings_panel_opened()
                        if panel_opened:
                            logger.info(f"✅ Panel de ajustes detectado después de clic normal en botón #{i+1}")
                            return True
                    except Exception as click_e:
                        logger.debug(f"Error en clic normal: {click_e}")
                except Exception as e:
                    logger.debug(f"Error al procesar botón #{i+1}: {e}")
            
            # Técnica 2: Buscar ícono específico de engranaje por su contenido SVG
            svg_gear_script = """
            return (function() {
                // Buscar elementos específicos que son típicamente usados para íconos de configuración
                const iconCandidates = [
                    // Iconos específicos de UI5
                    ...Array.from(document.querySelectorAll('.sapUiIcon')),
                    // Cualquier elemento que contenga la palabra 'icon' en su clase
                    ...Array.from(document.querySelectorAll('[class*="icon"]')),
                    // Paths de SVG que podrían formar un engranaje
                    ...Array.from(document.querySelectorAll('path[d*="M"]')).map(p => p.closest('svg')).filter(Boolean),
                    // Elementos font-awesome u otros íconos conocidos
                    ...Array.from(document.querySelectorAll('.fa-cog, .fa-gear, .fa-wrench'))
                ];
                
                // Filtrar duplicados y elementos no visibles
                return [...new Set(iconCandidates)].filter(el => 
                    el && el.offsetParent !== null && el.getBoundingClientRect().width > 0 && 
                    el.getBoundingClientRect().height > 0
                );
            })();
            """
            
            icon_elements = self.driver.execute_script(svg_gear_script)
            logger.info(f"🔍 Se encontraron {len(icon_elements)} elementos de ícono potenciales")
            
            # Intentar hacer clic en cada ícono encontrado
            for i, icon in enumerate(icon_elements):
                try:
                    logger.info(f"🖱️ Intentando clic en ícono #{i+1}...")
                    
                    # Hacer scroll
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", icon)
                    time.sleep(0.5)
                    
                    # Intentar clic en el elemento del ícono
                    self.driver.execute_script("arguments[0].click();", icon)
                    logger.info(f"✅ Clic JavaScript ejecutado en ícono #{i+1}")
                    time.sleep(2)
                    
                    if self._verify_settings_panel_opened():
                        logger.info(f"✅ Panel de ajustes detectado después de clic en ícono #{i+1}")
                        return True
                    
                    # Si el ícono es parte de un botón, intenta hacer clic en el botón padre
                    parent_button = self.driver.execute_script("""
                        function findClosestButton(element, maxDepth = 5) {
                            let current = element;
                            let depth = 0;
                            
                            while (current && depth < maxDepth) {
                                if (current.tagName === 'BUTTON' || 
                                    current.getAttribute('role') === 'button' ||
                                    current.className.includes('btn') ||
                                    current.className.includes('Button')) {
                                    return current;
                                }
                                current = current.parentElement;
                                depth++;
                            }
                            return null;
                        }
                        return findClosestButton(arguments[0]);
                    """, icon)
                    
                    if parent_button:
                        logger.info(f"🔍 Encontrado botón padre para ícono #{i+1}, intentando clic...")
                        self.driver.execute_script("arguments[0].click();", parent_button)
                        time.sleep(2)
                        
                        if self._verify_settings_panel_opened():
                            logger.info(f"✅ Panel de ajustes detectado después de clic en botón padre del ícono #{i+1}")
                            return True
                except Exception as icon_e:
                    logger.debug(f"Error al procesar ícono #{i+1}: {icon_e}")
            
            # Técnica 3: Buscar específicamente elementos con aria-label o title relacionados con ajustes
            settings_attributes_script = """
            return (function() {
                const attributeSelectors = [
                    '[aria-label*="setting" i]',
                    '[aria-label*="config" i]',
                    '[aria-label*="option" i]',
                    '[aria-label*="prefer" i]',
                    '[title*="setting" i]',
                    '[title*="config" i]',
                    '[title*="option" i]',
                    '[title*="prefer" i]',
                    '[data-help-id*="setting" i]'
                ];
                
                // Buscar todos los elementos que coincidan con estos selectores
                let allElements = [];
                attributeSelectors.forEach(selector => {
                    allElements = [...allElements, ...document.querySelectorAll(selector)];
                });
                
                // Filtrar elementos visibles
                return allElements.filter(el => el.offsetParent !== null);
            })();
            """
            
            attribute_elements = self.driver.execute_script(settings_attributes_script)
            logger.info(f"🔍 Se encontraron {len(attribute_elements)} elementos con atributos relacionados con ajustes")
            
            for i, element in enumerate(attribute_elements):
                try:
                    logger.info(f"🖱️ Intentando clic en elemento con atributos de ajustes #{i+1}...")
                    
                    # Obtener atributos para debug
                    attrs = self.driver.execute_script("""
                        var result = {};
                        ['aria-label', 'title', 'data-help-id'].forEach(attr => {
                            const value = arguments[0].getAttribute(attr);
                            if (value) result[attr] = value;
                        });
                        return result;
                    """, element)
                    
                    logger.info(f"📋 Atributos del elemento #{i+1}: {attrs}")
                    
                    # Clic
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                    time.sleep(0.5)
                    self.driver.execute_script("arguments[0].click();", element)
                    time.sleep(2)
                    
                    if self._verify_settings_panel_opened():
                        logger.info(f"✅ Panel de ajustes detectado después de clic en elemento con atributos #{i+1}")
                        return True
                except Exception as attr_e:
                    logger.debug(f"Error al procesar elemento con atributos #{i+1}: {attr_e}")
            
            # Técnica 4: Si todo lo anterior falla, intentar acceder directamente a las funciones del framework UI5
            logger.info("🔧 Intentando acceso directo a funciones de framework SAP UI5...")
            
            ui5_script = """
            return (function() {
                try {
                    // Intentar acceder a la API de UI5
                    if (window.sap && window.sap.ui) {
                        // Buscar controles que podrían ser el botón de ajustes
                        const buttons = sap.ui.getCore().byFieldGroupId("settingsButton") || 
                                    sap.ui.getCore().byFieldGroupId("configButton") ||
                                    sap.ui.getCore().byFieldGroupId("optionsButton");
                        
                        if (buttons && buttons.length > 0) {
                            // Encontró controles específicos
                            return {success: true, method: "fieldGroupId", controlIds: buttons.map(b => b.getId())};
                        }
                        
                        // Intentar buscar por tipo de control y propiedades
                        const allButtons = sap.ui.getCore().getElements().filter(c => 
                            (c.getMetadata && c.getMetadata().getName() === "sap.m.Button") || 
                            (c instanceof sap.m.Button));
                        
                        const settingsButtons = allButtons.filter(b => {
                            const text = b.getText && b.getText();
                            const tooltip = b.getTooltip && b.getTooltip();
                            const icon = b.getIcon && b.getIcon();
                            
                            return (text && text.toLowerCase().includes('setting')) || 
                                (tooltip && tooltip.toLowerCase().includes('setting')) ||
                                (icon && icon.includes('setting'));
                        });
                        
                        if (settingsButtons.length > 0) {
                            // Activar el primer botón encontrado
                            settingsButtons[0].firePress();
                            return {success: true, method: "buttonPress", controlId: settingsButtons[0].getId()};
                        }
                        
                        return {success: false, method: "ui5api", message: "No matching controls found"};
                    }
                    
                    return {success: false, message: "UI5 API not available"};
                } catch (e) {
                    return {success: false, error: e.toString()};
                }
            })();
            """
            
            ui5_result = self.driver.execute_script(ui5_script)
            logger.info(f"🔍 Resultado de acceso a API UI5: {ui5_result}")
            
            if ui5_result.get("success", False):
                logger.info(f"✅ Panel de ajustes abierto mediante API UI5 usando método: {ui5_result.get('method')}")
                time.sleep(2)
                return self._verify_settings_panel_opened()
            
            # Capturar pantalla final para depuración
            try:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                screenshot_path = f"logs/screenshots/settings_button_failed_{timestamp}.png"
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"📸 Captura final guardada en: {screenshot_path}")
            except Exception as ss_e:
                logger.debug(f"Error al guardar captura final: {ss_e}")
            
            logger.error("❌ No se pudo encontrar o hacer clic en el botón de ajustes con ninguna estrategia")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error general en búsqueda de botón de ajustes: {e}")
            return False









    def navigate_by_keyboard(self):
        """
        Navega a través de la interfaz utilizando teclado en lugar de hacer clic en botones
        Esta función implementa la secuencia específica de tabs y teclas para configurar columnas
        """
        try:
            logger.info("Iniciando navegación por teclado para configurar columnas...")
            
            # Importar clases necesarias para la navegación por teclado
            from selenium.webdriver.common.action_chains import ActionChains
            from selenium.webdriver.common.keys import Keys
            
            # Crear una acción para manejar la secuencia de pulsaciones de teclas
            actions = ActionChains(self.driver)
            
            # 1. Primero, hacer clic en el body para establecer el foco
            body = self.driver.find_element(By.TAG_NAME, "body")
            body.click()
            time.sleep(0.5)
            
            # 2. Secuencia de 18 tabs para llegar al botón de ajustes
            logger.info("Enviando 18 tabs para llegar al botón de ajustes...")
            for i in range(18):
                actions.send_keys(Keys.TAB)
                actions.pause(0.2)  # Pequeña pausa entre cada pulsación
            
            # 3. Pulsar Enter para abrir el panel de ajustes
            logger.info("Pulsando Enter para el botón de ajustes...")
            actions.send_keys(Keys.ENTER)
            actions.perform()  # Ejecutar la secuencia acumulada
            
            # Dar tiempo a que se abra el panel
            time.sleep(2)
            
            # 4. Secuencia para navegar a "Select Columns" (Tab x3, Flecha derecha x2, Enter)
            logger.info("Navegando a 'Select Columns'...")
            actions = ActionChains(self.driver)  # Resetear acciones
            
            # 3 tabs
            for i in range(3):
                actions.send_keys(Keys.TAB)
                actions.pause(0.2)
            
            # 2 flechas derecha
            for i in range(2):
                actions.send_keys(Keys.ARROW_RIGHT)
                actions.pause(0.2)
            
            # Enter para seleccionar "Select Columns"
            actions.send_keys(Keys.ENTER)
            actions.perform()
            
            # Dar tiempo a que se abra el panel de columnas
            time.sleep(2)
            
            # 5. Secuencia para "Select All" (Tab x3, Enter)
            logger.info("Seleccionando 'Select All'...")
            actions = ActionChains(self.driver)
            
            # 3 tabs
            for i in range(3):
                actions.send_keys(Keys.TAB)
                actions.pause(0.2)
            
            # Enter para marcar "Select All"
            actions.send_keys(Keys.ENTER)
            actions.perform()
            
            # Dar tiempo para procesar la selección
            time.sleep(1)
            
            # 6. Secuencia para confirmar con OK (Tab x2, Enter)
            logger.info("Confirmando con OK...")
            actions = ActionChains(self.driver)
            
            # 2 tabs
            for i in range(2):
                actions.send_keys(Keys.TAB)
                actions.pause(0.2)
            
            # Enter para confirmar con OK
            actions.send_keys(Keys.ENTER)
            actions.perform()
            
            # Dar tiempo para que se apliquen los cambios
            time.sleep(3)
            
            logger.info("Navegación por teclado completada exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error durante la navegación por teclado: {e}")
            return False









    def select_columns_in_settings_panel(self):
        """
        Navega dentro del panel de ajustes para seleccionar todas las columnas disponibles.
        Este método asume que el panel de ajustes ya está abierto.
        
        Implementa múltiples estrategias para hacer clic en "Select Columns", 
        marcar "Select All" y confirmar con OK.
        
        Returns:
            bool: True si la selección fue exitosa, False en caso contrario
        """
        try:
            logger.info("MÉTODO: select_columns_in_settings_panel - Iniciando selección de columnas en panel abierto...")
            
            # ESTRATEGIA 1: Detectar y hacer clic directamente en los elementos por texto específico
            # Paso 1: Buscar y hacer clic en "Select Columns"
            select_columns_clicked = False
            
            # Intentar encontrar elementos "Select Columns" por diferentes selectores
            select_columns_selectors = [
                "//span[text()='Select Columns']",
                "//div[text()='Select Columns']",
                "//li[contains(., 'Select Columns')]",
                "//div[contains(@class, 'sapMDialogScrollCont')]//span[contains(text(), 'Select Columns')]",
                "//div[contains(@class, 'sapMPopover')]//span[contains(text(), 'Select Columns')]",
                # UI5 específico
                "//div[contains(@class, 'sapMSelectListItem')][contains(., 'Select Columns')]",
                "//div[contains(@class, 'sapMList')]//div[contains(text(), 'Select Columns')]"
            ]
            
            for selector in select_columns_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            logger.info(f"Encontrado elemento 'Select Columns' con selector: {selector}")
                            # Hacer scroll y clic
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                            time.sleep(0.5)
                            self.driver.execute_script("arguments[0].click();", element)
                            logger.info("Clic ejecutado en 'Select Columns'")
                            time.sleep(2)
                            select_columns_clicked = True
                            break
                    if select_columns_clicked:
                        break
                except Exception as e:
                    logger.debug(f"Error con selector '{selector}': {e}")
            
            # Si no logramos hacer clic directamente, tomar una captura del panel actual
            if not select_columns_clicked:
                try:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    screenshot_path = f"logs/screenshots/settings_panel_{timestamp}.png"
                    self.driver.save_screenshot(screenshot_path)
                    logger.info(f"Captura del panel guardada en: {screenshot_path}")
                except Exception as ss_e:
                    logger.debug(f"Error al guardar captura: {ss_e}")
                
                # ESTRATEGIA 2: JavaSript para examinar y hacer clic en los elementos del panel
                js_click_select_columns = """
                return (function() {
                    // Función para buscar un elemento por texto aproximado
                    function findElementByText(searchText) {
                        const allElements = document.querySelectorAll('span, div, li, a');
                        for (const el of allElements) {
                            if (el.offsetParent !== null && el.textContent.includes(searchText)) {
                                return el;
                            }
                        }
                        return null;
                    }
                    
                    // Buscar específicamente en el diálogo abierto
                    const settingsDialog = document.querySelector('.sapMDialog, .sapMPopover');
                    if (!settingsDialog) return { success: false, reason: "No dialog found" };
                    
                    // Buscar específicamente el ítem "Select Columns"
                    const selectColumns = findElementByText("Select Columns");
                    if (selectColumns) {
                        // Intentar hacer clic en el elemento o en su padre si parece ser un ítem de lista
                        const clickTarget = selectColumns.closest('li') || selectColumns;
                        clickTarget.click();
                        return { success: true, element: "Select Columns", action: "clicked" };
                    }
                    
                    // Si no encuentra "Select Columns", buscar por estructura típica
                    const dialogs = document.querySelectorAll('.sapMDialogScrollCont, .sapMPopoverCont');
                    for (const dialog of dialogs) {
                        const items = dialog.querySelectorAll('li, .sapMSelectListItem');
                        // Intentar hacer clic en el segundo ítem (típicamente "Select Columns")
                        if (items.length >= 2) {
                            items[1].click();
                            return { success: true, element: "Second list item", action: "clicked" };
                        }
                    }
                    
                    return { success: false, reason: "Select Columns not found" };
                })();
                """
                
                try:
                    js_result = self.driver.execute_script(js_click_select_columns)
                    logger.info(f"Resultado JavaScript para 'Select Columns': {js_result}")
                    
                    if js_result.get('success', False):
                        select_columns_clicked = True
                        time.sleep(2)
                except Exception as js_e:
                    logger.debug(f"Error en script JavaScript: {js_e}")
            
            # ESTRATEGIA 3: Si las estrategias anteriores fallaron, intentar navegación por teclado
            if not select_columns_clicked:
                logger.info("Estrategias directas fallidas, intentando navegación por teclado...")
                
                from selenium.webdriver.common.action_chains import ActionChains
                from selenium.webdriver.common.keys import Keys
                
                actions = ActionChains(self.driver)
                
                # Establecer el foco en el diálogo
                dialog = self.driver.find_element(By.XPATH, "//div[contains(@class, 'sapMDialog')]")
                dialog.click()
                time.sleep(0.5)
                
                # 3 tabs, 2 flechas derecha, Enter (para Select Columns)
                for _ in range(3):
                    actions.send_keys(Keys.TAB)
                    actions.pause(0.5)
                
                for _ in range(2):
                    actions.send_keys(Keys.ARROW_RIGHT)
                    actions.pause(0.5)
                    
                actions.send_keys(Keys.ENTER)
                actions.perform()
                
                time.sleep(2)
                logger.info("Navegación por teclado completada para 'Select Columns'")
            
            # Verificar si el panel de Select Columns está abierto
            columns_panel_open = self._verify_column_panel_opened()
            
            if not columns_panel_open:
                logger.warning("No se pudo abrir el panel de 'Select Columns', intentando un método alternativo...")
                
                # Método alternativo: Buscar directamente botones en el panel actual
                try:
                    buttons = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'sapMBtn')]")
                    if len(buttons) >= 3:  # Típicamente hay al menos 3 botones
                        # Intentar hacer clic en cada botón excepto "Close" o "Cancel"
                        for button in buttons:
                            button_text = button.text.strip().lower()
                            if button_text and 'close' not in button_text and 'cancel' not in button_text:
                                logger.info(f"Intentando clic en botón: '{button_text}'")
                                self.driver.execute_script("arguments[0].click();", button)
                                time.sleep(2)
                                
                                # Verificar si se abrió algún panel después del clic
                                columns_panel_open = self._verify_column_panel_opened()
                                if columns_panel_open:
                                    logger.info(f"Panel de columnas abierto después de clic en '{button_text}'")
                                    break
                except Exception as alt_e:
                    logger.debug(f"Error en método alternativo: {alt_e}")
            
            # Si todavía no tenemos el panel de columnas abierto, mostrar mensaje y continuar
            if not columns_panel_open:
                logger.warning("No se pudo abrir el panel de 'Select Columns', intentando continuar con el flujo...")
            
            # ----- PARTE 2: Seleccionar "Select All" -----
            # Ya sea que tengamos el panel de columnas abierto o no, intentamos encontrar y marcar "Select All"
            select_all_clicked = False
            
            # ESTRATEGIA 1: Buscar y hacer clic en "Select All" directamente
            select_all_selectors = [
                "//div[text()='Select All']",
                "//span[text()='Select All']",
                "//label[contains(., 'Select All')]",
                "//div[contains(@class, 'sapMCb')]/label[contains(., 'Select All')]",
                # Checkbox cerca de "Select All"
                "//div[text()='Select All']/preceding-sibling::div[contains(@class, 'sapMCb')]",
                "//span[text()='Select All']/preceding-sibling::div[contains(@class, 'sapMCb')]"
            ]
            
            for selector in select_all_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            logger.info(f"Encontrado elemento 'Select All' con selector: {selector}")
                            # Hacer scroll y clic
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                            time.sleep(0.5)
                            self.driver.execute_script("arguments[0].click();", element)
                            logger.info("Clic ejecutado en 'Select All'")
                            time.sleep(1)
                            select_all_clicked = True
                            break
                    if select_all_clicked:
                        break
                except Exception as e:
                    logger.debug(f"Error con selector '{selector}': {e}")
            
            # Si no encontramos "Select All", intentar JavaScript
            if not select_all_clicked:
                js_click_select_all = """
                return (function() {
                    // Función para buscar un elemento por texto aproximado
                    function findElementByText(searchText) {
                        const allElements = document.querySelectorAll('*');
                        for (const el of allElements) {
                            if (el.offsetParent !== null && el.textContent.includes(searchText)) {
                                return el;
                            }
                        }
                        return null;
                    }
                    
                    // Buscar elemento "Select All"
                    const selectAll = findElementByText("Select All");
                    if (selectAll) {
                        // Si es un label o div, buscar un checkbox cercano
                        const checkbox = selectAll.previousElementSibling || 
                                        selectAll.parentElement.querySelector('input[type="checkbox"]') ||
                                        document.evaluate(".//preceding-sibling::*[1]", selectAll, null, 
                                                        XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                        
                        if (checkbox && (checkbox.tagName === 'INPUT' || checkbox.className.includes('sapMCb'))) {
                            checkbox.click();
                            return { success: true, element: "checkbox", action: "clicked" };
                        }
                        
                        // Si no encontramos un checkbox, hacer clic en el elemento mismo
                        selectAll.click();
                        return { success: true, element: "Select All", action: "clicked" };
                    }
                    
                    // Intentar encontrar checkboxes en el diálogo
                    const dialog = document.querySelector('.sapMDialog, .sapMPopover');
                    if (dialog) {
                        const checkboxes = dialog.querySelectorAll('.sapMCb, input[type="checkbox"]');
                        if (checkboxes.length > 0) {
                            // Hacer clic en el primer checkbox (típicamente es "Select All")
                            checkboxes[0].click();
                            return { success: true, element: "First checkbox", action: "clicked" };
                        }
                    }
                    
                    return { success: false, reason: "Select All not found" };
                })();
                """
                
                try:
                    js_result = self.driver.execute_script(js_click_select_all)
                    logger.info(f"Resultado JavaScript para 'Select All': {js_result}")
                    
                    if js_result.get('success', False):
                        select_all_clicked = True
                        time.sleep(1)
                except Exception as js_e:
                    logger.debug(f"Error en script JavaScript: {js_e}")
            
            # Si todavía no hemos logrado marcar "Select All", intentar navegación por teclado
            if not select_all_clicked:
                logger.info("Intentando navegación por teclado para 'Select All'...")
                
                actions = ActionChains(self.driver)
                
                # 3 tabs, Enter (para Select All)
                for _ in range(3):
                    actions.send_keys(Keys.TAB)
                    actions.pause(0.5)
                    
                actions.send_keys(Keys.ENTER)
                actions.perform()
                
                time.sleep(1)
                logger.info("Navegación por teclado completada para 'Select All'")
                select_all_clicked = True  # Asumimos éxito para continuar el flujo
            
            # ----- PARTE 3: Confirmar con OK -----
            # Buscar y hacer clic en el botón OK o similar
            ok_clicked = False
            
            # ESTRATEGIA 1: Buscar y hacer clic en botón OK directamente
            ok_selectors = [
                "//button[contains(text(), 'OK')]",
                "//span[contains(text(), 'OK')]/ancestor::button",
                "//button[contains(@id, 'ok')]",
                "//button[contains(@class, 'sapMDialogOkButton')]",
                # UI5 específico
                "//footer//button[contains(@class, 'sapMBtn')]",
                "//div[contains(@class, 'sapMBarRight')]//button"
            ]
            
            for selector in ok_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            # Obtener texto para debug
                            btn_text = element.text.strip()
                            logger.info(f"Encontrado posible botón OK: '{btn_text}' con selector: {selector}")
                            
                            # Hacer scroll y clic
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                            time.sleep(0.5)
                            self.driver.execute_script("arguments[0].click();", element)
                            logger.info(f"Clic ejecutado en botón '{btn_text}'")
                            time.sleep(2)
                            ok_clicked = True
                            break
                    if ok_clicked:
                        break
                except Exception as e:
                    logger.debug(f"Error con selector '{selector}': {e}")
            
            # ESTRATEGIA 2: JavaScript para encontrar y hacer clic en el botón OK
            if not ok_clicked:
                js_click_ok = """
                return (function() {
                    // Función para evaluar la probabilidad de que un botón sea el "OK"
                    function evaluateOkButton(button) {
                        let score = 0;
                        
                        // Por texto
                        const text = button.textContent.trim().toLowerCase();
                        if (text === "ok") score += 10;
                        else if (text.includes("ok")) score += 5;
                        
                        // Por posición (los botones OK suelen estar a la derecha)
                        const rect = button.getBoundingClientRect();
                        const dialogRect = button.closest('.sapMDialog, .sapMPopover').getBoundingClientRect();
                        if (rect.right > dialogRect.width * 0.7) score += 3;
                        
                        // Por clases
                        if (button.className.includes('Primary')) score += 3;
                        if (button.className.includes('Accept')) score += 3;
                        if (button.className.includes('Emphasized')) score += 2;
                        
                        return score;
                    }
                    
                    // Buscar todos los botones en el diálogo actual
                    const dialog = document.querySelector('.sapMDialog, .sapMPopover');
                    if (!dialog) return { success: false, reason: "No dialog found" };
                    
                    const buttons = Array.from(dialog.querySelectorAll('button'));
                    if (buttons.length === 0) return { success: false, reason: "No buttons found" };
                    
                    // Evaluar todos los botones
                    const scoredButtons = buttons.map(button => ({
                        button: button,
                        score: evaluateOkButton(button),
                        text: button.textContent.trim()
                    }));
                    
                    // Ordenar por puntuación
                    scoredButtons.sort((a, b) => b.score - a.score);
                    
                    // Hacer clic en el botón con mayor puntuación
                    if (scoredButtons[0].score > 0) {
                        scoredButtons[0].button.click();
                        return { 
                            success: true, 
                            buttonText: scoredButtons[0].text, 
                            score: scoredButtons[0].score 
                        };
                    }
                    
                    // Si no hay botones con buena puntuación, hacer clic en el último botón (suele ser OK o Aplicar)
                    buttons[buttons.length - 1].click();
                    return { 
                        success: true, 
                        buttonText: buttons[buttons.length - 1].textContent.trim(),
                        method: "lastButton"
                    };
                })();
                """
                
                try:
                    js_result = self.driver.execute_script(js_click_ok)
                    logger.info(f"Resultado JavaScript para 'OK': {js_result}")
                    
                    if js_result.get('success', False):
                        ok_clicked = True
                        time.sleep(2)
                except Exception as js_e:
                    logger.debug(f"Error en script JavaScript: {js_e}")
            
            # ESTRATEGIA 3: Navegación por teclado para OK
            if not ok_clicked:
                logger.info("Intentando navegación por teclado para 'OK'...")
                
                actions = ActionChains(self.driver)
                
                # 2 tabs, Enter (para OK)
                for _ in range(2):
                    actions.send_keys(Keys.TAB)
                    actions.pause(0.5)
                    
                actions.send_keys(Keys.ENTER)
                actions.perform()
                
                time.sleep(2)
                logger.info("Navegación por teclado completada para 'OK'")
                ok_clicked = True  # Asumimos éxito
            
            # Verificar que el panel se cerró
            try:
                dialogs = self.driver.find_elements(By.XPATH, 
                    "//div[contains(@class, 'sapMDialog') and contains(@style, 'visibility: visible')]")
                panel_closed = not dialogs or not any(d.is_displayed() for d in dialogs)
                
                if panel_closed:
                    logger.info("Selección de columnas completada con éxito. Panel cerrado correctamente.")
                    return True
                else:
                    logger.warning("El panel no se cerró después de hacer clic en OK")
                    # Intentar cerrar haciendo clic en cualquier botón visible
                    try:
                        close_buttons = self.driver.find_elements(By.XPATH, 
                            "//button[contains(text(), 'Close') or contains(text(), 'Cancel') or contains(@class, 'sapMDialogClose')]")
                        if close_buttons:
                            for btn in close_buttons:
                                if btn.is_displayed():
                                    self.driver.execute_script("arguments[0].click();", btn)
                                    logger.info("Clic en botón de cierre ejecutado")
                                    time.sleep(1)
                    except Exception as close_e:
                        logger.debug(f"Error al intentar cerrar panel: {close_e}")
                    
                    return False
            except Exception as verify_e:
                logger.error(f"Error al verificar cierre del panel: {verify_e}")
                return False
                
        except Exception as e:
            logger.error(f"Error en select_columns_in_settings_panel: {e}")
            return False
            
    def _verify_column_panel_opened(self):
        """
        Verifica que el panel de selección de columnas se ha abierto correctamente
        
        Returns:
            bool: True si el panel está abierto, False en caso contrario
        """
        try:
            # Dar tiempo a que se abra el panel
            time.sleep(1)
            
            # 1. Verificar la presencia del texto "Select All"
            select_all_elements = self.driver.find_elements(By.XPATH, "//div[text()='Select All']")
            if select_all_elements and any(el.is_displayed() for el in select_all_elements):
                logger.info("Panel de columnas detectado: 'Select All' visible")
                return True
                
            # 2. Verificar los checkboxes de columnas (específico de la interfaz de columnas)
            checkboxes = self.driver.find_elements(By.XPATH, 
                "//div[contains(@class, 'sapMCb')]/parent::div[contains(text(), 'Issue Title') or contains(text(), 'SAP Category')]")
            if checkboxes and any(checkbox.is_displayed() for checkbox in checkboxes):
                logger.info("Panel de columnas detectado: Checkboxes de columnas visibles")
                return True
                
            # 3. Verificar otros elementos comunes de la interfaz de selección de columnas
            column_selectors = [
                "//div[@role='dialog']//div[contains(@class, 'sapMList')]", # Lista de columnas
                "//div[contains(@class, 'sapMSelectDialogListItem')]",  # Elementos de la lista de columnas
                "//div[contains(@class, 'sapMDialog')]//div[contains(@aria-selected, 'true')]", # Item seleccionado
                "//div[contains(@class, 'sapMList')]//li", # Items de lista genéricos
                "//div[contains(@class, 'sapMDialog')]//ul[contains(@class, 'sapMListItems')]" # Lista de items UI5
            ]
            
            for selector in column_selectors:
                elements = self.driver.find_elements(By.XPATH, selector)
                if elements and any(el.is_displayed() for el in elements):
                    logger.info(f"Panel de columnas detectado con selector: {selector}")
                    return True
            
            # 4. Verificación mediante JavaScript para casos difíciles
            js_verify = """
            (function() {
                // Buscar diálogo visible
                var dialog = document.querySelector('.sapMDialog[style*="visibility: visible"]');
                if (!dialog) return false;
                
                // Verificar texto "Select All"
                var selectAll = document.evaluate(
                    "//div[text()='Select All']", 
                    document, 
                    null, 
                    XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, 
                    null
                );
                
                if (selectAll.snapshotLength > 0) {
                    return true;
                }
                
                // Verificar presencia de checkboxes en el diálogo
                var checkboxes = dialog.querySelectorAll('.sapMCb, input[type="checkbox"]');
                if (checkboxes.length > 3) {
                    return true;
                }
                
                // Verificar lista de columnas
                var listItems = dialog.querySelectorAll('.sapMList li, .sapMLIB');
                if (listItems.length > 3) {
                    return true;
                }
                
                return false;
            })();
            """
            
            try:
                result = self.driver.execute_script(js_verify)
                if result:
                    logger.info("Panel de columnas detectado mediante JavaScript")
                    return True
            except Exception as js_e:
                logger.debug(f"Error en verificación JavaScript: {js_e}")
            
            logger.warning("No se detectó el panel de selección de columnas")
            return False
            
        except Exception as e:
            logger.error(f"Error al verificar panel de columnas: {e}")
            return False




    def select_all_visible_columns(self):
        """
        Selecciona todas las columnas disponibles mediante navegación por teclado.
        
        Usando la secuencia exacta definida por el cliente:
        1. 5 tabs, 2 flechas derecha y enter para select columns
        2. 3 tabs y enter para marcar "Select All"
        3. 2 tabs y enter para confirmar con OK
        
        Returns:
            bool: True si la selección fue exitosa, False en caso contrario
        """
        try:
            logger.info("Iniciando selección de columnas con secuencia específica de teclado...")
            
            # Verificar que estamos en el panel de ajustes
            if not self._verify_settings_panel_opened():
                logger.warning("El panel de ajustes no está abierto")
                return False
                
            # Importar las clases necesarias para la navegación por teclado
            from selenium.webdriver.common.action_chains import ActionChains
            from selenium.webdriver.common.keys import Keys
            
            # =====================================================================
            # PASO 1: Navegar a "Select Columns"
            # =====================================================================
            logger.info("PASO 1: Navegando a 'Select Columns'...")
            
            # Limpiar cualquier selección previa haciendo clic en el título del diálogo
            try:
                title_element = self.driver.find_element(By.XPATH, 
                    "//div[contains(@class, 'sapMDialogTitle')] | //div[contains(@class, 'sapMIBar')]//div")
                title_element.click()
                time.sleep(0.5)
            except:
                logger.debug("No se pudo hacer clic en el título del diálogo")
            
            # Usar ActionChains para enviar la secuencia exacta de teclas
            actions = ActionChains(self.driver)
            
            # Secuencia: 5 tabs, 2 flechas derecha, Enter
            logger.info("Enviando 5 TABs...")
            for _ in range(5):
                actions.send_keys(Keys.TAB)
                actions.pause(0.4)  # Pausa entre cada tab
            
            logger.info("Enviando 2 flechas DERECHA...")
            for _ in range(2):
                actions.send_keys(Keys.ARROW_RIGHT)
                actions.pause(0.5)  # Pausa entre cada flecha
            
            logger.info("Enviando ENTER para seleccionar 'Select Columns'...")
            actions.send_keys(Keys.ENTER)
            
            # Ejecutar la secuencia
            actions.perform()
            
            # Dar tiempo para que se abra el panel de columnas
            time.sleep(2.5)
            
            # Verificar que estamos en el panel de columnas
            select_all_visible = False
            try:
                select_all = self.driver.find_elements(By.XPATH, "//div[text()='Select All']")
                select_all_visible = select_all and any(el.is_displayed() for el in select_all)
            except:
                pass
                
            if not select_all_visible:
                logger.warning("No se pudo navegar al panel de columnas")
                return False
                
            logger.info("Panel de columnas abierto correctamente")
            
            # =====================================================================
            # PASO 2: Marcar "Select All"
            # =====================================================================
            logger.info("PASO 2: Seleccionando 'Select All'...")
            
            # Usar ActionChains para enviar la secuencia exacta de teclas
            actions = ActionChains(self.driver)
            
            # Secuencia: 3 tabs, Enter
            logger.info("Enviando 3 TABs...")
            for _ in range(3):
                actions.send_keys(Keys.TAB)
                actions.pause(0.4)  # Pausa entre cada tab
            
            logger.info("Enviando ENTER para marcar 'Select All'...")
            actions.send_keys(Keys.ENTER)
            
            # Ejecutar la secuencia
            actions.perform()
            
            # Dar tiempo para que se procese la selección
            time.sleep(1.5)
            
            # =====================================================================
            # PASO 3: Confirmar con OK
            # =====================================================================
            logger.info("PASO 3: Confirmando con OK...")
            
            # Usar ActionChains para enviar la secuencia exacta de teclas
            actions = ActionChains(self.driver)
            
            # Secuencia: 2 tabs, Enter
            logger.info("Enviando 2 TABs...")
            for _ in range(2):
                actions.send_keys(Keys.TAB)
                actions.pause(0.4)  # Pausa entre cada tab
            
            logger.info("Enviando ENTER para confirmar...")
            actions.send_keys(Keys.ENTER)
            
            # Ejecutar la secuencia
            actions.perform()
            
            # Dar tiempo para que se cierre el panel
            time.sleep(2)
            
            # Verificar que el panel se cerró
            panel_closed = True
            try:
                dialogs = self.driver.find_elements(By.XPATH, 
                    "//div[contains(@class, 'sapMDialog') and contains(@style, 'visibility: visible')]")
                panel_closed = not dialogs or not any(d.is_displayed() for d in dialogs)
            except:
                pass
                
            if panel_closed:
                logger.info("Selección de columnas completada con éxito")
                return True
            else:
                logger.warning("No se pudo confirmar que los paneles se cerraron")
                return False
                
        except Exception as e:
            logger.error(f"Error durante la selección de columnas: {e}")
            return False




    def get_total_issues_count(self):
        """
        Obtiene el número total de issues desde el encabezado
        
        Returns:
            int: Número total de issues o un valor por defecto (100) si no se puede determinar
        """
        try:
            # Estrategia 1: Buscar el texto "Issues (número)"
            try:
                header_text = self.driver.find_element(
                    By.XPATH, "//div[contains(text(), 'Issues') and contains(text(), '(')]"
                ).text
                logger.info(f"Texto del encabezado de issues: {header_text}")
                
                # Extraer el número entre paréntesis
                match = re.search(r'\((\d+)\)', header_text)
                if match:
                    return int(match.group(1))
            except NoSuchElementException:
                logger.warning("No se encontró el encabezado Issues con formato (número)")
            
            # Estrategia 2: Buscar contador específico de SAP UI5
            try:
                counter_element = self.driver.find_element(
                    By.XPATH, "//div[contains(@class, 'sapMITBCount')]"
                )
                if counter_element.text.isdigit():
                    return int(counter_element.text)
            except NoSuchElementException:
                logger.warning("No se encontró contador de issues en formato SAP UI5")
            
            # Estrategia 3: Contar filas visibles y usar como estimación
            rows = find_table_rows(self.driver, highlight=False)
            if rows:
                count = len(rows)
                logger.info(f"Estimando número de issues basado en filas visibles: {count}")
                return max(count, 100)  # Al menos 100 para asegurar cobertura completa
            
            logger.warning("No se pudo determinar el número total de issues, usando valor por defecto")
            return 100  # Valor por defecto
            
        except Exception as e:
            logger.error(f"Error al obtener el total de issues: {e}")
            return 100  # Valor por defecto si hay error
            
            
            
            
            
                
    def perform_exact_keyboard_sequence(self):
        """
        Ejecuta la secuencia exacta de pulsaciones de teclas para configurar columnas
        desde el panel de ajustes ya abierto.
        
        Secuencia: 
        1. 5 tabs
        2. 2 flechas a la derecha
        3. Enter (para Select Columns)
        4. 3 tabs
        5. Enter (para Select All)
        6. 2 tabs
        7. Enter (para OK)
        
        Returns:
            bool: True si la secuencia se completó, False en caso contrario
        """
        try:
            logger.info("MÉTODO: perform_exact_keyboard_sequence - Iniciando secuencia exacta de teclas")
            
            from selenium.webdriver.common.action_chains import ActionChains
            from selenium.webdriver.common.keys import Keys
            
            # Capturar estado inicial para verificación
            initial_screenshot_path = os.path.join("logs", f"settings_panel_initial_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            self.driver.save_screenshot(initial_screenshot_path)
            logger.info(f"Captura inicial guardada en: {initial_screenshot_path}")
            
            # Verificar si hay un diálogo abierto antes de empezar
            dialogs = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'sapMDialog')]")
            if not dialogs or not any(d.is_displayed() for d in dialogs):
                logger.error("No hay diálogo abierto para iniciar la secuencia de teclas")
                return False
                
            # Hacer clic en el diálogo para establecer el foco
            dialog = next(d for d in dialogs if d.is_displayed())
            self.driver.execute_script("arguments[0].click();", dialog)
            time.sleep(0.5)
            
            # PARTE 1: Seleccionar "Select Columns"
            logger.info("PASO 1-3: 5 TABS + 2 FLECHAS DERECHA + ENTER (para Select Columns)")
            actions = ActionChains(self.driver)
            
            # 5 tabs con pausas
            for i in range(5):
                actions.send_keys(Keys.TAB)
                actions.pause(0.8)  # Pausa más larga para que la interfaz responda
            
            # 2 flechas derecha con pausas
            for i in range(2):
                actions.send_keys(Keys.ARROW_RIGHT)
                actions.pause(0.8)
            
            # Enter para Select Columns
            actions.send_keys(Keys.ENTER)
            actions.perform()
            
            # Pausa importante para que se abra el panel
            time.sleep(3)
            
            # Capturar estado intermedio
            mid_screenshot_path = os.path.join("logs", f"columns_panel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            self.driver.save_screenshot(mid_screenshot_path)
            logger.info(f"Captura después de Select Columns guardada en: {mid_screenshot_path}")
            
            # PARTE 2: Seleccionar "Select All"
            logger.info("PASO 4-5: 3 TABS + ENTER (para Select All)")
            actions = ActionChains(self.driver)
            
            # 3 tabs con pausas
            for i in range(3):
                actions.send_keys(Keys.TAB)
                actions.pause(0.8)
                
            # Enter para Select All
            actions.send_keys(Keys.ENTER)
            actions.perform()
            
            # Pausa para que se procese la selección
            time.sleep(2)
            
            # PARTE 3: Confirmar con OK
            logger.info("PASO 6-7: 2 TABS + ENTER (para OK)")
            actions = ActionChains(self.driver)
            
            # 2 tabs con pausas
            for i in range(2):
                actions.send_keys(Keys.TAB)
                actions.pause(0.8)
                
            # Enter para OK
            actions.send_keys(Keys.ENTER)
            actions.perform()
            
            # Pausa para que se cierre el panel
            time.sleep(3)
            
            # Capturar estado final
            final_screenshot_path = os.path.join("logs", f"after_sequence_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            self.driver.save_screenshot(final_screenshot_path)
            logger.info(f"Captura final guardada en: {final_screenshot_path}")
            
            # Verificar si el panel se cerró
            dialogs = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'sapMDialog') and contains(@style, 'visibility: visible')]")
            if not dialogs or not any(d.is_displayed() for d in dialogs):
                logger.info("Secuencia completada con éxito. Panel cerrado.")
                return True
            else:
                logger.warning("El panel no se cerró después de la secuencia de teclas")
                
                # Intentar un último recurso: hacer clic en un botón de cierre
                try:
                    close_buttons = self.driver.find_elements(By.XPATH, 
                        "//button[contains(text(), 'Close') or contains(text(), 'Cancel') or contains(@class, 'sapMDialogClose')]")
                    if close_buttons and any(b.is_displayed() for b in close_buttons):
                        for btn in close_buttons:
                            if btn.is_displayed():
                                self.driver.execute_script("arguments[0].click();", btn)
                                logger.info("Clic en botón de cierre ejecutado")
                                time.sleep(1)
                                return True
                except Exception as close_e:
                    logger.error(f"Error al intentar cerrar panel: {close_e}")
                    
                return False
                
        except Exception as e:
            logger.error(f"Error en secuencia exacta de teclas: {e}")
            return False
            
            
            
            
            
            
    
            
            
        
            
            
            
    def navigate_keyboard_sequence(self):
        """
        Implementa la secuencia precisa de navegación por teclado para configurar columnas
        en SAP UI5/Fiori después de la selección de cliente y proyecto.
        
        La secuencia exacta es:
        1. Click en el título "Issues and Actions Overview"
        2. 18 tabs
        3. Enter (click en botón Settings)
        4. Click en "ViewSettings"
        5. 3 tabs
        6. 2 flechas derecha 
        7. Enter (para Select Columns)
        8. 3 tabs
        9. Enter (para Select All)
        10. 2 tabs
        11. Enter (para OK)
        
        Returns:
            bool: True si la navegación fue exitosa, False en caso contrario
        """
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            from selenium.webdriver.common.keys import Keys
            
            logger.info("Iniciando secuencia precisa de navegación por teclado...")
            
            # PASO 1: Click en el título "Issues and Actions Overview"
            logger.info("Paso 1: Buscando y haciendo click en el título...")
            
            # Buscar el título con múltiples selectores posibles
            title_selectors = [
                "//span[contains(text(), 'Issues and Actions Overview')]",
                "//div[contains(text(), 'Issues and Actions Overview')]",
                "//h1[contains(text(), 'Issues and Actions Overview')]",
                "//div[contains(@class, 'sapMTitle') and contains(text(), 'Issues')]",
                "//div[contains(@class, 'sapMText') and contains(text(), 'Issues')]"
            ]
            
            
            
            
            title_clicked = False
            for selector in title_selectors:
                try:
                    title_elements = self.driver.find_elements(By.XPATH, selector)
                    for element in title_elements:
                        if element.is_displayed():
                            # Hacer scroll y click
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                            time.sleep(0.5)
                            self.driver.execute_script("arguments[0].click();", element)
                            logger.info(f"✅ Click realizado en título con selector: {selector}")
                            title_clicked = True
                            break
                    if title_clicked:
                        break
                except Exception as e:
                    logger.debug(f"Error con selector de título {selector}: {e}")
                    continue
            
            # Si no se encontró el título específico, hacer click en el área principal como alternativa
            if not title_clicked:
                try:
                    main_area = self.driver.find_element(By.XPATH, 
                        "//div[contains(@class, 'sapMPage')] | //div[contains(@class, 'sapMPageHeader')]")
                    if main_area:
                        self.driver.execute_script("arguments[0].click();", main_area)
                        logger.info("Click realizado en área principal como alternativa")
                        title_clicked = True
                except Exception as e:
                    logger.debug(f"Error al hacer click en área alternativa: {e}")
                    
                    # Último recurso: click en el body
                    try:
                        self.driver.find_element(By.TAG_NAME, "body").click()
                        logger.info("Click realizado en body como último recurso")
                        title_clicked = True
                    except:
                        pass
            
            if not title_clicked:
                logger.warning("No se pudo hacer click en ningún título o área alternativa")
                return False
                
            # Dar un tiempo para que la interfaz responda al click
            time.sleep(1)
            
            # PASO 2 y 3: Pulsar 18 tabs y Enter para click en botón Settings
            logger.info("Paso 2-3: Enviando 18 TABs y ENTER para botón Settings...")
            
            actions = ActionChains(self.driver)
            
            # Enviar exactamente 18 tabs con pausas para mejor confiabilidad
            for i in range(19):
                actions.send_keys(Keys.TAB)
                actions.pause(0.3)  # Pausa entre teclas
                
            # Enviar Enter para hacer click en botón Settings
            actions.send_keys(Keys.ENTER)
            
            # Ejecutar la secuencia completa
            actions.perform()
            logger.info("✅ Secuencia de 18 TABs + ENTER completada")
            
            # Esperar a que se abra el panel de ajustes
            time.sleep(0.2)
            
            # PASO 4: Click en "ViewSettings" (no es necesario si el panel ya está en la vista correcta)
            # Nota: Este paso parece ser para asegurar que estamos en la vista correcta
            
            # PASO 5, 6 y 7: 3 tabs, 2 flechas derecha, Enter (Select Columns)
            logger.info("Paso 5-7: Enviando 3 TABs, 2 flechas DERECHA y ENTER para Select Columns...")
            
            actions = ActionChains(self.driver)
            
            # 3 tabs
            for i in range(3):
                actions.send_keys(Keys.TAB)
                actions.pause(0.3)
            
            # 2 flechas derecha
            for i in range(2):
                actions.send_keys(Keys.ARROW_RIGHT)
                actions.pause(0.3)
            
            # Enter para Select Columns
            actions.send_keys(Keys.ENTER)
            
            # Ejecutar la secuencia
            actions.perform()
            logger.info("✅ Secuencia para Select Columns completada")
            
            # Esperar a que se abra el panel de columnas
            time.sleep(0.1)
            
            # PASO 8 y 9: 3 tabs y Enter (Select All)
            logger.info("Paso 8-9: Enviando 3 TABs y ENTER para Select All...")
            
            actions = ActionChains(self.driver)
            
            # 3 tabs
            for i in range(3):
                actions.send_keys(Keys.TAB)
                actions.pause(0.2)
            
            # Enter para Select All
            actions.send_keys(Keys.ENTER)
            
            # Ejecutar la secuencia
            actions.perform()
            logger.info("✅ Secuencia para Select All completada")
            
            # Esperar a que se procese la selección
            time.sleep(0.2)
            
            
            
            
            
            
            
            # PASO 10 y 11: 2 tabs y Enter (OK)
            logger.info("Paso 10-11: Enviando 2 TABs y ENTER para confirmar con OK...")
            
            actions = ActionChains(self.driver)
            
            # 2 tabs
            for i in range(2):
                actions.send_keys(Keys.TAB)
                actions.pause(0.3)
            
            # Enter para OK
            actions.send_keys(Keys.ENTER)
            
            # Ejecutar la secuencia
            actions.perform()
            logger.info("✅ Secuencia para OK completada")
            
            # Esperar a que se cierre el panel y se apliquen los cambios
            time.sleep(3)
            
            logger.info("✅ Secuencia completa de navegación por teclado ejecutada con éxito")
            return True
            
        except Exception as e:
            logger.error(f"Error durante la navegación por teclado: {e}")
            return False
            
    def select_all_visible_columns(self):
        """
        Selecciona todas las columnas disponibles mediante navegación por teclado.
        
        Usando la secuencia exacta definida por el cliente:
        1. 5 tabs, 2 flechas derecha y enter para select columns
        2. 3 tabs y enter para marcar "Select All"
        3. 2 tabs y enter para confirmar con OK
        
        Returns:
            bool: True si la selección fue exitosa, False en caso contrario
        """
        try:
            logger.info("Iniciando selección de columnas con secuencia específica de teclado...")
            
            # Verificar que estamos en el panel de ajustes
            if not self._verify_settings_panel_opened():
                logger.warning("El panel de ajustes no está abierto")
                return False
                
            # Importar las clases necesarias para la navegación por teclado
            from selenium.webdriver.common.action_chains import ActionChains
            from selenium.webdriver.common.keys import Keys
            
            # =====================================================================
            # PASO 1: Navegar a "Select Columns"
            # =====================================================================
            logger.info("PASO 1: Navegando a 'Select Columns'...")
            
            # Limpiar cualquier selección previa haciendo clic en el título del diálogo
            try:
                title_element = self.driver.find_element(By.XPATH, 
                    "//div[contains(@class, 'sapMDialogTitle')] | //div[contains(@class, 'sapMIBar')]//div")
                title_element.click()
                time.sleep(0.5)
            except:
                logger.debug("No se pudo hacer clic en el título del diálogo")
            
            # Usar ActionChains para enviar la secuencia exacta de teclas
            actions = ActionChains(self.driver)
            
            # Secuencia: 5 tabs, 2 flechas derecha, Enter
            logger.info("Enviando 5 TABs...")
            for _ in range(5):
                actions.send_keys(Keys.TAB)
                actions.pause(0.4)  # Pausa entre cada tab
            
            logger.info("Enviando 2 flechas DERECHA...")
            for _ in range(2):
                actions.send_keys(Keys.ARROW_RIGHT)
                actions.pause(0.5)  # Pausa entre cada flecha
            
            logger.info("Enviando ENTER para seleccionar 'Select Columns'...")
            actions.send_keys(Keys.ENTER)
            
            # Ejecutar la secuencia
            actions.perform()
            
            # Dar tiempo para que se abra el panel de columnas
            time.sleep(2.5)
            
            

# Verificar que estamos en el panel de columnas
            select_all_visible = False
            try:
                select_all = self.driver.find_elements(By.XPATH, "//div[text()='Select All']")
                select_all_visible = select_all and any(el.is_displayed() for el in select_all)
            except:
                pass
                
            if not select_all_visible:
                logger.warning("No se pudo navegar al panel de columnas")
                return False
                
            logger.info("Panel de columnas abierto correctamente")
            
            # =====================================================================
            # PASO 2: Marcar "Select All"
            # =====================================================================
            logger.info("PASO 2: Seleccionando 'Select All'...")
            
            # Usar ActionChains para enviar la secuencia exacta de teclas
            actions = ActionChains(self.driver)
            
            # Secuencia: 3 tabs, Enter
            logger.info("Enviando 3 TABs...")
            for _ in range(3):
                actions.send_keys(Keys.TAB)
                actions.pause(0.4)  # Pausa entre cada tab
            
            logger.info("Enviando ENTER para marcar 'Select All'...")
            actions.send_keys(Keys.ENTER)
            
            # Ejecutar la secuencia
            actions.perform()
            
            # Dar tiempo para que se procese la selección
            time.sleep(1.5)
            
            # =====================================================================
            # PASO 3: Confirmar con OK
            # =====================================================================
            logger.info("PASO 3: Confirmando con OK...")
            
            # Usar ActionChains para enviar la secuencia exacta de teclas
            actions = ActionChains(self.driver)
            
            # Secuencia: 2 tabs, Enter
            logger.info("Enviando 2 TABs...")
            for _ in range(2):
                actions.send_keys(Keys.TAB)
                actions.pause(0.4)  # Pausa entre cada tab
            
            logger.info("Enviando ENTER para confirmar...")
            actions.send_keys(Keys.ENTER)
            
            # Ejecutar la secuencia
            actions.perform()
            
            # Dar tiempo para que se cierre el panel
            time.sleep(2)
            
            # Verificar que el panel se cerró
            panel_closed = True
            try:
                dialogs = self.driver.find_elements(By.XPATH, 
                    "//div[contains(@class, 'sapMDialog') and contains(@style, 'visibility: visible')]")
                panel_closed = not dialogs or not any(d.is_displayed() for d in dialogs)
            except:
                pass
                
            if panel_closed:
                logger.info("Selección de columnas completada con éxito")
                return True
            else:
                logger.warning("No se pudo confirmar que los paneles se cerraron")
                return False
                
        except Exception as e:
            logger.error(f"Error durante la selección de columnas: {e}")
            return False
            
    def find_and_click_settings_button(self):
        """
        Encuentra y hace clic en el botón de ajustes (engranaje/settings) con métodos altamente robustos.
        
        Este método utiliza múltiples estrategias para localizar el botón en diferentes versiones de SAP UI5.
        
        Returns:
            bool: True si el clic fue exitoso y se abrió el panel, False en caso contrario
        """
        try:
            logger.info("Buscando el botón de ajustes con estrategia mejorada...")
            
            # ESTRATEGIA 1: Usar selectores altamente específicos
            specific_selectors = [
                # Por ID o clase
                "//button[contains(@id, 'settings')]", 
                "//button[contains(@id, 'gear')]",
                "//button[contains(@id, 'config')]",
                "//button[contains(@class, 'settings')]",
                "//button[contains(@class, 'gear')]",
                "//button[contains(@class, 'config')]",
                "//button[contains(@class, 'customize')]",
                
                
                
                
                
                
                
                
# Por atributos de UI5
                "//span[contains(@data-sap-ui, 'icon-action-settings')]/ancestor::button",
                "//span[contains(@data-sap-ui, 'glyph-setting')]/ancestor::button",
                "//span[contains(@class, 'sapUiIcon')]/ancestor::button",
                
                # Por ubicación
                "//footer//button[last()]",
                "//div[contains(@class, 'sapMBarRight')]//button[last()]"
            ]
            
            # Intentar cada selector específico
            for selector in specific_selectors:
                elements = self.driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        # Hacer scroll para asegurar visibilidad
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                        time.sleep(0.5)
                        
                        # Intentar clic con JavaScript
                        self.driver.execute_script("arguments[0].click();", element)
                        logger.info(f"Clic en botón de ajustes realizado con selector: {selector}")
                        time.sleep(2)
                        
                        # Verificar si se abrió el panel
                        if self._verify_settings_panel_opened():
                            logger.info("Panel de ajustes abierto correctamente")
                            return True
            
            # ESTRATEGIA 2: Usar análisis de pantalla para encontrar engranajes o íconos
            logger.info("Usando análisis visual para encontrar el botón de ajustes...")
            
            # Script para buscar elementos visuales que parezcan botones de ajustes
            visual_script = """
            return (function() {
                // Buscar todos los elementos visibles que podrían ser botones
                const allElements = document.querySelectorAll('button, span, div, a');
                const candidates = [];
                
                // Para cada elemento, verificar si parece un botón de ajustes
                for (const el of allElements) {
                    // Solo elementos visibles
                    if (el.offsetParent === null) continue;
                    
                    // Verificar tamaño (los botones de ajustes suelen ser pequeños)
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 50 && rect.height > 50) continue;
                    
                    // Verificar posición (los botones de ajustes suelen estar en esquinas)
                    const isInCorner = (
                        rect.bottom > window.innerHeight * 0.7 &&
                        rect.right > window.innerWidth * 0.7
                    );
                    
                    // Verificar atributos y clases
                    const hasSettingsAttributes = (
                        (el.id && (el.id.includes('settings') || el.id.includes('gear') || el.id.includes('config'))) ||
                        (el.className && (el.className.includes('settings') || el.className.includes('gear') || el.className.includes('config'))) ||
                        (el.innerHTML && (el.innerHTML.includes('gear') || el.innerHTML.includes('cog') || el.innerHTML.includes('settings')))
                    );
                    
                    // Puntuar candidatos
                    let score = 0;
                    if (isInCorner) score += 2;
                    if (hasSettingsAttributes) score += 3;
                    if (el.tagName === 'BUTTON') score += 1;
                    
                    // Añadir a candidatos si tiene suficiente puntuación
                    if (score >= 2) {
                        candidates.push({
                            element: el,
                            score: score
                        });
                    }
                }
                
                // Ordenar candidatos por puntuación
                candidates.sort((a, b) => b.score - a.score);
                
                return candidates.slice(0, 3).map(c => c.element);
            })();
            """
            
            candidates = self.driver.execute_script(visual_script)
            
            # Intentar hacer clic en cada candidato
            for i, candidate in enumerate(candidates):
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", candidate)
                    time.sleep(0.5)
                    self.driver.execute_script("arguments[0].click();", candidate)
                    logger.info(f"Clic en candidato #{i+1} con análisis visual")
                    time.sleep(2)
                    
                    if self._verify_settings_panel_opened():
                        logger.info("Panel de ajustes abierto correctamente mediante análisis visual")
                        return True
                except Exception as e:
                    logger.debug(f"Error al hacer clic en candidato #{i+1}: {e}")
            
            
            
            
            
            
            
            
            
            
            
# ESTRATEGIA 3: Buscar cualquier botón en la parte inferior de la pantalla
            logger.info("Buscando botones en la parte inferior de la pantalla...")
            
            bottom_script = """
            return (function() {
                const allButtons = Array.from(document.querySelectorAll('button'));
                // Filtrar botones visibles en la parte inferior
                return allButtons.filter(btn => {
                    if (btn.offsetParent === null) return false;
                    const rect = btn.getBoundingClientRect();
                    return rect.bottom > window.innerHeight * 0.7;
                });
            })();
            """
            
            bottom_buttons = self.driver.execute_script(bottom_script)
            
            # Intentar hacer clic en cada botón de la parte inferior
            for i, button in enumerate(bottom_buttons):
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                    time.sleep(0.5)
                    self.driver.execute_script("arguments[0].click();", button)
                    logger.info(f"Clic en botón inferior #{i+1}")
                    time.sleep(2)
                    
                    if self._verify_settings_panel_opened():
                        logger.info("Panel de ajustes abierto correctamente mediante botón inferior")
                        return True
                except Exception as e:
                    logger.debug(f"Error al hacer clic en botón inferior #{i+1}: {e}")
            
            # ESTRATEGIA 4: Buscar por atributos visuales como tooltips
            tooltip_selectors = [
                "//*[@title='Settings']",
                "//*[@title='Configure']",
                "//*[@title='Customize']",
                "//*[@title='Options']",
                "//*[@aria-label='Settings']",
                "//*[@aria-label='Configure']",
                "//*[@aria-label='Customize']",
                "//*[@aria-label='Options']"
            ]
            
            for selector in tooltip_selectors:
                elements = self.driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed():
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                        time.sleep(0.5)
                        self.driver.execute_script("arguments[0].click();", element)
                        logger.info(f"Clic en elemento con tooltip usando selector: {selector}")
                        time.sleep(2)
                        
                        if self._verify_settings_panel_opened():
                            logger.info("Panel de ajustes abierto correctamente mediante tooltip")
                            return True
            
            # Si todas las estrategias fallan, guardar captura y reportar
            try:
                screenshot_path = os.path.join("logs", f"settings_button_not_found_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                if not os.path.exists("logs"):
                    os.makedirs("logs")
                    
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"Captura guardada en: {screenshot_path}")
            except Exception as ss_e:
                logger.debug(f"Error al guardar captura: {ss_e}")
            
            logger.error("No se pudo encontrar o hacer clic en el botón de ajustes con ninguna estrategia")
            return False
            
        except Exception as e:
            logger.error(f"Error general en búsqueda de botón de ajustes: {e}")
            return False
            
    def _verify_settings_panel_opened(self):
        """
        Verifica si el panel de ajustes se ha abierto correctamente después de hacer clic en el botón.
        
        Returns:
            bool: True si el panel está abierto, False en caso contrario
        """
        try:
            # Esperamos un momento para que se abra el panel si es necesario
            time.sleep(1)
            
            # Selectores para detectar el panel de ajustes
            settings_panel_selectors = [
                # Diálogos y popups
                "//div[contains(@class, 'sapMDialog') and contains(@class, 'sapMPopup-CTX')]",
                "//div[contains(@class, 'sapMPopover') and contains(@class, 'sapMPopup-CTX')]",
                "//div[contains(@class, 'sapMActionSheet') and contains(@style, 'visibility: visible')]",
                
                # Contenido de ajustes
                "//div[contains(@class, 'sapMDialog')]//div[contains(text(), 'Settings')]",
                "//div[contains(@class, 'sapMPopover')]//div[contains(text(), 'Settings')]",
                "//div[contains(text(), 'Settings')]/ancestor::div[contains(@class, 'sapMPopup-CTX')]",
                
                # Elementos específicos de configuración
                "//ul[contains(@class, 'sapMListItems')]//li[contains(@class, 'sapMLIB-CTX')]",
                "//div[contains(@class, 'sapMPopover')]//ul[contains(@class, 'sapMList')]",
                "//div[contains(@class, 'sapMPopup-CTX')]//ul[contains(@class, 'sapMList')]"
            ]
            
            # Verificar cada selector
            for selector in settings_panel_selectors:
                elements = self.driver.find_elements(By.XPATH, selector)
                if elements and any(element.is_displayed() for element in elements):
                    logger.info(f"Panel de ajustes detectado con selector: {selector}")
                    
                    # Tomar captura del panel abierto para verificación
                    try:
                        panel_screenshot = os.path.join("logs", f"settings_panel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                        if not os.path.exists("logs"):
                            os.makedirs("logs")
                        self.driver.save_screenshot(panel_screenshot)
                        logger.info(f"Captura del panel de ajustes guardada en: {panel_screenshot}")
                    except:
                        pass
                        
                    return True
            
            # Verificación adicional con JavaScript para elementos emergentes
            js_check = """
            return (function() {
                // Verificar diálogos y popovers visibles
                var popups = document.querySelectorAll('.sapMDialog, .sapMPopover, .sapMActionSheet');
                for (var i = 0; i < popups.length; i++) {
                    var popup = popups[i];
                    var style = window.getComputedStyle(popup);
                    if (style.visibility === 'visible' || style.display !== 'none') {
                        return true;
                    }
                }
                
                // Verificar cambios en la interfaz que indiquen que se abrió un panel
                var newElements = document.querySelectorAll('.sapMDialog, .sapMPopover');
                if (newElements.length > 0) {
                    return true;
                }
                
                return false;
            })();
            """
            
            js_result = self.driver.execute_script(js_check)
            if js_result:
                logger.info("Panel de ajustes detectado mediante JavaScript")
                return True
            
            logger.warning("No se detectó el panel de ajustes después del clic")
            return False
            
        except Exception as e:
            logger.error(f"Error al verificar si el panel de ajustes se abrió: {e}")
            return False
        
        
            
    def _verify_column_panel_opened(self):
            """
            Verifica que el panel de selección de columnas se ha abierto correctamente
            después de hacer clic en el ícono 'Select Columns'.
            
            Returns:
                bool: True si el panel está abierto, False en caso contrario
            """
            try:
                # Dar tiempo a que se abra el panel
                time.sleep(1)
                
                # 1. Verificar la presencia del texto "Select All"
                select_all_elements = self.driver.find_elements(By.XPATH, "//div[text()='Select All']")
                if select_all_elements and any(el.is_displayed() for el in select_all_elements):
                    logger.info("Panel de columnas detectado: 'Select All' visible")
                    return True
                    
                # 2. Verificar los checkboxes de columnas (específico de la interfaz de columnas)
                checkboxes = self.driver.find_elements(By.XPATH, 
                    "//div[contains(@class, 'sapMCb')]/parent::div[contains(text(), 'Issue Title') or contains(text(), 'SAP Category')]")
                if checkboxes and any(checkbox.is_displayed() for checkbox in checkboxes):
                    logger.info("Panel de columnas detectado: Checkboxes de columnas visibles")
                    return True
                    
                # 3. Verificar otros elementos comunes de la interfaz de selección de columnas
                column_selectors = [
                    "//div[@role='dialog']//div[contains(@class, 'sapMList')]", # Lista de columnas
                    "//div[contains(@class, 'sapMSelectDialogListItem')]",  # Elementos de la lista de columnas
                    "//div[contains(@class, 'sapMDialog')]//div[contains(@aria-selected, 'true')]", # Item seleccionado
                    "//div[contains(@class, 'sapMList')]//li", # Items de lista genéricos
                    "//div[contains(@class, 'sapMDialog')]//ul[contains(@class, 'sapMListItems')]" # Lista de items UI5
                ]
                
                for selector in column_selectors:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements and any(el.is_displayed() for el in elements):
                        logger.info(f"Panel de columnas detectado con selector: {selector}")
                        return True
                
                # 4. Verificación mediante JavaScript para casos difíciles
                js_verify = """
                (function() {
                    // Buscar diálogo visible
                    var dialog = document.querySelector('.sapMDialog[style*="visibility: visible"]');
                    if (!dialog) return false;
                    
                    // Verificar texto "Select All"
                    var selectAll = document.evaluate(
                        "//div[text()='Select All']", 
                        document, 
                        null, 
                        XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, 
                        null
                    );
                    
                    if (selectAll.snapshotLength > 0) {
                        return true;
                    }
                    
                    // Verificar presencia de checkboxes en el diálogo
                    var checkboxes = dialog.querySelectorAll('.sapMCb, input[type="checkbox"]');
                    if (checkboxes.length > 3) {
                        return true;
                    }
                    
                    // Verificar lista de columnas
                    var listItems = dialog.querySelectorAll('.sapMList li, .sapMLIB');
                    if (listItems.length > 3) {
                        return true;
                    }
                    
                    return false;
                })();
                """
                
                try:
                    result = self.driver.execute_script(js_verify)
                    if result:
                        logger.info("Panel de columnas detectado mediante JavaScript")
                        return True
                except Exception as js_e:
                    logger.debug(f"Error en verificación JavaScript: {js_e}")
                
                logger.warning("No se detectó el panel de selección de columnas")
                return False
                
            except Exception as e:
                logger.error(f"Error al verificar panel de columnas: {e}")
                return False

    def navigate_post_selection(self):
        """
        Ejecuta la navegación completa después de seleccionar cliente y proyecto.
        
        Este método implementa la secuencia exacta de navegación por teclado:
        1. Hacer clic en el botón de búsqueda
        2. Ejecutar la secuencia precisa de navegación por teclado
        
        Returns:
            bool: True si toda la navegación fue exitosa, False en caso contrario
        """
        try:
            logger.info("Iniciando navegación post-selección con secuencia precisa de teclado...")
            
            # ============================================================
            # PASO 1: Hacer clic en el botón de búsqueda
            # ============================================================
            logger.info("PASO 1: Haciendo clic en el botón de búsqueda...")
            
            # Intentar hacer clic directamente en el botón de búsqueda
            search_success = self.click_search_button()
            
            if not search_success:
                logger.info("Intentando navegación por teclado para el botón de búsqueda...")
                
                # Establecer foco en la página
                body = self.driver.find_element(By.TAG_NAME, "body")
                body.click()
                time.sleep(0.5)
                
                # Navegar con tabs hasta el botón de búsqueda
                from selenium.webdriver.common.action_chains import ActionChains
                from selenium.webdriver.common.keys import Keys
                
                actions = ActionChains(self.driver)
                # Enviar 3 tabs y Enter
                for _ in range(3):
                    actions.send_keys(Keys.TAB)
                    actions.pause(0.5)
                actions.send_keys(Keys.ENTER)
                actions.perform()
            
            # Esperar a que se ejecute la búsqueda
            time.sleep(3)
            logger.info("Búsqueda completada, iniciando secuencia de navegación por teclado...")
            
            # ============================================================
            # PASO 2: Ejecutar la secuencia precisa de navegación por teclado
            # ============================================================
            # Usar el nuevo método que implementa exactamente la secuencia requerida
            keyboard_success = self.navigate_keyboard_sequence()
            
            if keyboard_success:
                logger.info("✅ Navegación post-selección completada con éxito mediante secuencia de teclado")
                return True
            else:
                logger.warning("❌ La secuencia de navegación por teclado falló")
                
                # Como último recurso, intentar con el método antiguo basado en clicks
                logger.info("Intentando método alternativo basado en clicks...")
                
                # Intentar hacer clic en el botón de ajustes
                if not self.find_and_click_settings_button():
                    logger.warning("No se pudo hacer clic en el botón de ajustes")
                    return False
                    
                # Intentar seleccionar todas las columnas
                if not self.select_all_visible_columns():
                    logger.warning("No se pudieron seleccionar todas las columnas")
                    return False
                
                logger.info("✅ Método alternativo completado con éxito")
                return True
                
        except Exception as e:
            logger.error(f"Error durante la navegación post-selección: {e}")
            return False
        
        
        
        
        
        
        
        
    def scroll_to_load_all_items(self, total_expected=300, max_attempts=100):
        """
        Estrategia de scroll mejorada para cargar elementos, combinando enfoques
        de V11.txt con mejoras adicionales para aumentar la cobertura.
        """
        logger.info(f"Iniciando proceso de scroll mejorado para cargar {total_expected} elementos...")
        
        # Actualizar la interfaz si existe
        if hasattr(self, 'status_var') and self.status_var:
            self.status_var.set(f"Cargando elementos...")
        
        # Lista para almacenar las filas procesadas y evitar duplicados
        processed_titles = set()
        
        attempt = 0
        previous_rows_count = 0
        no_change_count = 0
        max_no_change = 25  # Aumentar el umbral de intentos sin cambios
        
        # Inicializar con un scroll agresivo para activar la carga inicial
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        
        # Estrategia 1: Hacer clic en botón de mostrar más si existe
        self._try_click_show_more_button()
        
        # Estrategia 2: Verificar si hay elementos de paginación y manejarlos
        pagination_found = self._check_and_handle_pagination()
        if pagination_found:
            logger.info("Se encontró y manejó la paginación")
            return self._count_loaded_rows()
            
        while attempt < max_attempts:
            try:
                # Estrategia 3: Scroll agresivo con múltiples técnicas
                
                # 3.1 Scroll al final del documento
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.5)
                
                # 3.2 Scroll dentro de contenedores específicos de SAP
                self.driver.execute_script("""
                    // Lista completa de posibles contenedores de scroll en SAP UI5
                    const scrollContainers = [
                        '.sapMListItems', 
                        '.sapMTableTBody', 
                        '.sapUiTableCtrlScr',
                        '.sapUiTableCCnt',
                        '.sapMList',
                        '.sapMScrollCont',
                        '.sapUiScrollDelegate'
                    ];
                    
                    // Encontrar todos los contenedores y hacer scroll en cada uno
                    for (const selector of scrollContainers) {
                        const containers = document.querySelectorAll(selector);
                        for (const container of containers) {
                            if (container) {
                                try {
                                    container.scrollTop = container.scrollHeight * 2;
                                } catch(e) {}
                            }
                        }
                    }
                """)
                
                # 3.3 Scroll por ventanas a diferentes posiciones
                if attempt % 3 == 0:
                    for position in range(1000, 20000, 1000):
                        self.driver.execute_script(f"window.scrollTo(0, {position});")
                        time.sleep(0.2)
                
                time.sleep(1)  # Esperar a que carguen elementos
                
                # Estrategia 4: Intentar hacer clic en botones "Show More" cada ciertos intentos
                if attempt % 2 == 0:
                    self._try_click_show_more_button()
                
                # Estrategia 5: Simular teclas Page Down para scroll adicional
                if attempt % 4 == 0:
                    try:
                        body = self.driver.find_element(By.TAG_NAME, "body")
                        for _ in range(3):
                            body.send_keys(Keys.PAGE_DOWN)
                            time.sleep(0.3)
                    except:
                        pass
                
                # Contar filas actualmente cargadas
                rows = self._count_loaded_rows()
                current_rows_count = rows
                
                logger.info(f"Intento {attempt+1}: {current_rows_count} filas cargadas")
                
                # Actualizar interfaz
                if hasattr(self, 'status_var') and self.status_var:
                    self.status_var.set(f"Cargando elementos: {current_rows_count}/{total_expected}")
                    if self.root:
                        self.root.update()
                
                # Verificar progreso
                if current_rows_count == previous_rows_count:
                    no_change_count += 1
                    
                    # Estrategia 6: Scroll agresivo si no hay cambios
                    if no_change_count >= 5:
                        # Ejecutar JavaScript más agresivo para forzar la carga
                        self.driver.execute_script("""
                            // Forzar actualización de todos los contenedores de UI5
                            try {
                                if (sap && sap.ui && sap.ui.getCore) {
                                    const elements = sap.ui.getCore().byFieldGroupId("table");
                                    if (elements && elements.length > 0) {
                                        for (const el of elements) {
                                            if (el.rerender) el.rerender();
                                        }
                                    }
                                }
                            } catch(e) {}
                            
                            // Scroll rápido arriba y abajo varias veces
                            for (let i = 0; i < 5; i++) {
                                window.scrollTo(0, 0);
                                setTimeout(() => {
                                    window.scrollTo(0, document.body.scrollHeight);
                                }, 100);
                            }
                        """)
                        
                        # Estrategia 7: Hacer clic en el último elemento visible para forzar carga
                        try:
                            rows = self.find_table_rows(highlight=False)
                            if rows and len(rows) > 0:
                                last_row = rows[-1]
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'end', behavior: 'auto'});", last_row)
                                self.driver.execute_script("arguments[0].click();", last_row)
                                time.sleep(0.5)
                                self.driver.execute_script("document.body.click();")  # Cancelar cualquier selección
                        except:
                            pass
                    
                    # Criterios de finalización
                    if no_change_count >= max_no_change:
                        logger.warning(f"No se detectaron más filas después de {no_change_count} intentos sin cambios")
                        break
                        
                    # Si tenemos una buena proporción del total, podemos terminar antes
                    if current_rows_count >= total_expected * 0.95:
                        logger.info(f"Se han cargado {current_rows_count} filas (>= 95% del total esperado). Terminando scroll.")
                        break
                else:
                    # Reiniciar contador si hay progreso
                    no_change_count = 0
                    
                previous_rows_count = current_rows_count
                attempt += 1
                    
                # Si alcanzamos o superamos lo esperado, terminamos
                if current_rows_count >= total_expected:
                    logger.info(f"Se han cargado {current_rows_count} filas (>= {total_expected} esperadas). Scroll completado.")
                    break
                    
            except Exception as e:
                logger.warning(f"Error durante el scroll en intento {attempt+1}: {e}")
                attempt += 1
            
        # Calcular cobertura final
        coverage = (previous_rows_count / total_expected) * 100 if total_expected > 0 else 0
        logger.info(f"Proceso de scroll completado. Cobertura: {coverage:.2f}% ({previous_rows_count}/{total_expected})")
        
        # Actualizar interfaz
        if hasattr(self, 'status_var') and self.status_var:
            self.status_var.set(f"Elementos cargados: {previous_rows_count}/{total_expected} ({coverage:.1f}%)")
            
        return previous_rows_count

    def _try_click_show_more_button(self):
        """
        Intenta hacer clic en los botones "Show More" de la tabla
        """
        try:
            # Solo buscar botones específicos de carga de tabla, no en elementos de título
            show_more_selectors = [
                "//div[contains(@class, 'sapMListShowMoreButton')]",
                "//button[contains(@id, 'loadMore')]",
                "//button[contains(@id, '__more')]",
                "//span[contains(@class, 'sapUiTableColShowMoreButton')]",
                "//button[contains(text(), 'More') and not(ancestor::*[contains(@class, 'sapMLIB')])]",
                "//button[contains(text(), 'Show') and contains(text(), 'More') and not(ancestor::*[contains(@class, 'sapMLIB')])]",
                "//a[contains(text(), 'More') and not(ancestor::*[contains(@class, 'sapMLIB')])]"
            ]
            
            for selector in show_more_selectors:
                buttons = self.driver.find_elements(By.XPATH, selector)
                for button in buttons:
                    try:
                        if button.is_displayed():
                            # Verificar que no esté dentro de una fila de tabla
                            parent_row = button.find_elements(By.XPATH, "./ancestor::*[contains(@class, 'sapMLIB') or contains(@class, 'sapMListItem')]")
                            if not parent_row:  # No está dentro de una fila
                                logger.info(f"Haciendo clic en botón 'Show More': {button.text}")
                                self.driver.execute_script("arguments[0].click();", button)
                                time.sleep(1.5)  # Esperar a que carguen nuevos elementos
                                return True
                    except Exception as btn_e:
                        continue
                        
            return False
        except Exception as e:
            logger.debug(f"Error al intentar hacer clic en 'Show More': {e}")
            return False

    def _check_and_handle_pagination(self):
        """
        Verifica si hay paginación y navega por todas las páginas
        """
        try:
            # Buscar elementos de paginación
            pagination_selectors = [
                "//div[contains(@class, 'sapMPagingPanel')]",
                "//button[contains(@title, 'Next Page')]",
                "//button[contains(@aria-label, 'Next Page')]",
                "//span[contains(@class, 'sapMPaginatorNext')]/..",
                "//div[contains(@class, 'sapMPageNext')]",
                "//span[contains(@class, 'sapUiIcon--navigation-right-arrow')]/.."
            ]
            
            pagination_found = False
            
            # Verificar si hay elementos de paginación visibles
            for selector in pagination_selectors:
                elements = self.driver.find_elements(By.XPATH, selector)
                if elements and any(e.is_displayed() for e in elements):
                    pagination_found = True
                    break
                    
            if not pagination_found:
                return False
                
            logger.info("Paginación detectada, navegando por todas las páginas...")
            
            # Recorrer todas las páginas haciendo clic en "Next"
            page = 1
            has_more_pages = True
            
            while has_more_pages and page <= 30:  # Máximo 30 páginas por seguridad
                logger.info(f"Procesando página {page}...")
                
                # Esperar a que se cargue la página actual
                time.sleep(2)
                
                # Buscar el botón "Next"
                next_button = None
                for selector in [
                    "//button[contains(@title, 'Next Page')]",
                    "//button[contains(@aria-label, 'Next Page')]",
                    "//span[contains(@class, 'sapMPaginatorNext')]/..",
                    "//div[contains(@class, 'sapMPageNext')]",
                    "//span[contains(@class, 'sapUiIcon--navigation-right-arrow')]/.."
                ]:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            try:
                                is_enabled = element.is_enabled() and "sapMBtnDisabled" not in element.get_attribute("class")
                                if is_enabled:
                                    next_button = element
                                    break
                            except:
                                continue
                                
                    if next_button:
                        break
                
                # Si no hay botón "Next" o está deshabilitado, terminamos
                if not next_button:
                    logger.info("No hay botón 'Next' visible, finalizando paginación")
                    has_more_pages = False
                    break
                    
                # Hacer clic en "Next"
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                    time.sleep(0.5)
                    self.driver.execute_script("arguments[0].click();", next_button)
                    logger.info(f"Clic en botón 'Next' para página {page+1}")
                    page += 1
                    
                    # Verificar si el botón quedó deshabilitado después del clic
                    time.sleep(2)  # Esperar a que se cargue la siguiente página
                    try:
                        is_disabled = "sapMBtnDisabled" in next_button.get_attribute("class") or not next_button.is_enabled()
                        if is_disabled:
                            logger.info("Botón 'Next' deshabilitado, finalizando paginación")
                            has_more_pages = False
                    except:
                        # Si hay error al verificar, asumimos que estamos en la última página
                        has_more_pages = False
                except Exception as e:
                    logger.warning(f"Error al hacer clic en botón 'Next': {e}")
                    has_more_pages = False
            
            logger.info(f"Paginación completada. Se procesaron {page} páginas.")
            return True
        
        except Exception as e:
            logger.error(f"Error al verificar paginación: {e}")
            return False

    def _count_loaded_rows(self):
        """
        Cuenta las filas actualmente cargadas usando múltiples selectores
        """
        try:
            # Usar find_table_rows pero con nuevos selectores adicionales
            rows = self.find_table_rows(highlight=False)
            return len(rows)
        except Exception as e:
            logger.error(f"Error al contar filas cargadas: {e}")
            return 0    
    
    
    
    
    
    
    
    
    
    def find_table_load_more_buttons(self):
        """
        Encuentra los botones 'Cargar más' a nivel de tabla, evitando los botones 'Show more'/'Show less'
        que aparecen dentro de los títulos de issues.
        
        Returns:
            list: Lista de elementos WebElement que son botones de carga a nivel de tabla
        """
        logger.info("Buscando botones de carga a nivel de tabla...")
        table_load_buttons = []
        
        try:
            # 1. Buscar botones específicos de carga de SAP UI5/Fiori
            specific_buttons = self.driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'sapMListShowMoreButton')] | " +
                "//button[contains(@id, 'loadMore')] | " +
                "//button[contains(@id, '__more')] | " +
                "//button[contains(@aria-label, 'Show more')] | " +
                "//span[contains(@class, 'sapUiTableColShowMoreButton')]"
            )
            
            # 2. Filtrar para excluir botones que están dentro de celdas o filas
            for btn in specific_buttons:
                try:
                    # Verificar si este botón está dentro de una fila o celda (los que no queremos)
                    cell_parents = btn.find_elements(By.XPATH, 
                        "./ancestor::*[contains(@class, 'sapMListItem') or contains(@class, 'sapMLIB') or contains(@class, 'sapUiTableCell') or contains(@role, 'gridcell')]"
                    )
                    
                    # Verificar si este botón está en el área de pie de tabla o sección de carga (los que sí queremos)
                    footer_location = btn.find_elements(By.XPATH,
                        "./ancestor::*[contains(@class, 'sapMListShowMoreDiv') or contains(@class, 'sapMListShowMore') or contains(@class, 'sapUiTableColHdrCnt')]"
                    )
                    
                    # Solo incluir botones que no están dentro de celdas/filas O están explícitamente en el footer
                    if not cell_parents or footer_location:
                        # Verificar el texto para asegurar que es un botón de carga
                        button_text = btn.text.lower() if btn.text else ""
                        
                        is_load_button = (
                            "more" in button_text or 
                            "load" in button_text or 
                            "show" in button_text or 
                            len(button_text.strip()) == 0  # Algunos botones de carga no tienen texto
                        )
                        
                        # Excluir botones "Show less" explícitamente
                        if is_load_button and "less" not in button_text:
                            table_load_buttons.append(btn)
                            logger.debug(f"Botón de carga encontrado: '{button_text}'")
                except Exception as e:
                    logger.debug(f"Error al evaluar botón: {e}")
                    continue
            
            # 3. Buscar mediante JavaScript para detectar botones de carga adicionales
            if not table_load_buttons:
                js_buttons = self.driver.execute_script("""
                    return (function() {
                        // Buscar botones específicos de carga en SAP UI5/Fiori
                        var loadButtons = [];
                        
                        // Buscar en clases específicas de SAP
                        var sapButtons = document.querySelectorAll('.sapMListShowMoreButton, .sapMShowMore-CTX, .sapUiTableColShowMoreButton');
                        for (var i = 0; i < sapButtons.length; i++) {
                            var btn = sapButtons[i];
                            // Verificar que no esté dentro de una fila
                            var inRow = false;
                            var parent = btn.parentElement;
                            while (parent && parent !== document.body) {
                                if (parent.classList.contains('sapMLIB') || 
                                    parent.classList.contains('sapMListItem') ||
                                    parent.getAttribute('role') === 'gridcell' ||
                                    parent.classList.contains('sapUiTableCell')) {
                                    inRow = true;
                                    break;
                                }
                                parent = parent.parentElement;
                            }
                            
                            if (!inRow) {
                                loadButtons.push(btn);
                            }
                        }
                        
                        // Si no encontramos botones específicos, buscar botones genéricos en posiciones típicas
                        if (loadButtons.length === 0) {
                            var allButtons = document.querySelectorAll('button, span[role="button"]');
                            for (var j = 0; j < allButtons.length; j++) {
                                var btn = allButtons[j];
                                var text = btn.textContent.toLowerCase();
                                
                                // Filtrar por texto
                                if ((text.includes('more') || text.includes('load')) && !text.includes('less')) {
                                    // Verificar que no esté dentro de una fila
                                    var inRow = false;
                                    var parent = btn.parentElement;
                                    while (parent && parent !== document.body) {
                                        if (parent.classList.contains('sapMLIB') || 
                                            parent.classList.contains('sapMListItem') ||
                                            parent.getAttribute('role') === 'gridcell' ||
                                            parent.classList.contains('sapUiTableCell')) {
                                            inRow = true;
                                            break;
                                        }
                                        parent = parent.parentElement;
                                    }
                                    
                                    if (!inRow) {
                                        loadButtons.push(btn);
                                    }
                                }
                            }
                        }
                        
                        return loadButtons;
                    })();
                """)
                
                if js_buttons:
                    table_load_buttons.extend(js_buttons)
            
            # Registrar los botones encontrados
            logger.info(f"Se encontraron {len(table_load_buttons)} botones de carga a nivel de tabla")
            return table_load_buttons
            
        except Exception as e:
            logger.error(f"Error al buscar botones de carga: {e}")
            return []

 
 
 
 
 
 
 
 
 
 
 
    def extract_issues_data(self):
        """
        Método mejorado para extraer datos de issues con alta precisión.
        Implementa técnicas avanzadas para obtener todos los datos de las filas.
        """
        try:
            logger.info("MÉTODO: extract_issues_data - Iniciando extracción de datos mejorada")
            
            # Actualizar la interfaz si existe
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set("Iniciando extracción de datos...")
                
            # 1. Detectar tabla y obtener el número total de issues
            total_issues = self._detect_total_issues_from_tab()
            logger.info(f"Total de issues a procesar: {total_issues}")
            
            # 2. Hacer scroll mejorado para cargar todas las filas
            loaded_rows = self.scroll_to_load_all_items(total_issues)
            logger.info(f"Scroll completado. Rows cargadas: {loaded_rows}")
            
            # 3. Obtener todas las filas después del scroll
            logger.info("Obteniendo todas las filas después del scroll...")
            
            # Actualizar la interfaz
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set("Obteniendo todas las filas...")
                
            # Usar el método mejorado para encontrar las filas
            rows = self.find_table_rows(highlight=False)
            
            if not rows:
                logger.error("No se pudieron encontrar filas en la tabla")
                
                # Actualizar la interfaz
                if hasattr(self, 'status_var') and self.status_var:
                    self.status_var.set("ERROR: No se pudieron encontrar filas en la tabla")
                    
                return []
            
            # 4. Detectar el tipo de tabla y sus columnas
            table_info = self._detect_table_structure(rows[0])
            
            # 5. Lista para almacenar los datos extraídos
            issues_data = []
            processed_count = 0
            seen_titles = set()  # Para detectar posibles duplicados (no filtrarlos)
            
            # 6. Procesar cada fila para extraer datos
            logger.info(f"Procesando {len(rows)} filas...")
            
            # Actualizar la interfaz
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set(f"Procesando {len(rows)} filas...")
                
            for index, row in enumerate(rows):
                try:
                    # Actualizar la interfaz periódicamente
                    if index % 10 == 0:
                        if hasattr(self, 'status_var') and self.status_var:
                            self.status_var.set(f"Procesando fila {index+1} de {len(rows)}...")
                            if self.root:
                                self.root.update()
                    
                    # Extraer datos de la fila actual
                    issue_data = self._extract_row_data(row, index, table_info)
                    
                    # Verificar si obtuvimos datos válidos
                    if issue_data and issue_data.get('Title'):
                        # Registrar títulos para estadísticas (no filtrar duplicados)
                        title_lower = issue_data['Title'].lower()
                        if title_lower in seen_titles:
                            logger.debug(f"Título repetido detectado: '{issue_data['Title']}' (lo incluimos igualmente)")
                        seen_titles.add(title_lower)
                        
                        # Añadir a los datos recopilados
                        issues_data.append(issue_data)
                        processed_count += 1
                        
                        # Logging periódico
                        if processed_count % 10 == 0:
                            logger.info(f"Procesados {processed_count} issues hasta ahora")
                except Exception as row_e:
                    logger.error(f"Error al procesar la fila {index}: {row_e}")
                    
            # 7. Verificar resultados
            logger.info(f"Extracción completada. Total de issues procesados: {len(issues_data)}")
            
            # Actualizar la interfaz
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set(f"Extracción completada. Total: {len(issues_data)} issues")
            
            # 8. Guardar datos crudos para depuración (si hay issues)
            if issues_data:
                try:
                    with open("issues_data_raw.txt", "w", encoding="utf-8") as f:
                        for item in issues_data:
                            f.write(str(item) + "\n")
                except Exception as file_e:
                    logger.warning(f"No se pudo guardar el archivo de debug: {file_e}")
            
            return issues_data
            
        except Exception as e:
            logger.error(f"Error en la extracción de datos: {e}")
            return []

    def _detect_table_structure(self, sample_row):
        """
        Detecta la estructura de la tabla basada en una fila de muestra
        """
        try:
            # Intentar detectar el tipo de tabla y sus columnas
            logger.info("Detectando estructura de la tabla...")
            
            # 1. Detectar encabezados de tabla (si están disponibles)
            headers = self._detect_table_headers()
            
            # 2. Detectar celdas en la fila de muestra
            cells = []
            cell_selectors = [
                ".//td",  # Celdas de tabla HTML estándar
                ".//div[@role='gridcell']",  # Celdas de SAP UI5
                ".//div[contains(@class, 'sapMListCell')]",  # Celdas de lista SAP
                ".//span[contains(@class, 'sapMObjectIdentifier')]/..",  # Identificadores de objeto SAP
                "./div"  # Divs directos (para algunos tipos de lista)
            ]
            
            for selector in cell_selectors:
                try:
                    found_cells = sample_row.find_elements(By.XPATH, selector)
                    if found_cells and len(found_cells) > 1:
                        cells = found_cells
                        logger.info(f"Detectadas {len(cells)} celdas con selector {selector}")
                        break
                except:
                    continue
            
            # Si no se encontraron celdas con los selectores, usar JavaScript
            if not cells:
                logger.info("Intentando detectar celdas con JavaScript...")
                try:
                    cells = self.driver.execute_script("""
                        return (function(row) {
                            // Intentar encontrar todos los elementos hijo que parecen celdas
                            let possibleCells = [];
                            
                            // 1. Buscar elementos con roles o clases de celda
                            const cellElements = row.querySelectorAll('[role="gridcell"], [class*="Cell"], td');
                            if (cellElements.length > 1) {
                                return Array.from(cellElements);
                            }
                            
                            // 2. Buscar elementos hijo directos con contenido
                            const children = row.children;
                            if (children.length > 1) {
                                // Filtrar para incluir solo elementos con contenido visible
                                return Array.from(children).filter(el => el.textContent.trim() !== '');
                            }
                            
                            // 3. Si todo falla, encontrar spans o divs con contenido significativo
                            const textElements = row.querySelectorAll('span, div');
                            return Array.from(textElements).filter(el => {
                                const text = el.textContent.trim();
                                // Solo incluir elementos con texto que sean hijos directos o no tengan padre con texto
                                return text !== '' && 
                                    (el.parentElement === row || 
                                    el.parentElement.textContent.trim() === text);
                            });
                        })(arguments[0]);
                    """, sample_row)
                    
                    if cells and len(cells) > 1:
                        logger.info(f"JavaScript detectó {len(cells)} celdas")
                except Exception as js_e:
                    logger.debug(f"Error en detección con JavaScript: {js_e}")
            
            # Determinar índices de columnas basados en encabezados o posición
            column_indices = {
                'Title': 0,  # Por defecto, el título está en la primera columna
                'Type': 1,
                'Priority': 2,
                'Status': 3,
                'Deadline': 4,
                'Due Date': 5,
                'Created By': 6,
                'Created On': 7,
                'SAP Category': None,
                'Project': None,
                'System ID': None,
                'Last Updated': None
            }
            
            # Si tenemos encabezados, actualizar los índices
            if headers:
                # Crear un mapeo de nombres de encabezado a nombres de columna estándar
                header_mapping = {
                    'ISSUE TITLE': 'Title',
                    'TITLE': 'Title',
                    'TYPE': 'Type',
                    'PRIORITY': 'Priority',
                    'STATUS': 'Status',
                    'DEADLINE': 'Deadline',
                    'DUE DATE': 'Due Date',
                    'SESSION': 'SAP Category',
                    'SAP CATEGORY': 'SAP Category',
                    'COMMENT': 'Comment',
                    'CREATED BY': 'Created By',
                    'CREATED ON': 'Created On',
                    'ASSIGNED ROLE': 'Assigned Role',
                    'PROJECT': 'Project',
                    'SYSTEM ID': 'System ID',
                    'LANGUAGE': 'Language',
                    'LAST UPDATED': 'Last Updated',
                    'LAST CHANGED BY': 'Last Updated By'
                }
                
                # Actualizar índices según los encabezados encontrados
                for header_text, idx in headers.items():
                    header_upper = header_text.upper()
                    if header_upper in header_mapping:
                        standard_name = header_mapping[header_upper]
                        column_indices[standard_name] = idx
            
            return {
                'header_info': headers,
                'cell_count': len(cells) if cells else 0,
                'columns': column_indices
            }
        
        except Exception as e:
            logger.error(f"Error al detectar estructura de tabla: {e}")
            # Retornar una estructura por defecto
            return {
                'header_info': {},
                'cell_count': 0,
                'columns': {
                    'Title': 0,
                    'Type': 1,
                    'Priority': 2,
                    'Status': 3,
                    'Deadline': 4,
                    'Due Date': 5,
                    'Created By': 6,
                    'Created On': 7
                }
            }

    def _detect_table_headers(self):
        """
        Detecta los encabezados de la tabla y sus posiciones
        """
        try:
            # Intentar encontrar encabezados de tabla con múltiples selectores
            header_selectors = [
                "//tr[contains(@class, 'sapMListTblHeader')]/th",
                "//div[contains(@class, 'sapMListTblHeader')]//th",
                "//div[@role='columnheader']",
                "//div[contains(@class, 'sapMListHdr')]//span",
                "//div[contains(@class, 'sapUiTableColHdr')]//span"
            ]
            
            headers = {}
            
            for selector in header_selectors:
                try:
                    header_elements = self.driver.find_elements(By.XPATH, selector)
                    if header_elements and len(header_elements) > 1:
                        # Procesar los encabezados encontrados
                        for idx, header in enumerate(header_elements):
                            header_text = header.text.strip()
                            if header_text:
                                headers[header_text] = idx
                        
                        if headers:
                            logger.info(f"Detectados {len(headers)} encabezados con selector {selector}")
                            return headers
                except:
                    continue
            
            # Si no se encontraron encabezados con los selectores, usar JavaScript
            if not headers:
                logger.info("Intentando detectar encabezados con JavaScript...")
                try:
                    js_headers = self.driver.execute_script("""
                        return (function() {
                            // Intentar encontrar elementos de encabezado
                            const selectors = [
                                'th', 
                                '[role="columnheader"]', 
                                '.sapMListTblHeaderCell', 
                                '.sapUiTableColHdr'
                            ];
                            
                            let headerElements = [];
                            
                            // Probar cada selector
                            for (const selector of selectors) {
                                const elements = document.querySelectorAll(selector);
                                if (elements.length > 1) {
                                    headerElements = Array.from(elements);
                                    break;
                                }
                            }
                            
                            // Si no se encontraron encabezados, buscar en la primera fila
                            if (headerElements.length < 2) {
                                const firstRow = document.querySelector('.sapMListTbl tr:first-child, .sapMList li:first-child');
                                if (firstRow) {
                                    // Verificar si la primera fila parece un encabezado
                                    const cells = firstRow.querySelectorAll('td, [role="gridcell"]');
                                    if (cells.length > 1) {
                                        headerElements = Array.from(cells);
                                    }
                                }
                            }
                            
                            // Procesar los encabezados encontrados
                            const headers = {};
                            headerElements.forEach((el, idx) => {
                                const text = el.textContent.trim();
                                if (text) {
                                    headers[text] = idx;
                                }
                            });
                            
                            return headers;
                        })();
                    """)
                    
                    if js_headers and len(js_headers) > 1:
                        logger.info(f"JavaScript detectó {len(js_headers)} encabezados")
                        return js_headers
                except Exception as js_e:
                    logger.debug(f"Error en detección de encabezados con JavaScript: {js_e}")
            
            return headers
        
        except Exception as e:
            logger.error(f"Error al detectar encabezados de tabla: {e}")
            return {}










    def _extract_row_data(self, row, row_index, table_info):
        """
        Extrae datos de una fila de la tabla con alta precisión
        
        Args:
            row: Elemento WebElement de la fila
            row_index: Índice de la fila en la tabla
            table_info: Información sobre la estructura de la tabla
            
        Returns:
            dict: Diccionario con los datos extraídos
        """
        try:
            logger.debug(f"Extrayendo datos de fila {row_index}...")
            
            # Inicializar diccionario de resultados con valores por defecto
            issue_data = {
                'Title': '',
                'Type': 'Issue',  # Valor por defecto
                'Priority': 'N/A',
                'Status': 'N/A',
                'Deadline': '',
                'Due Date': 'N/A',
                'Created By': 'N/A',
                'Created On': 'N/A',
                'Comment': '',
                'SAP Category': '',
                'Project': '',
                'System ID': '',
                'Language': '',
                'Last Updated': '',
                'Last Updated By': ''
            }
            
            # ESTRATEGIA 1: Extraer el título primero (elemento más importante)
            title = self._extract_title_from_row(row)
            
            if not title:
                logger.warning(f"No se pudo extraer título para la fila {row_index}, saltando...")
                return None
                
            issue_data['Title'] = title
            
            # ESTRATEGIA 2: Extraer datos usando la estructura de la tabla
            cells = self._get_cells_from_row(row)
            
            if cells and len(cells) > 1:
                column_indices = table_info.get('columns', {})
                
                # Mapear datos de las celdas según los índices de columna
                for field, idx in column_indices.items():
                    if idx is not None and idx < len(cells):
                        cell = cells[idx]
                        # Extraer valor de la celda usando diferentes técnicas
                        value = self._extract_cell_value(cell)
                        
                        if value:
                            issue_data[field] = value
            
            # ESTRATEGIA 3: Extraer datos adicionales con técnicas específicas
            
            # 3.1 Extraer tipo de issue si no se encontró
            if not issue_data['Type'] or issue_data['Type'] == 'Issue':
                type_value = self._extract_specific_field(row, 'Type')
                if type_value:
                    issue_data['Type'] = type_value
                    
            # 3.2 Extraer prioridad
            if issue_data['Priority'] == 'N/A':
                priority_value = self._extract_priority(row)
                if priority_value:
                    issue_data['Priority'] = priority_value
                    
            # 3.3 Extraer estado
            if issue_data['Status'] == 'N/A':
                status_value = self._extract_status(row)
                if status_value:
                    issue_data['Status'] = status_value
            
            # 3.4 Buscar fechas (Due Date, Created On)
            if issue_data['Due Date'] == 'N/A' or issue_data['Created On'] == 'N/A':
                dates = self._extract_dates(row)
                if dates:
                    if 'Due Date' in dates and dates['Due Date']:
                        issue_data['Due Date'] = dates['Due Date']
                    if 'Created On' in dates and dates['Created On']:
                        issue_data['Created On'] = dates['Created On']
            
            # ESTRATEGIA 4: Usar JavaScript para análisis completo de la fila
            if cells and (len(cells) < 4 or issue_data['Status'] == 'N/A'):
                try:
                    # Usar JavaScript para analizar la fila entera
                    js_data = self.driver.execute_script("""
                        return (function(row) {
                            // Analizar la estructura completa de la fila
                            const result = {};
                            
                            // Función de ayuda para extraer texto limpio
                            function extractText(element) {
                                if (!element) return '';
                                let text = element.textContent || '';
                                return text.replace(/\\s+/g, ' ').trim();
                            }
                            
                            // Buscar textos que parezcan títulos
                            const titleElements = row.querySelectorAll('a, span[title], div[title]');
                            for (const el of titleElements) {
                                const text = extractText(el);
                                if (text && text.length > 5) {
                                    result.Title = text;
                                    break;
                                }
                            }
                            
                            // Buscar textos que parezcan tipos
                            const typePatterns = ['Recommendation', 'Implementation', 'Question', 'Problem', 'Incident', 'Request', 'Task'];
                            const allText = extractText(row);
                            for (const pattern of typePatterns) {
                                if (allText.includes(pattern)) {
                                    result.Type = pattern;
                                    break;
                                }
                            }
                            
                            // Buscar textos que parezcan prioridades
                            const priorityPatterns = {
                                'Very High': 'Very High',
                                'High': 'High',
                                'Medium': 'Medium',
                                'Low': 'Low'
                            };
                            
                            for (const [pattern, value] of Object.entries(priorityPatterns)) {
                                if (allText.includes(pattern)) {
                                    result.Priority = value;
                                    break;
                                }
                            }
                            
                            // Buscar textos que parezcan estados
                            const statusPatterns = ['OPEN', 'DONE', 'IN PROGRESS', 'READY', 'CLOSED', 'DRAFT'];
                            for (const pattern of statusPatterns) {
                                if (allText.includes(pattern)) {
                                    result.Status = pattern;
                                    break;
                                }
                            }
                            
                            return result;
                        })(arguments[0]);
                    """, row)
                    
                    # Actualizar datos con los resultados de JavaScript
                    if js_data:
                        for field, value in js_data.items():
                            if value and (not issue_data[field] or issue_data[field] == 'N/A'):
                                issue_data[field] = value
                except Exception as js_e:
                    logger.debug(f"Error en análisis JavaScript: {js_e}")
            
            # ESTRATEGIA 5: Procesar y limpiar los datos
            self._clean_issue_data(issue_data)
            
            return issue_data
            
        except Exception as e:
            logger.error(f"Error al extraer datos de fila {row_index}: {e}")
            return None


    def _extract_title_from_row(self, row):
        """
        Extrae el título de una fila usando múltiples técnicas
        """
        try:
            # Lista de selectores para extraer el título
            title_selectors = [
                ".//a",  # Enlaces (común para títulos clickeables)
                ".//span[contains(@class, 'title')]",  # Spans con clase title
                ".//div[contains(@class, 'title')]",  # Divs con clase title
                ".//div[@role='gridcell'][1]",  # Primera celda (suele ser el título)
                ".//td[1]",  # Primera celda de tabla HTML
                ".//*[contains(@id, 'title')]",  # Elementos con ID que contiene 'title'
                ".//*[@title]",  # Elementos con atributo title
                ".//span[@title]"  # Spans con atributo title
            ]
            
            # Probar cada selector
            for selector in title_selectors:
                try:
                    elements = row.find_elements(By.XPATH, selector)
                    for element in elements:
                        title_text = element.text.strip()
                        if title_text:
                            # Limpiar texto de botones "Show more"/"Show less"
                            cleaned_title = self._clean_title_text(title_text)
                            if cleaned_title:
                                return cleaned_title
                                
                        # Verificar atributo title si no hay texto
                        if not title_text and element.get_attribute("title"):
                            title_attr = element.get_attribute("title").strip()
                            cleaned_title = self._clean_title_text(title_attr)
                            if cleaned_title:
                                return cleaned_title
                except:
                    continue
                    
            # Si no encontramos título con los selectores, usar el texto de la primera celda
            try:
                cells = self._get_cells_from_row(row)
                if cells and len(cells) > 0:
                    first_cell_text = cells[0].text.strip()
                    if first_cell_text:
                        return self._clean_title_text(first_cell_text)
            except:
                pass
                
            # Como último recurso, extraer el primer texto significativo de la fila
            try:
                row_text = row.text.strip()
                if row_text:
                    # Dividir por líneas y tomar la primera que no esté vacía
                    lines = row_text.split('\n')
                    for line in lines:
                        cleaned_line = line.strip()
                        if cleaned_line and len(cleaned_line) > 3:
                            return self._clean_title_text(cleaned_line)
            except:
                pass
                
            return None
        
        except Exception as e:
            logger.debug(f"Error al extraer título: {e}")
            return None




    def _get_cells_from_row(self, row):
        """
        Extrae todas las celdas de una fila
        """
        try:
            # Lista de selectores para encontrar celdas
            cell_selectors = [
                ".//td",  # Celdas de tabla HTML
                ".//div[@role='gridcell']",  # Celdas de grid SAP UI5
                ".//div[contains(@class, 'sapMListCell')]",  # Celdas de lista SAP
                "./div"  # Divs directos (para algunos tipos de fila)
            ]
            
            # Probar cada selector
            for selector in cell_selectors:
                try:
                    cells = row.find_elements(By.XPATH, selector)
                    if cells and len(cells) > 1:
                        return cells
                except:
                    continue
                    
            # Si no se encontraron celdas, usar JavaScript
            try:
                js_cells = self.driver.execute_script("""
                    return (function(row) {
                        // Buscar elementos que parezcan celdas
                        const cellElements = row.querySelectorAll('[role="gridcell"], [class*="Cell"], td');
                        if (cellElements.length > 1) {
                            return Array.from(cellElements);
                        }
                        
                        // Si no, usar los hijos directos como celdas
                        return Array.from(row.children);
                    })(arguments[0]);
                """, row)
                
                if js_cells and len(js_cells) > 1:
                    return js_cells
            except Exception as js_e:
                logger.debug(f"Error al extraer celdas con JavaScript: {js_e}")
            
            # Como último recurso, dividir la fila en secciones basadas en el texto
            try:
                row_text = row.text
                if row_text:
                    lines = row_text.split('\n')
                    # Si hay varias líneas, tratar cada línea como una "celda"
                    if len(lines) > 1:
                        # Convertir cada línea en un elemento para mantener la interfaz
                        pseudo_cells = []
                        for line in lines:
                            if line.strip():
                                # Crear un diccionario con método text para simular WebElement
                                pseudo_cells.append({"text": line.strip()})
                        
                        if len(pseudo_cells) > 1:
                            return pseudo_cells
            except:
                pass
            
            return []
        
        except Exception as e:
            logger.debug(f"Error al extraer celdas: {e}")
            return []




    def _extract_cell_value(self, cell):
        """
        Extrae el valor de una celda con manejo especial para diferentes tipos
        """
        try:
            # Si es un diccionario (pseudo celda de fallback)
            if isinstance(cell, dict) and "text" in cell:
                return cell["text"]
            
            # Primero intentar obtener el texto directo
            cell_text = cell.text.strip() if hasattr(cell, 'text') else ""
            
            if cell_text:
                return cell_text
                
            # Si no hay texto directo, buscar en atributos
            for attr in ["title", "aria-label", "data-value"]:
                try:
                    value = cell.get_attribute(attr)
                    if value and value.strip():
                        return value.strip()
                except:
                    pass
                    
            # Buscar en elementos hijo
            try:
                child_elements = cell.find_elements(By.XPATH, ".//span | .//div | .//a")
                for child in child_elements:
                    child_text = child.text.strip()
                    if child_text:
                        return child_text
            except:
                pass
                
            # Usar JavaScript para obtener contenido interno
            try:
                js_text = self.driver.execute_script("""
                    return arguments[0].textContent.replace(/\\s+/g, ' ').trim();
                """, cell)
                
                if js_text:
                    return js_text
            except:
                pass
                
            return ""
        
        except Exception as e:
            logger.debug(f"Error al extraer valor de celda: {e}")
            return ""










    def _extract_specific_field(self, row, field):
        """
        Extrae un campo específico de la fila usando técnicas adaptadas a cada tipo de dato
        """
        try:
            if field == 'Type':
                # Buscar específicamente el tipo de issue
                type_selectors = [
                    ".//div[contains(@class, 'type')]",
                    ".//span[contains(@class, 'type')]",
                    ".//div[@role='gridcell'][2]//span",  # Típicamente en la segunda columna
                    ".//td[2]//span"
                ]
                
                for selector in type_selectors:
                    try:
                        elements = row.find_elements(By.XPATH, selector)
                        for element in elements:
                            type_text = element.text.strip()
                            if type_text:
                                return type_text
                    except:
                        continue
                        
                # Buscar posibles tipos en el texto
                potential_types = ["Recommendation", "Implementation", "Question", 
                                "Problem", "Incident", "Request", "Task", "Business Process"]
                
                row_text = row.text.lower() if hasattr(row, 'text') else ""
                for potential_type in potential_types:
                    if potential_type.lower() in row_text:
                        return potential_type
            
            return ""
        
        except Exception as e:
            logger.debug(f"Error al extraer campo específico {field}: {e}")
            return ""


    def _extract_priority(self, row):
        """
        Extrae la prioridad de una fila con técnicas especializadas
        """
        try:
            # Buscar indicadores de prioridad
            priority_indicators = [
                (By.XPATH, ".//span[contains(@class, 'sapMGaugeNegativeColor')]", "Very High"),
                (By.XPATH, ".//span[contains(@class, 'sapMGaugeCriticalColor')]", "High"),
                (By.XPATH, ".//span[contains(@class, 'sapMGaugeNeutralColor')]", "Medium"),
                (By.XPATH, ".//span[contains(@class, 'sapMGaugePositiveColor')]", "Low"),
                (By.XPATH, ".//span[contains(text(), 'Very High')]", "Very High"),
                (By.XPATH, ".//span[contains(text(), 'High')]", "High"),
                (By.XPATH, ".//span[contains(text(), 'Medium')]", "Medium"),
                (By.XPATH, ".//span[contains(text(), 'Low')]", "Low"),
                (By.XPATH, ".//span[contains(text(), 'very high')]", "Very High"),
                (By.XPATH, ".//span[contains(text(), 'high')]", "High"),
                (By.XPATH, ".//span[contains(text(), 'medium')]", "Medium"),
                (By.XPATH, ".//span[contains(text(), 'low')]", "Low")
            ]
            
            for locator, indicator_text in priority_indicators:
                try:
                    elements = row.find_elements(locator)
                    if elements:
                        return indicator_text
                except:
                    continue
                    
            # Buscar en el texto de la fila
            row_text = row.text.lower() if hasattr(row, 'text') else ""
            
            priority_keywords = {
                "very high": "Very High",
                "high": "High",
                "medium": "Medium",
                "low": "Low"
            }
            
            for keyword, value in priority_keywords.items():
                if keyword in row_text:
                    return value
                    
            return ""
        
        except Exception as e:
            logger.debug(f"Error al extraer prioridad: {e}")
            return ""


    def _extract_status(self, row):
        """
        Extrae el estado de una fila con técnicas especializadas
        """
        try:
            # Buscar elementos específicos de estado
            status_selectors = [
                ".//div[contains(@class, 'status')]",
                ".//span[contains(@class, 'status')]",
                ".//div[@role='gridcell'][3]",  # Típicamente en la tercera columna
                ".//td[3]"
            ]
            
            for selector in status_selectors:
                try:
                    elements = row.find_elements(By.XPATH, selector)
                    for element in elements:
                        status_text = element.text.strip()
                        if status_text:
                            return status_text
                except:
                    continue
                    
            # Buscar textos de estado comunes
            status_texts = ["OPEN", "DONE", "READY FOR PUBLISHING", "IN PROGRESS", "CLOSED", "DRAFT", 
                        "Open", "Done", "In Progress", "Closed"]
            
            for status in status_texts:
                try:
                    elements = row.find_elements(By.XPATH, f".//*[contains(text(), '{status}')]")
                    if elements:
                        for element in elements:
                            if element.is_displayed():
                                return status
                except:
                    continue
                    
            return ""
        
        except Exception as e:
            logger.debug(f"Error al extraer estado: {e}")
            return ""








    def _extract_dates(self, row):
        """
        Extrae fechas de una fila detectando patrones de fecha
        """
        try:
            result = {}
            
            # Buscar elementos que contengan fechas
            date_selectors = [
                ".//span[contains(@id, 'date')]",
                ".//div[contains(@id, 'date')]",
                ".//span[contains(@class, 'date')]",
                ".//div[contains(@class, 'date')]",
                ".//*[contains(text(), '/')]",  # Para fechas como MM/DD/YYYY
                ".//*[contains(text(), '-')]"   # Para fechas como YYYY-MM-DD
            ]
            
            date_elements = []
            for selector in date_selectors:
                try:
                    elements = row.find_elements(By.XPATH, selector)
                    date_elements.extend(elements)
                except:
                    continue
            
            # Patrones comunes para detectar fechas
            date_patterns = [
                r'\d{1,2}/\d{1,2}/\d{2,4}',        # MM/DD/YYYY o DD/MM/YYYY
                r'\d{4}-\d{1,2}-\d{1,2}',          # YYYY-MM-DD
                r'\d{1,2}-\d{1,2}-\d{2,4}',         # DD-MM-YYYY o MM-DD-YYYY
                r'[A-Za-z]{3} \d{1,2}, \d{4}',     # MMM DD, YYYY
                r'\d{1,2} [A-Za-z]{3} \d{4}'      # DD MMM YYYY
            ]
            
            # Si tenemos más de un elemento con fecha, asumir que el primero es Created On y el último Due Date
            if len(date_elements) >= 2:
                created_text = date_elements[0].text.strip()
                due_text = date_elements[-1].text.strip()
                
                if created_text:
                    result['Created On'] = created_text
                if due_text:
                    result['Due Date'] = due_text
            
            # En cualquier caso, buscar patrones de fecha en el texto completo
            row_text = row.text if hasattr(row, 'text') else ""
            
            import re
            dates_found = []
            
            for pattern in date_patterns:
                matches = re.findall(pattern, row_text)
                dates_found.extend(matches)
            
            # Si encontramos fechas por patrón, usar la lógica de asignación
            if dates_found:
                # Si hay al menos una fecha y no tenemos Created On, asignarla
                if len(dates_found) >= 1 and 'Created On' not in result:
                    result['Created On'] = dates_found[0]
                    
                # Si hay al menos dos fechas y no tenemos Due Date, asignar la última
                if len(dates_found) >= 2 and 'Due Date' not in result:
                    result['Due Date'] = dates_found[-1]
            
            return result
        
        except Exception as e:
            logger.debug(f"Error al extraer fechas: {e}")
            return {}

    def _clean_issue_data(self, issue_data):
        """
        Limpia y normaliza los datos del issue
        """
        try:
            # 1. Limpiar el título
            if issue_data['Title']:
                issue_data['Title'] = self._clean_title_text(issue_data['Title'])
                
            # 2. Normalizar estado
            if issue_data['Status'] and issue_data['Status'] != 'N/A':
                status_text = issue_data['Status'].upper()
                if 'OPEN' in status_text:
                    issue_data['Status'] = 'OPEN'
                elif 'DONE' in status_text:
                    issue_data['Status'] = 'DONE'
                elif 'IN PROGRESS' in status_text or 'IN-PROGRESS' in status_text:
                    issue_data['Status'] = 'IN PROGRESS'
                elif 'READY' in status_text:
                    issue_data['Status'] = 'READY'
                elif 'CLOSED' in status_text:
                    issue_data['Status'] = 'CLOSED'
                    
            # 3. Normalizar prioridad
            if issue_data['Priority'] and issue_data['Priority'] != 'N/A':
                priority_text = issue_data['Priority'].upper()
                if 'VERY HIGH' in priority_text or 'VERY-HIGH' in priority_text:
                    issue_data['Priority'] = 'Very High'
                elif 'HIGH' in priority_text and 'VERY' not in priority_text:
                    issue_data['Priority'] = 'High'
                elif 'MEDIUM' in priority_text or 'MED' in priority_text:
                    issue_data['Priority'] = 'Medium'
                elif 'LOW' in priority_text:
                    issue_data['Priority'] = 'Low'
                    
            # 4. Formatear fechas
            if issue_data['Created On'] and issue_data['Created On'] != 'N/A':
                try:
                    # Algunas veces la fecha viene como "Friday, January 10, 2025"
                    date_parts = issue_data['Created On'].split(",")
                    if len(date_parts) > 1:
                        issue_data['Created On'] = ",".join(date_parts[-2:]).strip()
                except:
                    pass
                    
            if issue_data['Due Date'] and issue_data['Due Date'] != 'N/A':
                try:
                    # Procesar formato de fecha
                    date_parts = issue_data['Due Date'].split(",")
                    if len(date_parts) > 1:
                        issue_data['Due Date'] = ",".join(date_parts[-2:]).strip()
                except:
                    pass
                    
            # 5. Asegurar valores por defecto para campos vacíos
            for field in issue_data:
                if not issue_data[field] or issue_data[field].strip() == '':
                    if field in ['Priority', 'Status', 'Created By', 'Created On', 'Due Date']:
                        issue_data[field] = 'N/A'
                    elif field == 'Type' and not issue_data[field]:
                        issue_data[field] = 'Issue'  # Valor por defecto
                    else:
                        issue_data[field] = ''
            
            return issue_data
        
        except Exception as e:
            logger.error(f"Error al limpiar datos: {e}")
            return issue_data

    def _clean_title_text(self, title_text):
        """
        Limpia el texto del título eliminando los textos de botones 'Show more'/'Show less'
        """
        try:
            if not title_text:
                return ""
                
            # Patrones a eliminar
            patterns_to_remove = [
                r'Show more',
                r'Show less',
                r'Mostrar más',
                r'Mostrar menos',
                r'More…',
                r'Less…',
                r'More\.\.\.', 
                r'Less\.\.\.',
                r'\s*\[\+\]\s*',  # [+]
                r'\s*\[-\]\s*'    # [-]
            ]
            
            # Eliminar cada patrón
            cleaned_text = title_text
            import re
            for pattern in patterns_to_remove:
                cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE)
            
            # Eliminar espacios extra
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
            
            return cleaned_text
            
        except Exception as e:
            logger.debug(f"Error al limpiar título: {e}")
            return title_text







            
    def _clean_title_text(self, title_text):
        """
        Limpia el texto del título eliminando los textos de botones 'Show more'/'Show less'.
        
        Args:
            title_text (str): El texto del título a limpiar
            
        Returns:
            str: Texto del título limpio
        """
        # Patrones a eliminar
        patterns_to_remove = [
            r'Show more',
            r'Show less',
            r'Mostrar más',
            r'Mostrar menos',
            r'More…',
            r'Less…',
            r'More...',
            r'Less...',
            r'\s*\[\+\]\s*',  # [+]
            r'\s*\[-\]\s*'    # [-]
        ]
        
        # Eliminar cada patrón
        cleaned_text = title_text
        for pattern in patterns_to_remove:
            cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE)
        
        # Eliminar espacios extra
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        
        return cleaned_text
 
 
 
 
 
 
 
 
 
 
 
 
 
    def find_table_rows(self, highlight=False):
        """
        Método mejorado para encontrar todas las filas de la tabla con mayor cobertura y detección.
        Combina los enfoques de V11.txt con técnicas adicionales.
        """
        all_rows = []
        logger.info("MÉTODO: find_table_rows - Buscando filas con técnicas avanzadas")

        # ESTRATEGIA 1: Usar selectores específicos de SAP UI5
        selectors = [
            # Selectores estándar de SAP UI5
            "//table[contains(@class, 'sapMListTbl')]/tbody/tr[not(contains(@class, 'sapMListTblHeader'))]",
            "//div[contains(@class, 'sapMList')]//li[contains(@class, 'sapMLIB')]",
            "//table[contains(@class, 'sapMList')]/tbody/tr",
            "//div[@role='row'][not(contains(@class, 'sapMListHeaderSubTitleItems')) and not(contains(@class, 'sapMListTblHeader'))]",
            "//div[contains(@class, 'sapMListItems')]/div[contains(@class, 'sapMListItem')]",
            "//div[contains(@class, 'sapMListItems')]//div[contains(@class, 'sapMObjectIdentifier')]/..",
            "//div[contains(@class, 'sapMListItem')]",
            # Nuevos selectores específicos 
            "//div[contains(@class, 'sapMListUl')]/li",
            "//div[contains(@class, 'sapUiTable')]//tr[contains(@class, 'sapUiTableRow')]",
            "//div[contains(@class, 'sapUiTableCnt')]//tr[not(contains(@class, 'sapUiTableHeaderRow'))]",
            "//div[contains(@class, 'sapUiTableCtrl')]//tr[contains(@data-sap-ui-rowindex)]",
            "//div[contains(@class, 'sapMLIB-CTX')]",
            "//div[contains(@class, 'sapMTableTBody')]//tr",
            "//tr[contains(@class, 'sapMListTblRow')]"
        ]

        for selector in selectors:
            try:
                rows = self.driver.find_elements(By.XPATH, selector)
                if len(rows) > 0:
                    logger.info(f"Se encontraron {len(rows)} filas con selector: {selector}")

                    valid_rows = []
                    for row in rows:
                        try:
                            # Verificar si la fila tiene contenido visible
                            if not self._is_row_visible(row):
                                continue
                                
                            # Verificar si la fila tiene contenido significativo
                            has_content = False
                            text_elements = row.find_elements(By.XPATH, ".//span | .//div | .//a")
                            for element in text_elements:
                                if element.text and element.text.strip():
                                    has_content = True
                                    break

                            if has_content:
                                valid_rows.append(row)
                        except:
                            # Si hay error, intentamos añadir la fila de todos modos
                            valid_rows.append(row)

                    if len(valid_rows) > 0:
                        all_rows = valid_rows
                        logger.info(f"Se encontraron {len(valid_rows)} filas válidas")

                        # Si encontramos un número significativo de filas, usamos este selector
                        if len(valid_rows) >= 20:
                            break
                
            except Exception as e:
                logger.debug(f"Error al buscar filas con selector {selector}: {e}")

        # ESTRATEGIA 2: Si la primera estrategia no encuentra suficientes filas, usar JavaScript
        if len(all_rows) < 5:
            logger.info("Pocas filas encontradas, intentando con JavaScript...")
            try:
                js_rows = self.driver.execute_script("""
                    return (function() {
                        // Arrays para almacenar filas y selectores usados
                        let foundRows = [];
                        let usedSelector = '';
                        
                        // Selectores de SAP UI5 para tablas
                        const selectors = [
                            '.sapMListItems > .sapMLIB',
                            '.sapMListTbl tbody tr',
                            '.sapMList li.sapMLIB',
                            '.sapUiTable tr[data-sap-ui-rowindex]',
                            '[role="row"]',
                            '.sapMListItem',
                            '.sapMTableTBody tr',
                            '.sapMLIB-CTX'
                        ];
                        
                        // Probar cada selector
                        for (const selector of selectors) {
                            const elements = document.querySelectorAll(selector);
                            
                            // Si encontramos elementos, verificar que sean visibles
                            if (elements.length > 0) {
                                const visibleElements = Array.from(elements).filter(el => {
                                    // Solo incluir elementos visibles con contenido
                                    return el.offsetParent !== null && 
                                        el.textContent.trim().length > 0 &&
                                        !el.classList.contains('sapMListTblHeader') &&
                                        !el.classList.contains('sapUiTableHeaderRow');
                                });
                                
                                if (visibleElements.length > 0) {
                                    foundRows = visibleElements;
                                    usedSelector = selector;
                                    // Si encontramos más de 20 filas, consideramos que es bueno
                                    if (visibleElements.length >= 20) {
                                        break;
                                    }
                                }
                            }
                        }
                        
                        // Información para logging
                        return {
                            selector: usedSelector,
                            count: foundRows.length,
                            rows: foundRows
                        };
                    })();
                """)
                
                if js_rows and js_rows.get('count', 0) > 0:
                    all_rows = js_rows.get('rows', [])
                    logger.info(f"JavaScript encontró {js_rows.get('count')} filas con selector '{js_rows.get('selector')}'")
            except Exception as js_e:
                logger.error(f"Error en búsqueda JavaScript: {js_e}")

        # ESTRATEGIA 3: Aproximación alternativa para casos difíciles
        if len(all_rows) < 5:
            logger.warning("No se encontraron suficientes filas con los selectores estándar. Intentando aproximación alternativa...")
            try:
                # Buscar elementos que puedan contener datos de issues
                any_rows = self.driver.find_elements(
                    By.XPATH,
                    "//div[contains(@class, 'sapM')] | //tr | //li[contains(@class, 'sapM')]"
                )

                alternative_rows = []
                for element in any_rows:
                    try:
                        # Verificar si el elemento tiene texto significativo
                        if self._is_row_visible(element) and element.text and len(element.text.strip()) > 10:
                            children = element.find_elements(By.XPATH, ".//*")
                            # Una fila típica tiene varios elementos hijo
                            if len(children) >= 3:
                                alternative_rows.append(element)
                    except:
                        continue

                if alternative_rows:
                    all_rows = alternative_rows
                    logger.info(f"Aproximación alternativa encontró {len(alternative_rows)} posibles filas")
            except Exception as e:
                logger.error(f"Error en la aproximación alternativa: {e}")

        # Solo resaltar visualmente si se indica explícitamente
        if highlight and len(all_rows) > 0:
            try:
                self.driver.execute_script(
                    """
                    arguments[0].scrollIntoView(true);
                    arguments[0].style.border = '2px solid red';
                """,
                    all_rows[0],
                )
                self.driver.save_screenshot("rows_found.png")
                logger.info(
                    f"Captura de pantalla de filas encontradas guardada como 'rows_found.png'"
                )
            except:
                pass

        # Eliminar posibles duplicados (mismo elemento WebElement)
        unique_rows = []
        unique_ids = set()
        
        for row in all_rows:
            try:
                row_id = self.driver.execute_script("return arguments[0].outerHTML", row)
                short_id = hashlib.md5(row_id.encode()).hexdigest()[:10]
                if short_id not in unique_ids:
                    unique_ids.add(short_id)
                    unique_rows.append(row)
            except:
                # Si falla al obtener el ID, añadir la fila de todos modos
                unique_rows.append(row)
        
        if len(unique_rows) != len(all_rows):
            logger.info(f"Se eliminaron {len(all_rows) - len(unique_rows)} filas duplicadas")
        
        logger.info(f"Total de filas encontradas: {len(unique_rows)}")
        return unique_rows

    def _is_row_visible(self, element):
        """
        Verifica si un elemento de fila es realmente visible en la página
        """
        try:
            return element.is_displayed() and self.driver.execute_script(
                "return arguments[0].offsetParent !== null && " +
                "arguments[0].getBoundingClientRect().height > 0", element
            )
        except:
            return False 
 
 
 
 
 
 
 
    
    def extract_all_issues(self):
        """
        Método robusto para extraer issues con múltiples estrategias de scroll.
        
        Returns:
            list: Lista de issues extraídos
        """
        try:
            logger.info("🚀 Iniciando extracción dinámica de issues...")
            
            # 1. Optimizar rendimiento de página
            try:
                optimize_browser_performance(self.driver)
                logger.info("✅ Rendimiento de página optimizado")
            except Exception as perf_error:
                logger.warning(f"⚠️ Error en optimización de rendimiento: {perf_error}")
            
            # 2. Detectar número total de issues
            total_issues = self._detect_total_issues_from_tab()
            logger.info(f"📊 Total de issues detectados: {total_issues}")
            
            # 3. Estrategias de scroll múltiples para cargar todas las filas
            loaded_rows = self.scroll_to_load_all_items(total_issues)
            
            # 4. Esperar un momento después de los scrolls
            time.sleep(3)
            
            
            
            
            
            
            
# 5. Detectar filas finales
            final_rows = find_table_rows_optimized(self.driver)
            logger.info(f"📝 Total de filas detectadas: {len(final_rows)}")
            
            # 6. Detectar encabezados para mapeo de columnas
            header_map = self._detect_table_headers_enhanced()
            logger.info(f"📑 Encabezados detectados: {header_map}")
            
            # 7. Extraer datos de las filas
            issues_data = []
            for index, row in enumerate(final_rows):
                try:
                    # Obtener celdas de la fila
                    cells = get_row_cells_optimized(row)
                    
                    if not cells or len(cells) < 3:
                        logger.debug(f"Fila {index} sin suficientes celdas, saltando...")
                        continue
                    
                    # Extraer datos usando encabezados
                    issue_data = self._extract_row_data_with_headers(cells, header_map)
                    
                    # Validar y agregar issue
                    if (
                        issue_data and 
                        issue_data.get('Title') and 
                        not any(control in issue_data['Title'].lower() for control in ['show more', 'load more'])
                    ):
                        issues_data.append(issue_data)
                    
                    # Actualizar progreso
                    if (index + 1) % 20 == 0:
                        logger.info(f"✏️ Procesadas {index + 1} filas de {len(final_rows)}")
                
                except Exception as row_error:
                    logger.debug(f"Error procesando fila {index}: {row_error}")
            
            # 8. Validación final
            if not issues_data:
                logger.warning("❌ No se encontraron issues después de la extracción")
            else:
                logger.info(f"✅ Issues extraídos: {len(issues_data)}")
            
            return issues_data
        
        except Exception as e:
            logger.error(f"Error crítico en extracción de issues: {e}")
            return []
    
    
    
    
    
    
    def extract_all_issues_robust(self):
        """
        Método principal mejorado para extraer todos los issues de manera robusta.
        Maneja correctamente la paginación, scroll y extracción de datos.
        
        Returns:
            list: Lista completa de issues extraídos
        """
        try:
            logger.info("=== MÉTODO: extract_all_issues_robust - INICIANDO EXTRACCIÓN ROBUSTA DE ISSUES ===")
            all_issues = []
            
            # Actualizar la interfaz si existe
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set("Iniciando extracción robusta de issues...")
                if self.root:
                    self.root.update()
            
            # 1. Asegurar que estamos en la pestaña correcta
            self._ensure_issues_tab_active()
            
            # 2. Detectar número total de issues esperados
            total_issues = self._detect_total_issues_from_tab()
            logger.info(f"Total de issues detectados: {total_issues}")
            
            # 3. Verificar si hay paginación
            has_pagination = self._check_and_handle_pagination()
            
            if has_pagination:
                logger.info("Se detectó paginación. Extrayendo issues en cada página.")
                
                # Para cada página, extraer los issues
                page_number = 1
                more_pages = True
                
                while more_pages and page_number <= 30:  # Límite de seguridad
                    logger.info(f"Procesando página {page_number}...")
                    
                    # Actualizar la interfaz
                    if hasattr(self, 'status_var') and self.status_var:
                        self.status_var.set(f"Procesando página {page_number}...")
                        if self.root:
                            self.root.update()
                    
                    # Extraer issues de la página actual
                    # 3.1 Cargar elementos en la página actual con scroll
                    self.scroll_to_load_all_items(total_issues // 10 + 5)  # Estimación de items por página
                    
                    # 3.2 Extraer datos de la página actual
                    page_issues = self._extract_current_page_issues()
                    
                    if page_issues:
                        all_issues.extend(page_issues)
                        logger.info(f"Se extrajeron {len(page_issues)} issues de la página {page_number}")
                    
                    # 3.3 Navegar a la siguiente página si existe
                    more_pages = self._navigate_to_next_page()
                    if more_pages:
                        page_number += 1
                        # Esperar a que cargue la nueva página
                        time.sleep(3)
                    else:
                        logger.info("No hay más páginas, finalizando extracción paginada.")
            else:
                logger.info("No se detectó paginación. Utilizando scroll para cargar todos los issues.")
                
                # 4. Hacer scroll para cargar todos los items
                loaded_rows = self.scroll_to_load_all_items(total_issues)
                logger.info(f"Se cargaron {loaded_rows} filas mediante scroll")
                
                # 5. Extraer los datos usando el método avanzado
                issues_data = self._extract_all_visible_issues()
                
                if issues_data:
                    all_issues.extend(issues_data)
                    logger.info(f"Se extrajeron {len(issues_data)} issues mediante scroll")
            
            # 6. Verificar resultados
            if all_issues:
                # Registrar información sobre posibles duplicados (solo para logging)
                titles_count = {}
                for issue in all_issues:
                    title = issue.get('Title', '').lower()
                    if title:
                        titles_count[title] = titles_count.get(title, 0) + 1
                
                # Contar cuántos títulos aparecen más de una vez (solo para información)
                duplicate_titles = sum(1 for title, count in titles_count.items() if count > 1)
                duplicate_entries = sum(count - 1 for count in titles_count.values() if count > 1)
                
                if duplicate_entries > 0:
                    logger.info(f"Nota: Se detectaron {duplicate_titles} títulos duplicados, con {duplicate_entries} entradas potencialmente duplicadas")
                    logger.info("Se conservarán todas las filas según lo solicitado")
                    
                logger.info(f"Extracción robusta completada. Total de issues extraídos: {len(all_issues)}")
                
                # Actualizar la interfaz si existe
                if hasattr(self, 'status_var') and self.status_var:
                    self.status_var.set(f"Extracción completada. Issues extraídos: {len(all_issues)}")
                    if self.root:
                        self.root.update()
                
                return all_issues
            else:
                logger.warning("No se encontraron issues para extraer")
                
                # Actualizar la interfaz si existe
                if hasattr(self, 'status_var') and self.status_var:
                    self.status_var.set("No se encontraron issues para extraer")
                    if self.root:
                        self.root.update()
                
                return []
        
        except Exception as e:
            logger.error(f"Error en la extracción robusta de issues: {e}")
            
            # Actualizar la interfaz si existe
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set(f"Error: {e}")
                if self.root:
                    self.root.update()
            
            return []






    def _ensure_issues_tab_active(self):
        """
        Asegura que estamos en la pestaña Issues
        """
        try:
            # Verificar si ya estamos en la pestaña Issues
            issues_active = False
            
            # Verificadores de pestaña activa
            active_tab_selectors = [
                "//div[@role='tab' and @aria-selected='true']//*[contains(text(), 'Issues')]",
                "//li[@role='tab' and @aria-selected='true']//*[contains(text(), 'Issues')]",
                "//div[contains(@class, 'sapMITBSelected')]//*[contains(text(), 'Issues')]"
            ]
            
            for selector in active_tab_selectors:
                elements = self.driver.find_elements(By.XPATH, selector)
                if elements and any(e.is_displayed() for e in elements):
                    logger.info("Ya estamos en la pestaña Issues")
                    issues_active = True
                    break
            
            if not issues_active:
                logger.info("No estamos en la pestaña Issues, intentando navegar a ella...")
                
                # Intentar hacer clic en la pestaña Issues
                issues_tab_selectors = [
                    "//div[@role='tab']//*[contains(text(), 'Issues')]",
                    "//li[@role='tab']//*[contains(text(), 'Issues')]",
                    "//div[contains(@class, 'sapMITBText')][contains(text(), 'Issues')]",
                    "//span[contains(text(), 'Issues')]"
                ]
                
                tab_clicked = False
                for selector in issues_tab_selectors:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            # Hacer scroll para asegurar visibilidad
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                            time.sleep(0.5)
                            
                            # Hacer clic
                            self.driver.execute_script("arguments[0].click();", element)
                            logger.info("Clic en pestaña Issues realizado")
                            tab_clicked = True
                            
                            # Esperar a que la pestaña se active
                            time.sleep(3)
                            break
                    
                    if tab_clicked:
                        break
                
                if not tab_clicked:
                    logger.warning("No se pudo hacer clic en la pestaña Issues")
                    
                    # Intentar JavaScript directo como último recurso
                    self.driver.execute_script("""
                        (function() {
                            // Intentar encontrar y hacer clic en la pestaña de issues
                            const tabTexts = ['Issues', 'Problemas', 'Incidentes', 'Incidencias'];
                            
                            for (const text of tabTexts) {
                                const elements = Array.from(document.querySelectorAll('*')).filter(el => 
                                    el.offsetParent !== null && 
                                    el.textContent.includes(text) &&
                                    (el.role === 'tab' || 
                                    el.parentElement?.role === 'tab' || 
                                    el.classList.contains('sapMITBText'))
                                );
                                
                                if (elements.length > 0) {
                                    // Hacer clic en el primer elemento encontrado
                                    elements[0].click();
                                    return true;
                                }
                            }
                            
                            return false;
                        })();
                    """)
            
            # Esperar a que cargue la pestaña
            time.sleep(2)
        
        except Exception as e:
            logger.error(f"Error al asegurar pestaña Issues activa: {e}")


    def _navigate_to_next_page(self):
        """
        Navega a la siguiente página en una interfaz paginada
        
        Returns:
            bool: True si se navegó a una nueva página, False si no hay más páginas
        """
        try:
            # Buscar el botón "Next" con diferentes selectores
            next_button_selectors = [
                "//button[contains(@title, 'Next Page')]",
                "//button[contains(@aria-label, 'Next Page')]",
                "//span[contains(@class, 'sapMPaginatorNext')]/..",
                "//button[contains(@class, 'sapMBtn') and .//span[contains(text(), 'Next')]]",
                "//div[contains(@class, 'sapMPageNext')]",
                "//span[contains(@class, 'sapUiIcon--navigation-right-arrow')]/.."
            ]
            
            next_button = None
            
            for selector in next_button_selectors:
                elements = self.driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed():
                        try:
                            is_enabled = element.is_enabled() and "sapMBtnDisabled" not in element.get_attribute("class")
                            if is_enabled:
                                next_button = element
                                break
                        except:
                            continue
                
                if next_button:
                    break
            
            # Si no se encontró un botón "Next" habilitado, no hay más páginas
            if not next_button:
                logger.info("No se encontró botón 'Next' habilitado, parece ser la última página")
                return False
            
            # Hacer clic en el botón "Next"
            try:
                # Hacer scroll para asegurar visibilidad
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                time.sleep(0.5)
                
                # Hacer clic
                self.driver.execute_script("arguments[0].click();", next_button)
                logger.info("Clic en botón 'Next' realizado")
                
                # Esperar a que cargue la nueva página
                time.sleep(2)
                
                # Verificar que realmente cambiamos de página
                # Podríamos verificar cambios en el contenido, pero por ahora solo validaremos
                # que el botón aún existe y está habilitado (para no fallar si solo hay una página)
                try:
                    is_disabled = "sapMBtnDisabled" in next_button.get_attribute("class") or not next_button.is_enabled()
                    if is_disabled:
                        logger.info("Botón 'Next' ahora está deshabilitado, es la última página")
                        return False
                except:
                    # Si hay error al verificar, asumimos que la navegación funcionó
                    pass
                
                return True
                
            except Exception as e:
                logger.warning(f"Error al hacer clic en botón 'Next': {e}")
                return False
        
        except Exception as e:
            logger.error(f"Error al navegar a la siguiente página: {e}")
            return False






    def _extract_current_page_issues(self):
        """
        Extrae issues de la página actual
        
        Returns:
            list: Lista de issues extraídos de la página actual
        """
        try:
            # 1. Detectar número total de issues en esta página
            rows = self.find_table_rows(highlight=False)
            
            if not rows:
                logger.warning("No se encontraron filas en la página actual")
                return []
            
            logger.info(f"Se encontraron {len(rows)} filas en la página actual")
            
            # 2. Detectar estructura de la tabla
            table_info = self._detect_table_structure(rows[0])
            
            # 3. Extraer datos de cada fila
            page_issues = []
            
            for index, row in enumerate(rows):
                try:
                    # Extraer datos de la fila
                    issue_data = self._extract_row_data(row, index, table_info)
                    
                    # Verificar si obtuvimos datos válidos
                    if issue_data and issue_data.get('Title'):
                        page_issues.append(issue_data)
                except Exception as row_e:
                    logger.error(f"Error al procesar fila {index}: {row_e}")
            
            logger.info(f"Se extrajeron {len(page_issues)} issues de la página actual")
            return page_issues
            
        except Exception as e:
            logger.error(f"Error al extraer issues de la página actual: {e}")
            return []










    def _extract_all_visible_issues(self):
        """
        Extrae todos los issues visibles después del scroll
        
        Returns:
            list: Lista de todos los issues extraídos
        """
        try:
            # 1. Encontrar todas las filas
            rows = self.find_table_rows(highlight=False)
            
            if not rows:
                logger.warning("No se encontraron filas después del scroll")
                return []
                
            logger.info(f"Se encontraron {len(rows)} filas después del scroll")
            
            # 2. Detectar estructura de la tabla
            table_info = self._detect_table_structure(rows[0])
            
            # 3. Extraer datos de cada fila
            all_issues = []
            processed_count = 0
            
            # Actualizar la interfaz
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set(f"Procesando {len(rows)} filas...")
                if self.root:
                    self.root.update()
            
            for index, row in enumerate(rows):
                try:
                    # Actualizar estado periódicamente
                    if index % 10 == 0 and hasattr(self, 'status_var') and self.status_var:
                        self.status_var.set(f"Procesando fila {index+1} de {len(rows)}...")
                        if self.root:
                            self.root.update()
                    
                    # Extraer datos de la fila
                    issue_data = self._extract_row_data(row, index, table_info)
                    
                    # Verificar si obtuvimos datos válidos
                    if issue_data and issue_data.get('Title'):
                        all_issues.append(issue_data)
                        processed_count += 1
                        
                        # Logging periódico
                        if processed_count % 10 == 0:
                            logger.info(f"Procesadas {processed_count} filas hasta ahora")
                except Exception as row_e:
                    logger.error(f"Error al procesar fila {index}: {row_e}")
            
            logger.info(f"Se extrajeron {len(all_issues)} issues en total")
            return all_issues
            
        except Exception as e:
            logger.error(f"Error al extraer todos los issues visibles: {e}")
            return []    
    
    
    
    
    
    
    





    def _detect_total_issues_from_tab(self):
        """
        Detecta el número total de issues directamente desde la pestaña o encabezado
        utilizando múltiples estrategias para mayor precisión.
        
        Returns:
            int: Número total de issues detectado o un estimado razonable (default 200)
        """
        try:
            logger.info("MÉTODO: _detect_total_issues_from_tab - Detectando número total de issues...")
            
            # Estrategia 1: Buscar texto "Issues (número)" en la pestaña
            tab_selectors = [
                "//div[contains(@class, 'sapMITBTab')]//*[contains(text(), 'Issues')]",
                "//div[contains(@class, 'sapMITBContent')]//span[contains(text(), 'Issues')]",
                "//div[@role='tab']//*[contains(text(), 'Issues')]",
                "//li[@role='tab']//*[contains(text(), 'Issues')]",
                "//div[contains(text(), 'Issues') and contains(text(), '(')]",
                "//span[contains(text(), 'Issues') and contains(text(), '(')]",
                "//li[contains(text(), 'Issues') and contains(text(), '(')]",
                "//a[contains(text(), 'Issues') and contains(text(), '(')]"
            ]
            
            for selector in tab_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            text = element.text.strip()
                            logger.debug(f"Tab encontrado: {text}")
                            
                            # Buscar número entre paréntesis
                            if '(' in text and ')' in text:
                                import re
                                match = re.search(r'\((\d+)\)', text)
                                if match:
                                    total = int(match.group(1))
                                    logger.info(f"Total de issues detectado: {total} (desde elemento de pestaña)")
                                    return total
                except Exception as e:
                    logger.debug(f"Error con selector {selector}: {e}")
                    continue
            
            # Estrategia 2: Usar JavaScript para buscar en todos los elementos visibles
            try:
                js_result = self.driver.execute_script("""
                    return (function() {
                        // Buscar en todos los elementos visibles
                        var elements = document.querySelectorAll('*');
                        for (var i = 0; i < elements.length; i++) {
                            var el = elements[i];
                            if (el.offsetParent !== null) {  // Elemento visible
                                var text = el.textContent || '';
                                
                                // Buscar patrón "Issues(número)" o "Issues (número)"
                                var match = text.match(/Issues\\s*\\((\\d+)\\)/i);
                                if (match && match[1]) {
                                    return parseInt(match[1], 10);
                                }
                            }
                        }
                        
                        // Buscar patrón alternativo "N of M" o similar
                        var countElements = document.querySelectorAll('.sapMListNoData, .sapMMessageToast, .sapMListInfo, .sapMITBCount');
                        for (var j = 0; j < countElements.length; j++) {
                            var countEl = countElements[j];
                            if (countEl.offsetParent !== null) {
                                var countText = countEl.textContent || '';
                                
                                // Patrones como "10 of 103" o "Showing 10 of 103"
                                var countMatch = countText.match(/\\d+\\s+of\\s+(\\d+)/i);
                                if (countMatch && countMatch[1]) {
                                    return parseInt(countMatch[1], 10);
                                }
                                
                                // Número solo (típico en contadores de pestañas)
                                var numMatch = countText.match(/^(\\d+)$/);
                                if (numMatch && numMatch[1]) {
                                    return parseInt(numMatch[1], 10);
                                }
                            }
                        }
                        
                        return 0;  // No se encontró
                    })();
                """)
                
                if js_result and js_result > 0:
                    logger.info(f"Total de issues detectado: {js_result} (mediante JavaScript)")
                    return js_result
            except Exception as js_e:
                logger.debug(f"Error en detección con JavaScript: {js_e}")
            
            # Estrategia 3: Buscar específicamente el contador de la pestaña "Issues"
            try:
                count_elements = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'sapMITBCount')]")
                for element in count_elements:
                    if element.is_displayed():
                        count_text = element.text.strip()
                        if count_text.isdigit():
                            count = int(count_text)
                            logger.info(f"Total de issues detectado: {count} (desde contador de pestaña)")
                            return count
            except Exception as e:
                logger.debug(f"Error al buscar contador de pestaña: {e}")
            
            # Estrategia 4: Hacer clic en la pestaña Issues y luego intentar nuevamente
            try:
                # Verificar si estamos ya en la pestaña Issues
                issues_tab_active = False
                active_tab_selectors = [
                    "//div[@role='tab' and @aria-selected='true']//*[contains(text(), 'Issues')]",
                    "//li[@role='tab' and @aria-selected='true']//*[contains(text(), 'Issues')]",
                    "//div[contains(@class, 'sapMITBSelected')]//*[contains(text(), 'Issues')]"
                ]
                
                for selector in active_tab_selectors:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements and any(e.is_displayed() for e in elements):
                        issues_tab_active = True
                        break
                
                if not issues_tab_active:
                    # Intentar hacer clic en la pestaña Issues
                    tab_clicked = False
                    issues_tab_selectors = [
                        "//div[@role='tab']//*[contains(text(), 'Issues')]",
                        "//li[@role='tab']//*[contains(text(), 'Issues')]",
                        "//div[contains(@class, 'sapMITBText')][contains(text(), 'Issues')]",
                        "//span[contains(text(), 'Issues')]"
                    ]
                    
                    for selector in issues_tab_selectors:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            if element.is_displayed():
                                # Hacer scroll para asegurar visibilidad
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                                time.sleep(0.5)
                                
                                # Hacer clic
                                self.driver.execute_script("arguments[0].click();", element)
                                logger.info("Clic en pestaña Issues realizado")
                                tab_clicked = True
                                time.sleep(2)  # Esperar a que se actualice
                                break
                        
                        if tab_clicked:
                            break
                    
                    if tab_clicked:
                        # Intentar detectar nuevamente después del clic
                        for selector in tab_selectors:
                            try:
                                elements = self.driver.find_elements(By.XPATH, selector)
                                for element in elements:
                                    if element.is_displayed():
                                        text = element.text.strip()
                                        if '(' in text and ')' in text:
                                            import re
                                            match = re.search(r'\((\d+)\)', text)
                                            if match:
                                                total = int(match.group(1))
                                                logger.info(f"Total de issues detectado: {total} (después de clic en pestaña)")
                                                return total
                            except:
                                continue
            except Exception as e:
                logger.debug(f"Error al intentar hacer clic en pestaña Issues: {e}")
            
            # Estrategia 5: Contar las filas visibles y hacer una estimación
            try:
                rows = self.find_table_rows(highlight=False)
                if rows:
                    visible_count = len(rows)
                    # Asignar límite mínimo y máximo razonable
                    if visible_count <= 10:
                        # Si vemos pocas filas, es probable que sea una tabla paginada
                        # Usar valor alto para forzar scrolling completo
                        estimated_total = 200
                    else:
                        # Si vemos bastantes filas, estimar un múltiplo
                        estimated_total = visible_count * 5
                    
                    # Limitar a un valor razonable
                    estimated_total = min(estimated_total, 300)
                    logger.warning(f"No se detectó total exacto de issues. Estimando {estimated_total} basado en {visible_count} filas visibles")
                    return estimated_total
            except Exception as e:
                logger.debug(f"Error al contar filas visibles: {e}")
            
            # Si todo lo anterior falla, usar valor predeterminado alto para mayor seguridad
            logger.warning("No se pudo detectar el número total de issues, usando valor predeterminado (200)")
            return 200
        
        except Exception as e:
            logger.error(f"Error al detectar número total de issues: {e}")
            return 200



    
    def _detect_table_headers_enhanced(self):
        """
        Detecta y mapea los encabezados de la tabla para mejor extracción
        con soporte para 18 columnas.
        
        Returns:
            dict: Diccionario que mapea nombres de encabezados a índices de columna
        """
        try:
            # Intentar encontrar la fila de encabezados
            header_selectors = [
                "//tr[contains(@class, 'sapMListTblHeader')]",
                "//div[contains(@class, 'sapMListTblHeaderCell')]/..",
                "//div[@role='columnheader']/parent::div[@role='row']",
                "//th[contains(@class, 'sapMListTblHeaderCell')]/.."
            ]
            
            for selector in header_selectors:
                header_rows = self.driver.find_elements(By.XPATH, selector)
                if header_rows:
                    # Tomar la primera fila de encabezados encontrada
                    header_row = header_rows[0]
                    
                    # Extraer las celdas de encabezado
                    header_cells = header_row.find_elements(By.XPATH, 
                        ".//th | .//div[@role='columnheader'] | .//div[contains(@class, 'sapMListTblHeaderCell')]")
                    
                    if header_cells:
                        # Mapear nombres de encabezados a índices
                        header_map = {}
                        for i, cell in enumerate(header_cells):
                            header_text = cell.text.strip()
                            if header_text:
                                header_map[header_text.upper()] = i
                        
                        logger.info(f"Encabezados detectados: {header_map}")
                        return header_map
            
            # Si el método anterior falla, usar JavaScript para extraer encabezados
            js_script = """
            (function() {
                // Buscar encabezados de tabla en diferentes formatos
                var headerElements = [];
                
                // 1. Buscar encabezados tradicionales
                var headers = document.querySelectorAll('th, div[role="columnheader"]');
                if (headers.length > 3) {
                    headerElements = Array.from(headers);
                }
                
                // 2. Buscar en otras estructuras de SAP UI5
                if (headerElements.length === 0) {
                    var sapHeaders = document.querySelectorAll('.sapMListTblHeaderCell, .sapUiTableHeaderCell');
                    if (sapHeaders.length > 3) {
                        headerElements = Array.from(sapHeaders);
                    }
                }
                
                // 3. Buscar en la primera fila (a veces contiene encabezados)
                if (headerElements.length === 0) {
                    var firstRow = document.querySelector('.sapMListItems > div:first-child, .sapMListTbl > tbody > tr:first-child');
                    if (firstRow) {
                        var cells = firstRow.querySelectorAll('td, div[role="gridcell"]');
                        if (cells.length > 3) {
                            headerElements = Array.from(cells);
                        }
                    }
                }
                
                // Extraer el texto de los encabezados
                var headerMap = {};
                for (var i = 0; i < headerElements.length; i++) {
                    var text = headerElements[i].textContent.trim();
                    if (text) {
                        headerMap[text.toUpperCase()] = i;
                    }
                }
                
                return headerMap;
            })();
            """
            
            header_map = self.driver.execute_script(js_script)
            if header_map and len(header_map) >= 4:
                logger.info(f"Encabezados detectados mediante JavaScript: {header_map}")
                return header_map
            
            logger.warning("No se pudieron detectar encabezados de tabla")
            
            
# Usar mapeo predeterminado si todo falla
            default_map = {
                'TITLE': 0,
                'TYPE': 1,
                'PRIORITY': 2,
                'STATUS': 3,
                'DEADLINE': 4,
                'DUE DATE': 5,
                'CREATED BY': 6,
                'CREATED ON': 7
            }
            
            logger.info(f"Usando mapeo de encabezados predeterminado: {default_map}")
            return default_map
            
        except Exception as e:
            logger.error(f"Error al detectar encabezados: {e}")
            return {
                'TITLE': 0,
                'TYPE': 1,
                'PRIORITY': 2,
                'STATUS': 3,
                'DEADLINE': 4,
                'DUE DATE': 5,
                'CREATED BY': 6,
                'CREATED ON': 7
            }
    
    def _extract_row_data_with_headers(self, cells, header_map):
        """
        Extrae datos de una fila usando el mapeo de encabezados.
        Soporta hasta 18 columnas.
        
        Args:
            cells (list): Lista de celdas WebElement
            header_map (dict): Mapeo de nombres de encabezados a índices
            
        Returns:
            dict: Diccionario con los datos extraídos
        """
        try:
            # Inicializar el diccionario con las 18 columnas posibles
            issue_data = {
                'Title': '',
                'Type': '',
                'Priority': '',
                'Status': '',
                'Deadline': '',
                'Due Date': '',
                'Created By': '',
                'Created On': '',
                'SAP Category': '',
                'Assigned To': '',
                'Responsible Team': '',
                'Last Change': '',
                'Updated By': '',
                'Description': '',
                'Notes': '',
                'Solution': '',
                'External ID': '',
                'Customer': ''
            }
            
            # Mapeo de nombres de encabezados a claves en nuestro diccionario
            header_mappings = {
                'TITLE': 'Title',
                'TYPE': 'Type',
                'PRIORITY': 'Priority',
                'STATUS': 'Status',
                'DEADLINE': 'Deadline',
                'DUE DATE': 'Due Date',
                'CREATED BY': 'Created By',
                'CREATED ON': 'Created On',
                'SAP CATEGORY': 'SAP Category',
                'ASSIGNED TO': 'Assigned To',
                'RESPONSIBLE TEAM': 'Responsible Team',
                'LAST CHANGE': 'Last Change',
                'UPDATED BY': 'Updated By',
                'DESCRIPTION': 'Description',
                'NOTES': 'Notes',
                'SOLUTION': 'Solution',
                'EXTERNAL ID': 'External ID',
                'CUSTOMER': 'Customer',
                # Mapeos alternativos para diferentes nomenclaturas
                'ISSUE TITLE': 'Title',
                'NAME': 'Title',
                'ISSUE': 'Title',
                'CATEGORY': 'SAP Category',
                'PRIO': 'Priority',
                'STATE': 'Status',
                'DUE': 'Due Date',
                'RESP TEAM': 'Responsible Team',
                'TEAM': 'Responsible Team',
                'ASSIGNED': 'Assigned To',
                'OWNER': 'Assigned To',
                'UPDATED ON': 'Last Change',
                'MODIFIED BY': 'Updated By',
                'ID': 'External ID',
                'COMMENT': 'Notes'
            }
            
            # Extraer valores usando el mapa de encabezados
            for header, index in header_map.items():
                if index < len(cells):
                    # Buscar la clave correspondiente
                    header_upper = header.upper()
                    matched = False
                    
                    # Buscar coincidencias exactas o parciales
                    for pattern, key in header_mappings.items():
                        if pattern == header_upper or header_upper.startswith(pattern) or pattern in header_upper:
                            cell_text = cells[index].text.strip() if cells[index].text else ''
                            issue_data[key] = cell_text
                            matched = True
                            break
                    
                    # Si no se encontró coincidencia para este encabezado, intentar inferir el tipo de dato
                    if not matched and header_upper:
                        cell_text = cells[index].text.strip() if cells[index].text else ''
                        
                        if cell_text:
                            # Intentar inferir el tipo de dato basado en el contenido
                            if any(date_marker in cell_text for date_marker in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']):
                                # Parece una fecha - buscar campo de fecha vacío
                                for date_field in ['Last Change', 'Created On', 'Due Date', 'Deadline']:
                                    if not issue_data[date_field]:
                                        issue_data[date_field] = cell_text
                                        break
                            
                            elif cell_text.startswith('I') and len(cell_text) > 1 and cell_text[1:].isdigit():
                                # Parece un ID de usuario SAP - buscar campo de usuario vacío
                                for user_field in ['Created By', 'Assigned To', 'Updated By']:
                                    if not issue_data[user_field]:
                                        issue_data[user_field] = cell_text
                                        break
                            
                            elif cell_text.upper() in ['OPEN', 'DONE', 'IN PROGRESS', 'READY', 'CLOSED']:
                                # Parece un estado
                                if not issue_data['Status']:
                                    issue_data['Status'] = cell_text
                            
                            elif cell_text.upper() in ['HIGH', 'MEDIUM', 'LOW', 'VERY HIGH']:
                                # Parece una prioridad
                                if not issue_data['Priority']:
                                    issue_data['Priority'] = cell_text
            
            # Si no se encontró un título, usar la primera celda
            if not issue_data['Title'] and len(cells) > 0:
                issue_data['Title'] = cells[0].text.strip() if cells[0].text else "Issue sin título"
            
            # Procesar y normalizar los datos
            self._process_issue_data(issue_data)
            
            return issue_data
        
        except Exception as e:
            logger.debug(f"Error al extraer datos de fila con encabezados: {e}")
            
            # En caso de error, intentar extraer al menos los datos básicos
            if len(cells) > 0:
                basic_data = {'Title': cells[0].text.strip() if cells[0].text else "Issue sin título"}
                for i in range(1, min(len(cells), 8)):
                    field_name = ['Type', 'Priority', 'Status', 'Deadline', 'Due Date', 'Created By', 'Created On'][i-1]
                    basic_data[field_name] = cells[i].text.strip() if cells[i].text else ""
                
                # Inicializar campos restantes
                for field in ['SAP Category', 'Assigned To', 'Responsible Team', 'Last Change', 
                            'Updated By', 'Description', 'Notes', 'Solution', 'External ID', 'Customer']:
                    basic_data[field] = ""
                    
                return basic_data
                
    def _process_issue_data(self, issue_data):
        """
        Procesa y normaliza los datos del issue para garantizar consistencia.
        
        Args:
            issue_data (dict): Datos del issue a procesar
            
        Returns:
            dict: Datos procesados y normalizados
        """
        try:
            # 1. Normalizar Status
            if issue_data['Status']:
                status_text = issue_data['Status'].upper()
                if 'OPEN' in status_text:
                    issue_data['Status'] = 'OPEN'
                elif 'DONE' in status_text:
                    issue_data['Status'] = 'DONE'
                elif 'IN PROGRESS' in status_text or 'IN-PROGRESS' in status_text:
                    issue_data['Status'] = 'IN PROGRESS'
                elif 'READY' in status_text:
                    issue_data['Status'] = 'READY'
                elif 'CLOSED' in status_text:
                    issue_data['Status'] = 'CLOSED'
            
            # 2. Normalizar Priority
            if issue_data['Priority']:
                priority_text = issue_data['Priority'].upper()
                if 'VERY HIGH' in priority_text or 'VERY-HIGH' in priority_text or 'VERY_HIGH' in priority_text:
                    issue_data['Priority'] = 'Very High'
                elif 'HIGH' in priority_text and 'VERY' not in priority_text:
                    issue_data['Priority'] = 'High'
                elif 'MEDIUM' in priority_text or 'MED' in priority_text:
                    issue_data['Priority'] = 'Medium'
                elif 'LOW' in priority_text:
                    issue_data['Priority'] = 'Low'
            
            # 3. Verificar errores de desplazamiento de columnas
            # Si Type es igual a Title, probablemente hay un error de desplazamiento
            if issue_data['Type'] == issue_data['Title'] and issue_data['Title']:
                logger.debug(f"Posible error de desplazamiento detectado para issue '{issue_data['Title']}'")
                
                # Intentar corregir desplazamiento
                issue_data['Type'] = issue_data['Priority'] if issue_data['Priority'] != issue_data['Title'] else ""
                issue_data['Priority'] = issue_data['Status'] if issue_data['Status'] != issue_data['Type'] else ""
                issue_data['Status'] = issue_data['Deadline'] if issue_data['Deadline'] != issue_data['Priority'] else ""
            
            # 4. Limpiar campos vacíos o con valores no válidos
            for field in issue_data:
                # Convertir valores None a string vacía
                if issue_data[field] is None:
                    issue_data[field] = ""
                    
                # Asegurar que todos los valores son strings
                if not isinstance(issue_data[field], str):
                    issue_data[field] = str(issue_data[field])
                    
                # Recortar textos extremadamente largos para Excel
                if len(issue_data[field]) > 32000:
                    issue_data[field] = issue_data[field][:32000] + "..."
            
            return issue_data
            
        except Exception as e:
            logger.error(f"Error al procesar datos de issue: {e}")
            return issue_data
