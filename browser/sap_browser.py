"""
Módulo principal para la automatización del navegador con Selenium.
Proporciona funcionalidades específicas para interactuar con aplicaciones SAP UI5/Fiori.
"""

import os
import time
import logging
import re
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
from config.settings import CHROME_PROFILE_DIR, BROWSER_TIMEOUT, MAX_RETRY_ATTEMPTS
from utils.logger_config import logger
from browser.element_finder import (
    find_table_rows, 
    detect_table_headers, 
    get_row_cells,
    find_ui5_elements,
    check_for_pagination,
    wait_for_element,
    detect_table_type,
    click_element_safely,
    optimize_browser_performance
)



# Importar el gestor de columnas
from browser.column_selection_manager import ColumnSelectionManager, configurar_columnas_visibles



# Configurar logger
logger = logging.getLogger(__name__)


class SAPBrowser:
    """Clase para la automatización del navegador y extracción de datos de SAP"""
    
    def __init__(self):
        """Inicializa el controlador del navegador"""
        self.driver = None
        self.wait = None
        self.element_cache = {}  # Caché para elementos encontrados frecuentemente
        
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




    def _interact_with_dropdown(self, input_field, erp_number):
        """
        Interactúa con la lista desplegable de SAP UI5 después de ingresar un valor.
        Optimizado para el comportamiento específico de SAP Fiori.
        
        Args:
            input_field: El elemento de entrada donde se ha introducido el ERP
            erp_number (str): El número ERP ingresado
                
        Returns:
            bool: True si se seleccionó un elemento, False en caso contrario
        """
        try:
            logger.info("Interactuando con dropdown SAP UI5...")
            
            # 1. Estrategia de fuerza bruta para asegurar la selección
            actions = ActionChains(self.driver)
            
            # Limpiar y reenfocar el campo
            self.driver.execute_script("arguments[0].value = '';", input_field)
            input_field.clear()
            input_field.click()
            time.sleep(0.5)
            
            # Volver a ingresar el valor
            input_field.send_keys(erp_number)
            time.sleep(1.0)  # Espera más larga para que aparezcan sugerencias
            
            # Intentar hacer clic en el primer elemento del dropdown
            try:
                # Script específico para encontrar y hacer clic directamente en la primera sugerencia
                js_click_first = """
                (function() {
                    // Buscar todos los popups de sugerencias visibles
                    var popups = document.querySelectorAll('.sapMSuggestionPopup, .sapMPopover, .sapMSelectList');
                    for (var i = 0; i < popups.length; i++) {
                        if (popups[i].offsetParent !== null) {  // Verificar si es visible
                            // Encontrar los items dentro del popup
                            var items = popups[i].querySelectorAll('li');
                            if (items.length > 0) {
                                // Hacer clic en el primer item
                                items[0].click();
                                return true;
                            }
                        }
                    }
                    return false;
                })();
                """
                
                clicked = self.driver.execute_script(js_click_first)
                if clicked:
                    logger.info("Clic directo en primera sugerencia exitoso")
                    time.sleep(1.5)
                    if self._verify_client_selection_strict(erp_number):
                        return True
            except Exception as e:
                logger.debug(f"Error en clic directo: {e}")
            
            # 2. Método secuencial preciso: Múltiples DOWN y ENTER
            # Esta secuencia más lenta pero más precisa funciona mejor en SAP Fiori
            for i in range(3):  # Tres pulsaciones DOWN para estar seguro
                actions.pause(0.5)  # Pausa más larga entre acciones
                actions.send_keys_to_element(input_field, Keys.DOWN)
            
            actions.pause(0.8)  # Pausa importante antes del ENTER
            actions.send_keys_to_element(input_field, Keys.ENTER)
            actions.perform()
            
            time.sleep(1.5)  # Tiempo adicional para que se complete la acción
            
            # Verificar si la selección fue exitosa
            if self._verify_client_selection_strict(erp_number):
                logger.info("Selección exitosa con secuencia de teclas múltiples DOWN + ENTER")
                return True
            
            # 3. Último recurso: TAB para confirmar y avanzar al siguiente campo
            logger.info("Intentando estrategia final: TAB + ENTER")
            actions = ActionChains(self.driver)
            actions.send_keys_to_element(input_field, Keys.TAB)
            actions.pause(0.5)
            actions.send_keys_to_element(input_field, Keys.ENTER)
            actions.perform()
            
            time.sleep(1.5)
            
            return self._verify_client_selection_strict(erp_number)
            
        except Exception as e:
            logger.error(f"Error al interactuar con dropdown: {e}")
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
        











    def wait_for_sap_navigation_complete(self, timeout: float = 30) -> bool:
        """
        Espera a que se complete la navegación en una aplicación SAP
        con verificación mejorada de la carga de elementos interactivos.
        
        Args:
            timeout (float): Tiempo máximo de espera en segundos
            
        Returns:
            bool: True si la navegación se completó, False en caso contrario
        """
        try:
            logger.info("Esperando a que la navegación SAP se complete...")
            start_time = time.time()
            
            # Paso 1: Esperar a que se complete el estado de readyState
            try:
                WebDriverWait(self.driver, timeout).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                logger.info("Estado de documento 'complete' detectado")
            except TimeoutException:
                logger.warning(f"Timeout esperando a que documento esté completo ({timeout}s)")
                # Continuar de todos modos, ya que algunos elementos pueden estar cargados
            
            # Paso 2: Esperar a que desaparezca cualquier indicador de ocupado
            busy_indicator_selectors = [
                "//div[contains(@class, 'sapUiLocalBusyIndicator')]",
                "//div[contains(@class, 'sapMBusyIndicator')]",
                "//div[contains(@class, 'sapUiBusy')]",
                "//div[contains(@class, 'sapMBlockLayerOnly')]"
            ]
            
            # Verificar cada indicador de carga
            for selector in busy_indicator_selectors:
                try:
                    # Esperar hasta que NO exista o no sea visible (tiempo más corto)
                    WebDriverWait(self.driver, 5).until_not(
                        EC.visibility_of_element_located((By.XPATH, selector))
                    )
                except:
                    # Verificar manualmente si hay indicadores visibles
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements and any(e.is_displayed() for e in elements):
                        logger.info(f"Indicador de carga sigue visible: {selector}")
                        
                        # Esperar un poco más para que desaparezca
                        time.sleep(3)
            
            # Paso 3: Esperar a que UI5 complete su inicialización
            ui5_ready = self.check_sap_ui5_loaded(min(10, timeout / 2))
            if ui5_ready:
                logger.info("Framework SAP UI5 detectado y cargado")
            else:
                logger.warning("No se pudo confirmar carga de SAP UI5")
            
            # Paso 4: Verificar que los elementos interactivos estén disponibles
            ui_elements = [
                "//input[contains(@placeholder, 'Customer')]",
                "//input[contains(@placeholder, 'Project')]",
                "//button[contains(@aria-label, 'Search')]",
                "//div[contains(@class, 'sapMBarLeft')]"
            ]
            
            # Verificar si al menos uno de los elementos de interfaz está visible
            element_found = False
            for selector in ui_elements:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements and any(e.is_displayed() for e in elements):
                        element_found = True
                        logger.info(f"Elemento interactivo detectado: {selector}")
                        break
                except:
                    continue
            
            if not element_found:
                logger.warning("No se detectaron elementos interactivos en la interfaz")
                # Si llevamos mucho tiempo sin detectar nada, intentar forzar un refresco
                if time.time() - start_time > timeout / 2:
                    try:
                        self.driver.execute_script("""
                            if (window.sap && window.sap.ui && window.sap.ui.getCore) {
                                sap.ui.getCore().applyChanges();
                            }
                        """)
                        logger.info("Intentado forzar refresco de UI mediante API SAP UI5")
                    except:
                        pass
            
            # Paso 5: Esperar un momento adicional para que se completen posibles operaciones AJAX
            time.sleep(2)
            
            # Verificación final de tiempo transcurrido
            elapsed = time.time() - start_time
            logger.info(f"Navegación SAP completada en {elapsed:.2f}s")
            
            return True
            
        except TimeoutException:
            logger.warning(f"Timeout esperando a que se complete la navegación SAP ({timeout}s)")
            return False
        except Exception as e:
            logger.error(f"Error al esperar navegación SAP: {e}")
            return False

    def check_sap_ui5_loaded(self, timeout: float = 10) -> bool:
        """
        Verifica si la biblioteca SAP UI5 ha cargado completamente
        con verificaciones mejoradas de la API UI5
        
        Args:
            timeout (float): Tiempo máximo de espera en segundos
            
        Returns:
            bool: True si UI5 ha cargado, False en caso contrario
        """
        try:
            logger.debug("Verificando disponibilidad de SAP UI5...")
            
            # Verificar primero si UI5 está actualmente disponible
            ui5_check = self.driver.execute_script("""
                return (
                    window.sap !== undefined && 
                    window.sap.ui !== undefined && 
                    window.sap.ui.getCore !== undefined
                );
            """)
            
            if not ui5_check:
                logger.debug("API UI5 no detectada inmediatamente, esperando...")
                
                # Esperar hasta que UI5 esté disponible
                start_time = time.time()
                while time.time() - start_time < timeout:
                    ui5_check = self.driver.execute_script("""
                        return (
                            window.sap !== undefined && 
                            window.sap.ui !== undefined && 
                            window.sap.ui.getCore !== undefined
                        );
                    """)
                    
                    if ui5_check:
                        break
                        
                    time.sleep(0.5)
            
            if not ui5_check:
                logger.warning("No se pudo detectar API SAP UI5")
                return False
            
            # Verificar si UI5 está listo para interactuar
            ui5_ready_check = self.driver.execute_script("""
                try {
                    return (
                        window.sap.ui.getCore().isReady === true || 
                        (typeof window.sap.ui.getCore().isReady === 'function' && window.sap.ui.getCore().isReady())
                    );
                } catch(e) {
                    return false;
                }
            """)
            
            if ui5_ready_check:
                logger.info("SAP UI5 está completamente cargado y listo")
                
                # Verificar versión de UI5 como información adicional
                try:
                    ui5_version = self.driver.execute_script("return sap.ui.version || 'desconocida';")
                    logger.debug(f"Versión de SAP UI5: {ui5_version}")
                except:
                    pass
                    
                return True
            else:
                # Intentar esperar explícitamente a que UI5 esté listo
                start_time = time.time()
                while time.time() - start_time < timeout:
                    ui5_ready_check = self.driver.execute_script("""
                        try {
                            return (
                                window.sap.ui.getCore().isReady === true || 
                                (typeof window.sap.ui.getCore().isReady === 'function' && window.sap.ui.getCore().isReady())
                            );
                        } catch(e) {
                            return false;
                        }
                    """)
                    
                    if ui5_ready_check:
                        logger.info("SAP UI5 está ahora listo para interactuar")
                        return True
                        
                    time.sleep(0.5)
                    
                logger.warning(f"SAP UI5 está presente pero no parece estar completamente listo")
                return False
                
        except Exception as e:
            logger.error(f"Error al verificar carga de SAP UI5: {e}")
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










    def click_settings_button(self):
        """
        Hace clic en el botón de engranaje (⚙️) que aparece en la interfaz y verifica
        que el panel de ajustes se abra correctamente.
        
        Este método implementa múltiples estrategias para localizar y hacer clic en el botón,
        y luego verifica que el panel de ajustes se haya abierto correctamente.
        
        Returns:
            bool: True si el clic fue exitoso y se abrió el panel, False en caso contrario
        """
        try:
            logger.info("Intentando hacer clic en el botón de ajustes (engranaje)...")
            
            # Esperar un momento para asegurar que la interfaz se ha cargado completamente
            time.sleep(3)
            
            # 1. ESTRATEGIA: Selectores altamente específicos para el botón de engranaje
            settings_selectors = [
                # Por ID o clase
                "//button[contains(@id, 'settings')]", 
                "//button[contains(@id, 'sap-ui-settings')]",
                "//button[contains(@class, 'sapMBtn') and contains(@id, 'settings')]",
                "//span[contains(@id, 'settings')]/ancestor::button",
                
                # Por ícono
                "//span[contains(@class, 'sapUiIcon') and contains(@data-sap-ui, 'setting')]/ancestor::button",
                "//span[contains(@class, 'sapUiIcon') and contains(@data-sap-ui, 'action-settings')]/ancestor::button",
                "//span[contains(@class, 'sapUiIcon') and @data-sap-ui='sap-icon://action-settings']/ancestor::button",
                
                # Por texto
                "//button[contains(@title, 'Settings')]",
                "//button[contains(@aria-label, 'Settings')]",
                
                # Por ubicación específica
                "//footer//button[last()]",
                "//div[contains(@class, 'sapMFooter')]//button",
                "//div[contains(@class, 'sapMBarRight')]//button[last()]",
                
                # Específicos de la interfaz de Issues & Actions
                "//div[contains(@class, 'sapMPage')]//button[last()]",
                "//div[contains(@class, 'sapMShellHeader')]//button[last()]",
                
                # Selectores específicos para el botón en la esquina inferior
                "//span[contains(@data-sap-ui, 'icon-action-settings')]/ancestor::button",
                "//div[contains(@class, 'sapMFlexBox')]//button[contains(@id, 'settings')]",
                "//div[contains(@class, 'sapMBarPH')]//button[last()]",
                "//div[contains(@class, 'sapMBarContainer')]/div[contains(@class, 'sapMBarRight')]//button"
            ]
            
            # Tomar captura de pantalla antes de intentar para análisis posterior
            try:
                pre_click_screenshot = os.path.join("logs", f"pre_settings_click_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                if not os.path.exists("logs"):
                    os.makedirs("logs")
                self.driver.save_screenshot(pre_click_screenshot)
                logger.info(f"Captura previa al clic guardada en: {pre_click_screenshot}")
            except:
                pass
            
            # Probar cada selector e intentar hacer clic
            for selector in settings_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            # Hacer scroll para garantizar visibilidad
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                            time.sleep(0.5)
                            
                            # Intentar con tres clics para asegurar que uno funcione
                            click_success = False
                            
                            # 1. Primero: JavaScript click (más confiable)
                            try:
                                logger.info(f"Encontrado botón de ajustes con selector: {selector}")
                                self.driver.execute_script("arguments[0].click();", element)
                                logger.info("Clic en botón de ajustes realizado con JavaScript")
                                click_success = True
                            except Exception as js_e:
                                logger.debug(f"Error en clic con JavaScript: {js_e}")
                            
                            # Verificar si se abrió el diálogo después del primer intento
                            if click_success and self._verify_settings_panel_opened():
                                return True
                            
                            # 2. Segundo: Clic normal
                            try:
                                element.click()
                                logger.info("Clic en botón de ajustes realizado con método normal")
                                click_success = True
                            except Exception as normal_click_e:
                                logger.debug(f"Error en clic normal: {normal_click_e}")
                            
                            # Verificar si se abrió el diálogo después del segundo intento
                            if click_success and self._verify_settings_panel_opened():
                                return True
                            
                            # 3. Tercero: Action Chains (más preciso)
                            try:
                                from selenium.webdriver.common.action_chains import ActionChains
                                actions = ActionChains(self.driver)
                                actions.move_to_element(element).click().perform()
                                logger.info("Clic en botón de ajustes realizado con Action Chains")
                                click_success = True
                            except Exception as action_e:
                                logger.debug(f"Error en clic con Action Chains: {action_e}")
                            
                            # Verificar si se abrió el diálogo después del tercer intento
                            if click_success and self._verify_settings_panel_opened():
                                return True
                except Exception as selector_e:
                    logger.debug(f"Error con selector {selector}: {selector_e}")
                    continue
            
            # 2. ESTRATEGIA: Búsqueda por posición específica en la pantalla
            logger.info("Intentando encontrar botón de ajustes por posición en la pantalla...")
            try:
                # Script para encontrar botones en la esquina inferior derecha
                position_script = """
                (function() {
                    // Buscar botones en la esquina inferior
                    var allButtons = Array.from(document.querySelectorAll('button'));
                    var viewportHeight = window.innerHeight;
                    var viewportWidth = window.innerWidth;
                    
                    // Buscar botones en la parte inferior de la pantalla
                    var bottomButtons = allButtons.filter(function(btn) {
                        if (!btn.offsetParent) return false; // No visible
                        var rect = btn.getBoundingClientRect();
                        
                        // Botones en la parte inferior de la pantalla
                        return rect.top > (viewportHeight * 0.7) && 
                            rect.bottom <= viewportHeight;
                    });
                    
                    // Ordenar por posición (de derecha a izquierda)
                    bottomButtons.sort(function(a, b) {
                        var rectA = a.getBoundingClientRect();
                        var rectB = b.getBoundingClientRect();
                        return rectB.right - rectA.right; // Primero los de la derecha
                    });
                    
                    // Imprimir información para debugging
                    console.log("Botones en la parte inferior: " + bottomButtons.length);
                    
                    // Hacer clic en el primer botón (más a la derecha)
                    if (bottomButtons.length > 0) {
                        bottomButtons[0].click();
                        return true;
                    }
                    
                    return false;
                })();
                """
                
                result = self.driver.execute_script(position_script)
                if result:
                    logger.info("Clic realizado en botón mediante posición en pantalla")
                    time.sleep(2)
                    if self._verify_settings_panel_opened():
                        return True
            except Exception as pos_e:
                logger.debug(f"Error en estrategia de posición: {pos_e}")
            
            # 3. ESTRATEGIA: Atajos de teclado - SAP UI5 suele responder a Alt+O para opciones
            logger.info("Intentando abrir ajustes con atajos de teclado...")
            try:
                body = self.driver.find_element(By.TAG_NAME, "body")
                
                # Secuencia Alt+O (común para opciones en SAP)
                from selenium.webdriver.common.keys import Keys
                from selenium.webdriver.common.action_chains import ActionChains
                
                actions = ActionChains(self.driver)
                # Presionar Alt+O
                actions.key_down(Keys.ALT).send_keys('o').key_up(Keys.ALT).perform()
                logger.info("Enviada secuencia Alt+O para abrir opciones")
                time.sleep(2)
                
                if self._verify_settings_panel_opened():
                    return True
                    
                # Intentar con otras combinaciones comunes para abrir menús de opciones
                actions = ActionChains(self.driver)
                # Ctrl+,
                actions.key_down(Keys.CONTROL).send_keys(',').key_up(Keys.CONTROL).perform()
                logger.info("Enviada secuencia Ctrl+, para abrir opciones")
                time.sleep(2)
                
                if self._verify_settings_panel_opened():
                    return True
            except Exception as key_e:
                logger.debug(f"Error en estrategia de atajos de teclado: {key_e}")
            
            # 4. ESTRATEGIA: Si todo lo demás falló, hacer clic en cada botón visible del footer
            logger.info("Estrategia final: intentando con todos los botones del footer...")
            try:
                footer_buttons = self.driver.find_elements(By.XPATH, 
                    "//div[contains(@class, 'sapMFooter')]//button | //footer//button")
                
                for btn in footer_buttons:
                    if btn.is_displayed() and btn.is_enabled():
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                            time.sleep(0.5)
                            self.driver.execute_script("arguments[0].click();", btn)
                            logger.info(f"Clic en botón del footer ({btn.text or 'sin texto'})")
                            time.sleep(2)
                            
                            if self._verify_settings_panel_opened():
                                return True
                        except:
                            continue
            except Exception as footer_e:
                logger.debug(f"Error en estrategia de botones del footer: {footer_e}")
            
            # 5. ESTRATEGIA: Último recurso - tomar captura de pantalla para análisis
            try:
                screenshot_path = os.path.join("logs", f"settings_button_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                if not os.path.exists("logs"):
                    os.makedirs("logs")
                    
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"Captura de pantalla guardada en: {screenshot_path}")
                logger.error("No se pudo encontrar o hacer clic en el botón de ajustes. Revise la captura de pantalla para análisis manual.")
            except Exception as ss_e:
                logger.debug(f"Error al tomar captura de pantalla: {ss_e}")
            
            return False
            
        except Exception as e:
            logger.error(f"Error general al intentar hacer clic en botón de ajustes: {e}")
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
        
        







    def force_open_settings(self):
        """
        Método agresivo para forzar la apertura del panel de ajustes cuando los métodos
        convencionales fallan. Realiza múltiples acciones de manera secuencial.
        
        Returns:
            bool: True si se logró abrir el panel de ajustes, False en caso contrario
        """
        try:
            logger.info("Iniciando método agresivo para abrir panel de ajustes...")
            
            # 1. Identificar todos los botones en la esquina inferior derecha
            script_identify_buttons = """
            return (function() {
                // Todos los botones visibles
                var allButtons = Array.from(document.querySelectorAll('button')).filter(function(btn) {
                    return btn.offsetParent !== null; // Elemento visible
                });
                
                // Información sobre los botones
                var buttonInfo = allButtons.map(function(btn) {
                    var rect = btn.getBoundingClientRect();
                    return {
                        id: btn.id || "",
                        classes: btn.className || "",
                        text: btn.textContent || "",
                        x: rect.left,
                        y: rect.top,
                        width: rect.width,
                        height: rect.height,
                        bottomRight: rect.right >= (window.innerWidth * 0.7) && rect.bottom >= (window.innerHeight * 0.7)
                    };
                });
                
                return buttonInfo;
            })();
            """
            
            button_info = self.driver.execute_script(script_identify_buttons)
            logger.info(f"Se identificaron {len(button_info)} botones en la página")
            
            # Guardar captura de pantalla para análisis
            try:
                screenshot_path = os.path.join("logs", f"before_force_open_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                if not os.path.exists("logs"):
                    os.makedirs("logs")
                self.driver.save_screenshot(screenshot_path)
            except:
                pass
            
            # 2. Ordenar los botones: primero los de la esquina inferior derecha, luego por ID o clase
            def button_priority(btn_info):
                # Mayor prioridad: botones en esquina inferior derecha
                if btn_info.get('bottomRight', False):
                    return 3
                # Prioridad media: botones con "settings" en id o clase
                elif 'settings' in btn_info.get('id', '').lower() or 'settings' in btn_info.get('classes', '').lower():
                    return 2
                # Prioridad baja: últimos botones en la interfaz
                else:
                    return 1
                    
            # Ordenar por prioridad
            sorted_buttons = sorted(
                button_info, 
                key=button_priority,
                reverse=True  # Mayor prioridad primero
            )
            
            # 3. Intentar hacer clic en cada botón prioritario
            clicks_attempted = 0
            for i, btn_info in enumerate(sorted_buttons[:5]):  # Limitar a los 5 más probables
                try:
                    # Construir un XPath único para este botón
                    xpath = f"//button"
                    
                    # Añadir ID si existe
                    if btn_info.get('id'):
                        xpath = f"//button[@id='{btn_info['id']}']"
                    # Añadir clase si existe
                    elif btn_info.get('classes'):
                        class_list = btn_info['classes'].split()
                        if class_list:
                            xpath = f"//button[contains(@class, '{class_list[0]}')]"
                    
                    # Intentar encontrar el botón
                    buttons = self.driver.find_elements(By.XPATH, xpath)
                    if not buttons:
                        continue
                        
                    # Hacer clic en el botón
                    button = buttons[0]
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                    time.sleep(0.5)
                    
                    logger.info(f"Intentando clic en botón #{i+1}: ID='{btn_info.get('id', '')}', Classes='{btn_info.get('classes', '')}'")
                    
                    # Usar JavaScript para el clic
                    self.driver.execute_script("arguments[0].click();", button)
                    clicks_attempted += 1
                    
                    # Esperar a ver si se abre algún panel
                    time.sleep(2)
                    
                    # Verificar si se abrió algún panel de ajustes
                    if self._verify_settings_panel_opened():
                        logger.info(f"¡Éxito! Panel de ajustes abierto después de {clicks_attempted} intentos")
                        return True
                        
                except Exception as btn_e:
                    logger.debug(f"Error al hacer clic en botón #{i+1}: {btn_e}")
                    continue
            
            # 4. Si no funcionó, intentar con teclas de acceso rápido comunes en SAP
            common_shortcuts = [
                # Combinación de teclas, Descripción
                ((Keys.ALT, 's'), "Alt+S (Settings)"),
                ((Keys.ALT, 'o'), "Alt+O (Options)"),
                ((Keys.CONTROL, 's'), "Ctrl+S (Settings)"),
                ((Keys.CONTROL, 'o'), "Ctrl+O (Options)"),
                ((Keys.CONTROL, ','), "Ctrl+, (Preferences)")
            ]
            
            for shortcut, description in common_shortcuts:
                try:
                    logger.info(f"Intentando atajo de teclado: {description}")
                    actions = ActionChains(self.driver)
                    
                    # Presionar las teclas modificadoras
                    if shortcut[0] == Keys.CONTROL:
                        actions.key_down(Keys.CONTROL)
                    elif shortcut[0] == Keys.ALT:
                        actions.key_down(Keys.ALT)
                    
                    # Presionar la tecla principal
                    actions.send_keys(shortcut[1])
                    
                    # Liberar modificadores
                    if shortcut[0] == Keys.CONTROL:
                        actions.key_up(Keys.CONTROL)
                    elif shortcut[0] == Keys.ALT:
                        actions.key_up(Keys.ALT)
                    
                    # Ejecutar secuencia
                    actions.perform()
                    time.sleep(2)
                    
                    # Verificar si se abrió el panel
                    if self._verify_settings_panel_opened():
                        logger.info(f"¡Éxito! Panel de ajustes abierto con atajo {description}")
                        return True
                except Exception as shortcut_e:
                    logger.debug(f"Error con atajo {description}: {shortcut_e}")
                    continue
            
            # Si llegamos aquí, todos los intentos fallaron
            logger.warning("No se pudo abrir el panel de ajustes con ningún método")
            return False
            
        except Exception as e:
            logger.error(f"Error general en método agresivo para abrir ajustes: {e}")
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

    def scroll_to_load_all_items(self, total_expected=100, max_attempts=100):
        """
        Estrategia optimizada para cargar todos los elementos mediante scroll con mejor rendimiento
        
        Args:
            total_expected (int): Número total de elementos esperados
            max_attempts (int): Número máximo de intentos de scroll
            
        Returns:
            int: Número de elementos cargados
        """
        logger.info(f"Iniciando carga de {total_expected} elementos...")
        
        previous_rows_count = 0
        no_change_count = 0
        no_change_threshold = 10
        
        # Verificar tipo de tabla y estrategia de carga
        table_type = detect_table_type(self.driver)
        logger.info(f"Tipo de tabla detectado: {table_type}")
        
        # Verificar si hay paginación
        pagination_elements = check_for_pagination(self.driver)
        has_pagination = pagination_elements is not None and len(pagination_elements) > 0
        
        logger.info(f"¿La tabla tiene paginación? {'Sí' if has_pagination else 'No'}")
        
        # Ejecutar script para optimizar el rendimiento del navegador
        optimize_browser_performance(self.driver)
        
        # Algoritmo principal de scroll
        for attempt in range(max_attempts):
            try:
                # Usar estrategia de scroll adaptada al tipo de tabla detectado
                if table_type == "standard_ui5":
                    self._scroll_standard_ui5_table()
                elif table_type == "responsive_table":
                    self._scroll_responsive_table()
                elif table_type == "grid_table":
                    self._scroll_grid_table()
                else:
                    # Estrategia genérica
                    self._scroll_generic()
                
                # Contar filas actualmente visibles
                rows = find_table_rows(self.driver, highlight=False)
                current_rows_count = len(rows)
                
                # Registrar progreso periódicamente
                if attempt % 10 == 0:
                    logger.info(f"Intento {attempt+1}: {current_rows_count} filas cargadas")
                
                # Verificación de carga completa con lógica mejorada
                if current_rows_count == previous_rows_count:
                    no_change_count += 1
                    
                    # Si hay paginación y no hay cambios, intentar pasar a página siguiente
                    if has_pagination and no_change_count >= 5:
                        logger.info("Intentando pasar a la siguiente página...")
                        pagination_elements = check_for_pagination(self.driver)
                        if pagination_elements and self.click_pagination_next(pagination_elements):
                            logger.info("Se pasó a la siguiente página")
                            no_change_count = 0
                            time.sleep(3)
                            continue
                    
                    # Si no hay cambios, aplicar estrategias adicionales de scroll
                    if no_change_count >= 5:
                        if no_change_count % 5 == 0:  # Alternar estrategias
                            self._apply_alternative_scroll_strategy(no_change_count)
                    
                    # Criterios de finalización adaptados
                    if self._should_finish_scrolling(no_change_count, current_rows_count, total_expected):
                        break
                else:
                    # Reiniciar contador si se encontraron más filas
                    no_change_count = 0
                    
                previous_rows_count = current_rows_count
                
                # Si se alcanzó o superó el número esperado, terminar
                if current_rows_count >= total_expected:
                    logger.info(f"Se han cargado {current_rows_count} filas (>= {total_expected} esperadas)")
                    break
                
                # Tiempo adaptativo de espera basado en el rendimiento
                wait_time = self._calculate_adaptive_wait_time(no_change_count, current_rows_count)
                time.sleep(wait_time)
                    
            except Exception as e:
                logger.warning(f"Error durante el scroll en intento {attempt+1}: {e}")
            
        # Calcular y reportar métricas de éxito
        coverage = (previous_rows_count / total_expected) * 100 if total_expected > 0 else 0
        logger.info(f"Scroll completado. Cobertura: {coverage:.2f}% ({previous_rows_count}/{total_expected})")
        
        return previous_rows_count
        
    def _scroll_standard_ui5_table(self):
        """
        Estrategia de scroll específica para tablas estándar de SAP UI5.
        
        Returns:
            bool: True si el scroll fue exitoso, False en caso contrario
        """
        try:
            # Identificar contenedores de tablas estándar UI5
            table_containers = self.driver.find_elements(
                By.XPATH, 
                "//div[contains(@class, 'sapMListItems')] | " +
                "//div[contains(@class, 'sapMTableTBody')] | " +
                "//table[contains(@class, 'sapMListTbl')]/parent::div"
            )
            
            # Si se encuentran contenedores específicos, hacer scroll en ellos
            if table_containers:
                for container in table_containers:
                    # Realizar scroll al final del contenedor específico
                    self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", container)
                    time.sleep(0.2)  # Breve pausa para permitir carga
            else:
                # Si no se encuentran contenedores específicos, usar scroll general
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
            return True
        except Exception as e:
            logger.debug(f"Error en scroll de tabla estándar UI5: {e}")
            return False
            
    def _scroll_responsive_table(self):
        """
        Estrategia de scroll específica para tablas responsivas de SAP UI5.
        
        Returns:
            bool: True si el scroll fue exitoso, False en caso contrario
        """
        try:
            # Script específico para tablas responsivas, con mayor precisión
            scroll_script = """
                // Identificar contenedores de listas y tablas responsivas
                var listContainers = document.querySelectorAll(
                    '.sapMList, .sapMListItems, .sapMListUl, .sapMLIB'
                );
                
                // Si encontramos contenedores específicos, hacer scroll en ellos
                if (listContainers.length > 0) {
                    for (var i = 0; i < listContainers.length; i++) {
                        if (listContainers[i].scrollHeight > listContainers[i].clientHeight) {
                            listContainers[i].scrollTop = listContainers[i].scrollHeight;
                        }
                    }
                    return true;
                } else {
                    // Si no encontramos contenedores específicos, scroll general
                    window.scrollTo(0, document.body.scrollHeight);
                    return false;
                }
            """
            
            result = self.driver.execute_script(scroll_script)
            
            # Si el script no encontró contenedores específicos, intentar con Page Down
            if result is False:
                try:
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    body.send_keys(Keys.PAGE_DOWN)
                except:
                    pass
                    
            return True
        except Exception as e:
            logger.debug(f"Error en scroll de tabla responsiva: {e}")
            return False
        
        
        
        
        
        
        
        
        
        
        
    def _scroll_grid_table(self):
        """
        Estrategia de scroll específica para tablas tipo grid de SAP UI5.
        
        Returns:
            bool: True si el scroll fue exitoso, False en caso contrario
        """
        try:
            # Script especializado para tablas grid de UI5
            grid_scroll_script = """
                // Identificar contenedores de scroll en tablas grid
                var gridContainers = document.querySelectorAll(
                    '.sapUiTableCtrlScr, .sapUiTableCtrlCnt, .sapUiTableRowHdr'
                );
                
                var didScroll = false;
                
                // Hacer scroll en cada contenedor relevante
                if (gridContainers.length > 0) {
                    for (var i = 0; i < gridContainers.length; i++) {
                        // Verificar si el contenedor tiene scroll
                        if (gridContainers[i].scrollHeight > gridContainers[i].clientHeight) {
                            // Scroll vertical máximo
                            gridContainers[i].scrollTop = gridContainers[i].scrollHeight;
                            didScroll = true;
                        }
                        
                        // Reset de scroll horizontal para mejor visibilidad
                        if (gridContainers[i].scrollLeft > 0) {
                            gridContainers[i].scrollLeft = 0;
                        }
                    }
                }
                
                // Buscar específicamente botones "More"
                var moreButtons = document.querySelectorAll(
                    'button.sapUiTableMoreBtn, span.sapUiTableColShowMoreBtn'
                );
                
                for (var j = 0; j < moreButtons.length; j++) {
                    if (moreButtons[j] && moreButtons[j].offsetParent !== null) {
                        moreButtons[j].click();
                        didScroll = true;
                        break;  // Solo hacer clic en uno por vez
                    }
                }
                
                return didScroll;
            """
            
            did_specific_scroll = self.driver.execute_script(grid_scroll_script)
            
            # Si no se realizó ningún scroll específico, hacer scroll general
            if not did_specific_scroll:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
            return True
        except Exception as e:
            logger.debug(f"Error en scroll de tabla grid: {e}")
            return False

    def _scroll_generic(self):
        """
        Estrategia de scroll genérica para cualquier tipo de tabla o contenido.
        
        Returns:
            bool: True si al menos un método de scroll fue exitoso, False en caso contrario
        """
        try:
            success = False
            
            # 1. Scroll normal al final de la página
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            success = True
            
            # 2. Enviar tecla END para scroll alternativo
            try:
                active_element = self.driver.switch_to.active_element
                active_element.send_keys(Keys.END)
                success = True
            except:
                pass
                
            # 3. Buscar y hacer scroll en cualquier contenedor con capacidad de scroll
            scroll_finder_script = """
                // Identificar todos los elementos con scroll vertical
                var scrollElements = Array.from(document.querySelectorAll('*')).filter(function(el) {
                    var style = window.getComputedStyle(el);
                    return (style.overflowY === 'scroll' || style.overflowY === 'auto') && 
                        el.scrollHeight > el.clientHeight;
                });
                
                var scrolledCount = 0;
                
                // Hacer scroll en cada elemento encontrado
                for (var i = 0; i < scrollElements.length; i++) {
                    var initialScrollTop = scrollElements[i].scrollTop;
                    scrollElements[i].scrollTop = scrollElements[i].scrollHeight;
                    
                    // Verificar si realmente se movió el scroll
                    if (scrollElements[i].scrollTop > initialScrollTop) {
                        scrolledCount++;
                    }
                }
                
                return scrolledCount;
            """
            
            scrolled_count = self.driver.execute_script(scroll_finder_script)
            if scrolled_count > 0:
                success = True
                
            return success
        except Exception as e:
            logger.debug(f"Error en scroll genérico: {e}")
            return False

    def _apply_alternative_scroll_strategy(self, attempt_count):
        """
        Aplica estrategias alternativas de scroll cuando las normales no funcionan.
        
        Args:
            attempt_count (int): Número de intentos previos sin cambios
            
        Returns:
            bool: True si la estrategia alternativa fue aplicada, False en caso contrario
        """
        try:
            # Rotar entre tres estrategias diferentes basadas en el contador de intentos
            strategy = attempt_count % 15
            
            if strategy < 5:
                # Estrategia 1: Scroll progresivo en incrementos
                logger.debug("Aplicando estrategia de scroll progresivo")
                for pos in range(0, 10000, 500):
                    self.driver.execute_script(f"window.scrollTo(0, {pos});")
                    time.sleep(0.1)
                    
            elif strategy < 10:
                # Estrategia 2: Uso de teclas de navegación
                logger.debug("Aplicando estrategia de teclas de navegación")
                try:
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    # Alternar entre Page Down y End para máxima cobertura
                    for i in range(5):
                        body.send_keys(Keys.PAGE_DOWN)
                        time.sleep(0.1)
                        if i % 2 == 0:
                            body.send_keys(Keys.END)
                            time.sleep(0.1)
                except Exception as key_e:
                    logger.debug(f"Error en estrategia de teclas: {key_e}")
                    
            else:
                # Estrategia 3: Buscar y hacer clic en botones de carga
                logger.debug("Buscando botones de carga adicional")
                load_buttons_script = """
                    // Buscar botones de carga por texto y clase
                    var buttons = [];
                    
                    // Por texto
                    var textPatterns = ['More', 'más', 'Show', 'Ver', 'Load', 'Cargar', 'Next', 'Siguiente'];
                    for (var i = 0; i < textPatterns.length; i++) {
                        var pattern = textPatterns[i];
                        var matches = document.evaluate(
                            "//*[contains(text(), '" + pattern + "')]",
                            document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null
                        );
                        
                        for (var j = 0; j < matches.snapshotLength; j++) {
                            var element = matches.snapshotItem(j);
                            if (element.tagName === 'BUTTON' || element.tagName === 'A' || 
                                element.tagName === 'SPAN' || element.tagName === 'DIV') {
                                buttons.push(element);
                            }
                        }
                    }
                    
                    // Por clase
                    var classPatterns = [
                        'sapMListShowMoreButton', 'sapUiTableMoreBtn', 'sapMPaginatorButton',
                        'loadMore', 'showMore', 'moreButton', 'sapMBtn'
                    ];
                    
                    for (var k = 0; k < classPatterns.length; k++) {
                        var elements = document.getElementsByClassName(classPatterns[k]);
                        for (var l = 0; l < elements.length; l++) {
                            buttons.push(elements[l]);
                        }
                    }
                    
                    return buttons;
                """
                
                load_buttons = self.driver.execute_script(load_buttons_script)
                
                if load_buttons:
                    for btn in load_buttons[:3]:  # Limitar a 3 intentos
                        try:
                            # Hacer scroll hasta el botón
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", 
                                btn
                            )
                            time.sleep(0.2)
                            
                            # Intentar clic
                            self.driver.execute_script("arguments[0].click();", btn)
                            logger.info("Se hizo clic en botón de carga adicional")
                            time.sleep(1.5)  # Esperar a que cargue
                            return True
                        except Exception as btn_e:
                            logger.debug(f"Error al hacer clic en botón: {btn_e}")
                            continue
            
            return True
        except Exception as e:
            logger.debug(f"Error en estrategia alternativa de scroll: {e}")
            return False

    def _should_finish_scrolling(self, no_change_count, current_rows_count, total_expected):
        """
        Determina si se debe finalizar el proceso de scroll basado en criterios adaptativos.
        
        Args:
            no_change_count (int): Número de intentos sin cambios en el conteo de filas
            current_rows_count (int): Número actual de filas detectadas
            total_expected (int): Número total esperado de filas
            
        Returns:
            bool: True si se debe finalizar el scroll, False si se debe continuar
        """
        try:
            # Calcular porcentaje de cobertura
            coverage_percentage = (current_rows_count / total_expected * 100) if total_expected > 0 else 0
            
            # Criterio 1: Muchos intentos sin cambios y buena cobertura (≥90%)
            if no_change_count >= 10 and current_rows_count >= total_expected * 0.9:
                logger.info(f"Finalizando scroll: suficiente cobertura ({coverage_percentage:.1f}%, {current_rows_count}/{total_expected})")
                return True
                
            # Criterio 2: Demasiados intentos sin cambios (indicador de que no hay más contenido)
            if no_change_count >= 20:
                logger.info(f"Finalizando scroll: muchos intentos sin cambios ({no_change_count})")
                return True
                
            # Criterio 3: Se superó el total esperado
            if current_rows_count >= total_expected:
                logger.info(f"Finalizando scroll: se alcanzó o superó el total esperado ({current_rows_count}/{total_expected})")
                return True
            
            # Criterio 4: Cobertura muy alta (≥95%) incluso con pocos intentos sin cambios
            if coverage_percentage >= 95 and no_change_count >= 5:
                logger.info(f"Finalizando scroll: cobertura excelente ({coverage_percentage:.1f}%) con {no_change_count} intentos sin cambios")
                return True
                
            # Continuar con el scroll
            return False
        except Exception as e:
            logger.debug(f"Error al evaluar criterios de finalización: {e}")
            return no_change_count > 15  # Criterio de seguridad en caso de error
        








    def _calculate_adaptive_wait_time(self, no_change_count, current_rows_count):
        """
        Calcula un tiempo de espera adaptativo basado en el progreso de carga.
        
        Args:
            no_change_count (int): Número de intentos sin cambios en el conteo de filas
            current_rows_count (int): Número actual de filas detectadas
            
        Returns:
            float: Tiempo de espera en segundos
        """
        try:
            # Base: tiempo corto para maximizar rendimiento
            base_wait = 0.2
            
            # Factor basado en intentos sin cambios (incrementar gradualmente)
            if no_change_count > 0:
                no_change_factor = min(no_change_count * 0.1, 1.0)
            else:
                no_change_factor = 0
                
            # Factor basado en cantidad de filas (más filas = más tiempo para procesar)
            rows_factor = min(current_rows_count / 500, 0.5)
            
            # Calcular tiempo final, con límite máximo de 1 segundo
            wait_time = min(base_wait + no_change_factor + rows_factor, 1.0)
            
            return wait_time
        except Exception as e:
            logger.debug(f"Error al calcular tiempo adaptativo: {e}")
            return 0.5  # Valor por defecto en caso de error

    def click_pagination_next(self, pagination_elements):
        """
        Hace clic en el botón de siguiente página
        
        Args:
            pagination_elements (list): Lista de elementos de paginación
            
        Returns:
            bool: True si se hizo clic con éxito, False en caso contrario
        """
        if not pagination_elements:
            return False
            
        try:
            # Buscar el botón "Next" entre los elementos de paginación
            next_button = None
            
            for element in pagination_elements:
                try:
                    aria_label = element.get_attribute("aria-label") or ""
                    text = element.text.lower()
                    classes = element.get_attribute("class") or ""
                    
                    # Comprobar si es un botón "Next" o "Siguiente"
                    if ("next" in aria_label.lower() or 
                        "siguiente" in aria_label.lower() or
                        "next" in text or 
                        "siguiente" in text or
                        "show more" in text.lower() or
                        "more" in text.lower()):
                        
                        next_button = element
                        break
                        
                    # Comprobar por clase CSS
                    if ("next" in classes.lower() or 
                        "pagination-next" in classes.lower() or
                        "sapMBtn" in classes and "NavButton" in classes):
                        
                        next_button = element
                        break
                except Exception:
                    continue
            
            # Si se encontró un botón Next, intentar hacer clic
            if next_button:
                # Verificar si el botón está habilitado
                disabled = next_button.get_attribute("disabled") == "true" or next_button.get_attribute("aria-disabled") == "true"
                
                if disabled:
                    logger.info("Botón de siguiente página está deshabilitado")
                    return False
                    
                # Scroll hacia el botón para asegurar que está visible
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                time.sleep(0.5)
                
                # Intentar clic con distintos métodos, en orden de preferencia
                try:
                    self.driver.execute_script("arguments[0].click();", next_button)
                    logger.info("Clic en botón 'Next' realizado con JavaScript")
                    time.sleep(2)
                    return True
                except JavascriptException:
                    try:
                        next_button.click()
                        logger.info("Clic en botón 'Next' realizado")
                        time.sleep(2)
                        return True
                    except ElementClickInterceptedException:
                        from selenium.webdriver.common.action_chains import ActionChains
                        actions = ActionChains(self.driver)
                        actions.move_to_element(next_button).click().perform()
                        logger.info("Clic en botón 'Next' realizado con ActionChains")
                        time.sleep(2)
                        return True
            
            # Si no se encontró botón específico, intentar con el último elemento
            if pagination_elements and len(pagination_elements) > 0:
                last_element = pagination_elements[-1]
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", last_element)
                time.sleep(0.5)
                self.driver.execute_script("arguments[0].click();", last_element)
                logger.info("Clic en último elemento de paginación realizado")
                time.sleep(2)
                return True
            
            logger.warning("No se pudo identificar o hacer clic en el botón 'Next'")
            return False
            
        except Exception as e:
            logger.error(f"Error al hacer clic en paginación: {e}")
            return False

    def extract_issues_data(self):
        """
        Extrae datos de issues desde la tabla con procesamiento mejorado
        
        Returns:
            list: Lista de diccionarios con los datos de cada issue
        """
        try:
            logger.info("Iniciando extracción de issues...")
            
            # Esperar a que cargue la página inicial
            time.sleep(3)
            
            header_map = detect_table_headers(self.driver)
            
            # Obtener el número total de issues
            total_issues = self.get_total_issues_count()
            logger.info(f"Total de issues a procesar: {total_issues}")
            
            # Hacer scroll para cargar todos los elementos
            loaded_rows_count = self.scroll_to_load_all_items(total_issues)
            
            # Verificar si hay paginación
            pagination_elements = check_for_pagination(self.driver)
            has_pagination = pagination_elements is not None and len(pagination_elements) > 0
            
            # Lista para almacenar todos los datos extraídos
            all_issues_data = []
            seen_titles = set()  # Solo para registrar, ya no para filtrar duplicados
            
            page_num = 1
            max_pages = 20  # Límite de seguridad
            
            while page_num <= max_pages:
                logger.info(f"Procesando página {page_num}...")
                
                # Obtener filas de la página actual
                rows = find_table_rows(self.driver, highlight=False)
                
                if not rows:
                    logger.warning(f"No se encontraron filas en la página {page_num}")
                    break
                
                logger.info(f"Encontradas {len(rows)} filas en la página {page_num}")
                
                # Procesar filas en esta página
                page_issues_data = self._process_table_rows(rows, seen_titles, header_map)
                
                # Validar y corregir los datos extraídos
                corrected_data = []
                for issue in page_issues_data:
                    corrected_issue = self._validate_and_correct_issue_data(issue)
                    corrected_data.append(corrected_issue)
                
                # Agregar los datos corregidos al resultado total
                all_issues_data.extend(corrected_data)
                
                logger.info(f"Extraídos {len(corrected_data)} issues de la página {page_num}")
                logger.info(f"Total de issues extraídos hasta ahora: {len(all_issues_data)}")
                
                # Si no hay paginación o ya procesamos todos los datos, terminar
                if not has_pagination or len(page_issues_data) == 0:
                    break
                
                # Intentar pasar a la siguiente página
                if pagination_elements:
                    if not self.click_pagination_next(pagination_elements):
                        logger.info("No se pudo pasar a la siguiente página, terminando extracción")
                        break
                        
                    # Esperar a que cargue la nueva página
                    time.sleep(3)
                    
                    # Actualizar elementos de paginación (pueden cambiar entre páginas)
                    pagination_elements = check_for_pagination(self.driver)
                    
                    page_num += 1
                else:
                    break
            
            logger.info(f"Extracción completada. Total de issues extraídos: {len(all_issues_data)}")
            
            return all_issues_data
        
        except Exception as e:
            logger.error(f"Error en la extracción de datos: {e}")
            return []
        
        
        
        
        
        
        
    def _process_table_rows(self, rows, seen_titles, header_map=None):
        """
        Procesa las filas de la tabla y extrae los datos de cada issue
        
        Args:
            rows (list): Lista de filas WebElement
            seen_titles (set): Conjunto de títulos ya procesados
            header_map (dict, optional): Mapeo de nombres de encabezados a índices
            
        Returns:
            list: Lista de diccionarios con datos de issues
        """
        issues_data = []
        processed_count = 0
        batch_size = 10  # Procesar en lotes para actualizar progreso
        
        for index, row in enumerate(rows):
            try:
                # Intentar extracción basada en encabezados si existe un mapeo válido
                if header_map and len(header_map) >= 4:
                    try:
                        issue_data = self._extract_by_headers(row, header_map)
                        if issue_data and issue_data['Title']:
                            # Validar y corregir los datos
                            corrected_issue = self._validate_and_correct_issue_data(issue_data)
                            issues_data.append(corrected_issue)
                            processed_count += 1
                            continue  # Pasar a la siguiente fila
                    except Exception as header_e:
                        logger.debug(f"Error en extracción por encabezados: {header_e}, usando método alternativo")
                
                # Extraer todos los datos en un solo paso para análisis conjunto
                title = self._extract_title(row)
                
                if not title:
                    title = f"Issue sin título #{index+1}"
                
                # Extraer resto de datos
                type_text = self._extract_type(row, title)
                priority = self._extract_priority(row)
                status = self._extract_status(row)
                deadline = self._extract_deadline(row)
                due_date = self._extract_due_date(row)
                created_by = self._extract_created_by(row)
                created_on = self._extract_created_on(row)
                
                # Datos del issue completos
                issue_data = {
                    'Title': title,
                    'Type': type_text,
                    'Priority': priority,
                    'Status': status,
                    'Deadline': deadline,
                    'Due Date': due_date,
                    'Created By': created_by,
                    'Created On': created_on
                }
                
                # Validación especial: verificar si los datos están desplazados
                if type_text == title:
                    logger.warning(f"Posible desplazamiento de columnas detectado en issue '{title}' (Type = Title)")
                    
                    # Intentar extraer directamente por orden de columnas
                    cells = get_row_cells(row)
                    if cells and len(cells) >= 8:
                        # Extraer datos directamente por posición en la tabla
                        issue_data = {
                            'Title': cells[0].text.strip() if cells[0].text else title,
                            'Type': cells[1].text.strip() if len(cells) > 1 and cells[1].text else "",
                            'Priority': cells[2].text.strip() if len(cells) > 2 and cells[2].text else "",
                            'Status': cells[3].text.strip() if len(cells) > 3 and cells[3].text else "",
                            'Deadline': cells[4].text.strip() if len(cells) > 4 and cells[4].text else "",
                            'Due Date': cells[5].text.strip() if len(cells) > 5 and cells[5].text else "",
                            'Created By': cells[6].text.strip() if len(cells) > 6 and cells[6].text else "",
                            'Created On': cells[7].text.strip() if len(cells) > 7 and cells[7].text else ""
                        }
                        logger.info(f"Extracción directa por celdas realizada para issue '{title}'")
                
                # Validar y corregir los datos
                corrected_issue = self._validate_and_correct_issue_data(issue_data)
                
                # Añadir a la lista de resultados
                issues_data.append(corrected_issue)
                processed_count += 1
                
                if processed_count % batch_size == 0:
                    logger.info(f"Procesados {processed_count} issues hasta ahora")
                
            except Exception as e:
                logger.error(f"Error al procesar la fila {index}: {e}")
        
        logger.info(f"Procesamiento de filas completado. Total procesado: {processed_count} issues")
        return issues_data

    def _extract_by_headers(self, row, header_map):
        """
        Extrae datos directamente basado en el mapa de encabezados con mejor control de errores
        
        Args:
            row: WebElement representando una fila
            header_map: Diccionario que mapea nombres de encabezados a índices
            
        Returns:
            dict: Diccionario con los datos extraídos o None si hay error
        """
        try:
            cells = get_row_cells(row)
            if not cells:
                logger.debug("No se encontraron celdas en la fila")
                return None
                    
            # Inicializar diccionario de resultados con valores por defecto
            issue_data = {
                'Title': '',
                'Type': '',
                'Priority': '',
                'Status': '',
                'Deadline': '',
                'Due Date': '',
                'Created By': '',
                'Created On': ''
            }
            
            # Mapeo de nombres de encabezados a claves en nuestro diccionario (más flexible)
            header_mappings = {
                'TITLE': 'Title',
                'TYPE': 'Type',
                'PRIORITY': 'Priority',
                'STATUS': 'Status',
                'DEADLINE': 'Deadline',
                'DUE DATE': 'Due Date',
                'CREATED BY': 'Created By',
                'CREATED ON': 'Created On',
                # Añadir mapeos alternativos para diferentes nomenclaturas
                'NAME': 'Title',
                'ISSUE': 'Title',
                'PRIO': 'Priority',
                'STATE': 'Status',
                'DUE': 'Due Date'
            }
            
            # Extraer valores usando el mapa de encabezados
            for header, index in header_map.items():
                if index < len(cells):
                    # Buscar la clave correspondiente
                    header_upper = header.upper()
                    matched = False
                    
                    # Buscar coincidencias exactas o parciales
                    for pattern, key in header_mappings.items():
                        if pattern == header_upper or pattern in header_upper:
                            cell_text = cells[index].text.strip() if cells[index].text else ''
                            issue_data[key] = cell_text
                            matched = True
                            break
                    
                    # Registrar encabezados no reconocidos
                    if not matched and header_upper:
                        logger.debug(f"Encabezado no reconocido: '{header_upper}'")
                
            # Validación mínima - verificar que al menos tengamos un título
            if not issue_data['Title'] and len(cells) > 0:
                issue_data['Title'] = cells[0].text.strip() if cells[0].text else "Issue sin título"
                    
            return issue_data
        except Exception as e:
            logger.debug(f"Error en extracción por encabezados: {e}")
            return None

    def _extract_title(self, row):
        """
        Extrae el título de una fila
        
        Args:
            row: WebElement representando una fila
            
        Returns:
            str: Título extraído o None si no se encuentra
        """
        try:
            # Intentar múltiples métodos para extraer título
            title_extractors = [
                lambda r: r.find_element(By.XPATH, ".//a").text,
                lambda r: r.find_element(By.XPATH, ".//span[contains(@class, 'title')]").text,
                lambda r: r.find_element(By.XPATH, ".//div[contains(@class, 'title')]").text,
                lambda r: r.find_elements(By.XPATH, ".//div[@role='gridcell']")[0].text if r.find_elements(By.XPATH, ".//div[@role='gridcell']") else None,
                lambda r: r.find_elements(By.XPATH, ".//td")[0].text if r.find_elements(By.XPATH, ".//td") else None,
                lambda r: r.find_element(By.XPATH, ".//*[contains(@id, 'title')]").text,
                lambda r: r.find_element(By.XPATH, ".//div[@title]").get_attribute("title"),
                lambda r: r.find_element(By.XPATH, ".//span[@title]").get_attribute("title")
            ]

            for extractor in title_extractors:
                try:
                    title_text = extractor(row)
                    if title_text and title_text.strip():
                        return title_text.strip()
                except:
                    continue
            
            # Si no encontramos un título específico, usar el texto completo
            try:
                full_text = row.text.strip()
                if full_text:
                    lines = full_text.split('\n')
                    if lines:
                        title = lines[0].strip()
                        if len(title) > 100:  # Si es muy largo, recortar
                            title = title[:100] + "..."
                        return title
            except:
                pass
                
            return None
        except Exception as e:
            logger.debug(f"Error al extraer título: {e}")
            return None
            
    def _extract_type(self, row, title):
        """
        Extrae correctamente el tipo de issue
        
        Args:
            row: WebElement representando una fila
            title: Título ya extraído para comparación
            
        Returns:
            str: Tipo de issue o cadena vacía si no se encuentra
        """
        try:
            # Buscar con mayor precisión el tipo
            cells = get_row_cells(row)
            
            # Verificar si tenemos suficientes celdas
            if cells and len(cells) >= 2:
                # Extraer de la segunda celda, pero verificar que no sea igual al título
                type_text = cells[1].text.strip()
                
                # Si el tipo es igual al título, algo está mal, buscar en otra parte
                if type_text and type_text != title:
                    return type_text
            
            # Intentos alternativos para obtener el tipo
            # Buscar elementos específicos con clases o atributos que indiquen tipo
            type_elements = row.find_elements(By.XPATH, ".//span[contains(@class, 'type')] | .//div[contains(@class, 'type')]")
            for el in type_elements:
                if el.text and el.text.strip() and el.text.strip() != title:
                    return el.text.strip()
            
            # Intentar con selectores UI5 específicos como último recurso
            ui5_types = find_ui5_elements(self.driver, "sap.m.Label", {"text": "Type"})
            for type_label in ui5_types:
                try:
                    value_element = self.driver.find_element(By.XPATH, f"./following-sibling::*[1]")
                    if value_element and value_element.text and value_element.text.strip() != title:
                        return value_element.text.strip()
                except:
                    pass
                    
            # Si no encontramos nada, devolver vacío
            return ""
        except Exception as e:
            logger.debug(f"Error al extraer tipo: {e}")
            return ""
        
        
        
        
        

    def _extract_priority(self, row):
        """
        Extrae la prioridad del issue
        
        Args:
            row: WebElement representando una fila
            
        Returns:
            str: Prioridad del issue o cadena vacía si no se encuentra
        """
        try:
            # Buscar específicamente en la tercera columna 
            cells = get_row_cells(row)
            if cells and len(cells) >= 3:
                priority_text = cells[2].text.strip()
                if priority_text:
                    return self._normalize_priority(priority_text)
            
            # Intentos alternativos
            priority_indicators = [
                # Por clase de color
                (By.XPATH, ".//span[contains(@class, 'sapMGaugeNegativeColor')]", "Very High"),
                (By.XPATH, ".//span[contains(@class, 'sapMGaugeCriticalColor')]", "High"),
                (By.XPATH, ".//span[contains(@class, 'sapMGaugeNeutralColor')]", "Medium"),
                (By.XPATH, ".//span[contains(@class, 'sapMGaugePositiveColor')]", "Low"),
                
                # Por texto
                (By.XPATH, ".//span[contains(text(), 'Very High')]", "Very High"),
                (By.XPATH, ".//span[contains(text(), 'High') and not(contains(text(), 'Very'))]", "High"),
                (By.XPATH, ".//span[contains(text(), 'Medium')]", "Medium"),
                (By.XPATH, ".//span[contains(text(), 'Low')]", "Low")
            ]
            
            # Buscar indicadores visuales de prioridad
            for locator, indicator_text in priority_indicators:
                elements = row.find_elements(locator)
                if elements:
                    return indicator_text
            
            # Buscar por etiquetas o campos específicos
            priority_labels = row.find_elements(By.XPATH, 
                ".//div[contains(text(), 'Priority')]/following-sibling::*[1] | " +
                ".//span[contains(text(), 'Priority')]/following-sibling::*[1]")
            if priority_labels:
                for label in priority_labels:
                    if label.text:
                        return self._normalize_priority(label.text)
            
            # Verificar por los valores específicos en cualquier lugar de la fila
            for priority_value in ["Very High", "High", "Medium", "Low"]:
                elements = row.find_elements(By.XPATH, f".//*[contains(text(), '{priority_value}')]")
                if elements:
                    return priority_value
                    
            return ""
        except Exception as e:
            logger.debug(f"Error al extraer prioridad: {e}")
            return ""
            
    def _normalize_priority(self, priority_text):
        """
        Normaliza el texto de prioridad
        
        Args:
            priority_text (str): Texto crudo de prioridad
            
        Returns:
            str: Prioridad normalizada
        """
        if not priority_text:
            return ""
            
        priority_lower = priority_text.lower()
        
        if "very high" in priority_lower:
            return "Very High"
        elif "high" in priority_lower:
            return "High"
        elif "medium" in priority_lower:
            return "Medium"
        elif "low" in priority_lower:
            return "Low"
        
        return priority_text

    def _extract_status(self, row):
        """
        Extrae el estado del issue
        
        Args:
            row: WebElement representando una fila
            
        Returns:
            str: Estado del issue o cadena vacía si no se encuentra
        """
        try:
            # Buscar específicamente en la cuarta columna
            cells = get_row_cells(row)
            if cells and len(cells) >= 4:
                status_text = cells[3].text.strip()
                if status_text:
                    # Limpiar y extraer solo la primera línea si hay varias
                    status_lines = status_text.split("\n")
                    status = status_lines[0].strip()
                    status = status.replace("Object Status", "").strip()
                    return self._normalize_status(status)
            
            # Buscar por estados conocidos de SAP
            status_patterns = ["OPEN", "DONE", "IN PROGRESS", "READY", "ACCEPTED", "DRAFT"]
            for status in status_patterns:
                elements = row.find_elements(By.XPATH, f".//*[contains(text(), '{status}')]")
                if elements:
                    return status
                    
            # Buscar por etiquetas o campos específicos
            status_labels = row.find_elements(By.XPATH, 
                ".//div[contains(text(), 'Status')]/following-sibling::*[1] | " +
                ".//span[contains(text(), 'Status')]/following-sibling::*[1]")
            if status_labels:
                for label in status_labels:
                    if label.text:
                        return self._normalize_status(label.text.strip())
                        
            return ""
        except Exception as e:
            logger.debug(f"Error al extraer estado: {e}")
            return ""
        
    def _normalize_status(self, status_text):
        """
        Normaliza el texto de estado
        
        Args:
            status_text (str): Texto crudo de estado
            
        Returns:
            str: Estado normalizado
        """
        if not status_text:
            return ""
            
        status_upper = status_text.upper()
        
        if "OPEN" in status_upper:
            return "OPEN"
        elif "DONE" in status_upper:
            return "DONE"
        elif "IN PROGRESS" in status_upper:
            return "IN PROGRESS"
        elif "READY" in status_upper:
            return "READY FOR PUBLISHING" if "PUBLISH" in status_upper else "READY"
        elif "ACCEPTED" in status_upper:
            return "ACCEPTED"
        elif "DRAFT" in status_upper:
            return "DRAFT"
        elif "CLOSED" in status_upper:
            return "CLOSED"
        
        return status_text
        
    def _extract_deadline(self, row):
        """
        Extrae la fecha límite del issue
        
        Args:
            row: WebElement representando una fila
            
        Returns:
            str: Fecha límite o cadena vacía si no se encuentra
        """
        try:
            # Buscar específicamente en la quinta columna
            cells = get_row_cells(row)
            if cells and len(cells) >= 5:
                deadline_text = cells[4].text.strip()
                if deadline_text and any(month in deadline_text for month in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]):
                    return deadline_text
            
            # Buscar por formato de fecha
            date_elements = row.find_elements(By.XPATH, ".//*[contains(text(), '/') or contains(text(), '-') or contains(text(), 'day,')]")
            for el in date_elements:
                # Verificar si parece una fecha por formato o contenido
                text = el.text.strip()
                if text and any(month in text for month in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]):
                    # Verificar que no sea la fecha "Created On"
                    parent_text = ""
                    try:
                        parent = el.find_element(By.XPATH, "./parent::*")
                        parent_text = parent.text
                    except:
                        pass
                    
                    if "created" not in parent_text.lower() and "due" not in parent_text.lower():
                        return text
                        
            # Buscar por etiquetas específicas
            deadline_labels = row.find_elements(By.XPATH, 
                ".//div[contains(text(), 'Deadline')]/following-sibling::*[1] | " +
                ".//span[contains(text(), 'Deadline')]/following-sibling::*[1]")
            if deadline_labels:
                for label in deadline_labels:
                    if label.text:
                        return label.text.strip()
                        
            return ""
        except Exception as e:
            logger.debug(f"Error al extraer deadline: {e}")
            return ""
        
        
        
        
        
        
        
        
        
        
        
        
    def _extract_due_date(self, row):
        """
        Extrae la fecha de vencimiento del issue
        
        Args:
            row: WebElement representando una fila
            
        Returns:
            str: Fecha de vencimiento o cadena vacía si no se encuentra
        """
        try:
            # Buscar específicamente en la sexta columna
            cells = get_row_cells(row)
            if cells and len(cells) >= 6:
                due_date_text = cells[5].text.strip()
                if due_date_text and any(month in due_date_text for month in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]):
                    return due_date_text
            
            # Buscar por etiquetas específicas
            due_date_labels = row.find_elements(By.XPATH, 
                ".//div[contains(text(), 'Due') or contains(text(), 'Due Date')]/following-sibling::*[1] | " +
                ".//span[contains(text(), 'Due') or contains(text(), 'Due Date')]/following-sibling::*[1]")
            if due_date_labels:
                for label in due_date_labels:
                    if label.text:
                        return label.text.strip()
            
            # Última posibilidad: buscar fechas que no sean deadline ni created on
            date_elements = row.find_elements(By.XPATH, ".//*[contains(text(), '/') or contains(text(), '-') or contains(text(), 'day,')]")
            if len(date_elements) >= 2:  # Si hay al menos 2 fechas, la segunda podría ser due date
                return date_elements[1].text.strip()
                
            return ""
        except Exception as e:
            logger.debug(f"Error al extraer due date: {e}")
            return ""
                
    def _extract_created_by(self, row):
        """
        Extrae quién creó el issue
        
        Args:
            row: WebElement representando una fila
            
        Returns:
            str: Creador del issue o cadena vacía si no se encuentra
        """
        try:
            # Buscar específicamente en la séptima columna
            cells = get_row_cells(row)
            if cells and len(cells) >= 7:
                created_by_text = cells[6].text.strip()
                # Verificar que no sea una fecha (para evitar confusión con otras columnas)
                if created_by_text and not any(month in created_by_text for month in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]):
                    return created_by_text
            
            # Buscar por etiquetas específicas
            created_by_labels = row.find_elements(By.XPATH, 
                ".//div[contains(text(), 'Created By')]/following-sibling::*[1] | " +
                ".//span[contains(text(), 'Created By')]/following-sibling::*[1]")
            if created_by_labels:
                for label in created_by_labels:
                    if label.text:
                        return label.text.strip()
                        
            # Buscar elementos que parecen ser usuarios (con formato de ID)
            user_patterns = row.find_elements(By.XPATH, ".//*[contains(text(), 'I') and string-length(text()) <= 8]")
            if user_patterns:
                for user in user_patterns:
                    user_text = user.text.strip()
                    # Si parece un ID de usuario de SAP (como I587465)
                    if user_text.startswith("I") and user_text[1:].isdigit():
                        return user_text
                        
            return ""
        except Exception as e:
            logger.debug(f"Error al extraer creador: {e}")
            return ""
                
    def _extract_created_on(self, row):
        """
        Extrae la fecha de creación del issue
        
        Args:
            row: WebElement representando una fila
            
        Returns:
            str: Fecha de creación o cadena vacía si no se encuentra
        """
        try:
            # Buscar específicamente en la octava columna
            cells = get_row_cells(row)
            if cells and len(cells) >= 8:
                created_on_text = cells[7].text.strip()
                if created_on_text and any(month in created_on_text for month in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]):
                    return created_on_text
            
            # Buscar por etiquetas específicas
            created_on_labels = row.find_elements(By.XPATH, 
                ".//div[contains(text(), 'Created On')]/following-sibling::*[1] | " +
                ".//span[contains(text(), 'Created On')]/following-sibling::*[1]")
            if created_on_labels:
                for label in created_on_labels:
                    if label.text:
                        return label.text.strip()
            
            # Buscar la última fecha disponible que podría ser la fecha de creación
            date_elements = row.find_elements(By.XPATH, ".//*[contains(text(), '/') or contains(text(), '-') or contains(text(), 'day,')]")
            if date_elements and len(date_elements) >= 3:  # Si hay al menos 3 fechas, la última podría ser created on
                return date_elements[-1].text.strip()
                
            return ""
        except Exception as e:
            logger.debug(f"Error al extraer fecha de creación: {e}")
            return ""        

    def _validate_and_correct_issue_data(self, issue_data):
        """
        Valida y corrige los datos del issue antes de guardarlos
        
        Args:
            issue_data (dict): Diccionario con datos del issue
            
        Returns:
            dict: Diccionario con datos validados y corregidos
        """
        # Asegurar que todos los campos esperados estén presentes
        required_fields = ['Title', 'Type', 'Priority', 'Status', 'Deadline', 'Due Date', 'Created By', 'Created On']
        for field in required_fields:
            if field not in issue_data:
                issue_data[field] = ""
        
        # Validación y corrección contextual de los campos
        
        # 1. Verificar que Type no duplique el Title
        if issue_data['Type'] == issue_data['Title']:
            issue_data['Type'] = ""
        
        # 2. Verificar Status - debería contener palabras clave como "OPEN", "DONE", etc.
        if issue_data['Status']:
            status_keywords = ["OPEN", "DONE", "IN PROGRESS", "READY", "ACCEPTED", "DRAFT", "CLOSED"]
            if not any(keyword in issue_data['Status'].upper() for keyword in status_keywords):
                # Si Status no parece un status válido, verificar otros campos
                for field in ['Priority', 'Type', 'Deadline']:
                    if field in issue_data and issue_data[field]:
                        field_value = issue_data[field].upper()
                        if any(keyword in field_value for keyword in status_keywords):
                            # Intercambiar valores
                            temp = issue_data['Status']
                            issue_data['Status'] = issue_data[field]
                            issue_data[field] = temp
                            break
        
        # 3. Verificar prioridad - debería ser "High", "Medium", "Low", etc.
        if issue_data['Priority']:
            priority_keywords = ["HIGH", "MEDIUM", "LOW", "VERY HIGH"]
            if not any(keyword in issue_data['Priority'].upper() for keyword in priority_keywords):
                # Si Priority no parece una prioridad válida, verificar otros campos
                for field in ['Type', 'Status']:
                    if field in issue_data and issue_data[field]:
                        field_value = issue_data[field].upper()
                        if any(keyword in field_value for keyword in priority_keywords):
                            # Intercambiar valores
                            temp = issue_data['Priority']
                            issue_data['Priority'] = issue_data[field]
                            issue_data[field] = temp
                            break
        
        # 4. Verificar que Deadline, Due Date y Created On parezcan fechas
        date_fields = ['Deadline', 'Due Date', 'Created On']
        date_keywords = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
        
        for date_field in date_fields:
            if date_field in issue_data and issue_data[date_field]:
                # Verificar si parece una fecha
                if not any(month in issue_data[date_field].upper() for month in date_keywords):
                    # No parece una fecha, buscar en otros campos que no son fechas
                    for field in ['Status', 'Priority', 'Type']:
                        if field in issue_data and issue_data[field]:
                            field_value = issue_data[field].upper()
                            if any(month in field_value for month in date_keywords):
                                # Intercambiar valores
                                temp = issue_data[date_field]
                                issue_data[date_field] = issue_data[field]
                                issue_data[field] = temp
                                break
        
        # 5. Created By debería parecer un ID de usuario (no una fecha o un status)
        if issue_data['Created By']:
            if any(month in issue_data['Created By'].upper() for month in date_keywords):
                # Parece una fecha, buscar un mejor valor para Created By
                for field in date_fields:
                    if field in issue_data and not issue_data[field]:
                        # Si encontramos un campo de fecha vacío, mover Created By allí
                        issue_data[field] = issue_data['Created By']
                        issue_data['Created By'] = ""
                        break
        
        # 6. Verificar inconsistencia de desplazamiento general
        # Si detectamos un patrón de desplazamiento, corregirlo
        if (issue_data['Type'] == issue_data['Title'] and 
            issue_data['Priority'] == issue_data['Type'] and 
            issue_data['Status'] == issue_data['Priority']):
            
            # Desplazar todos los campos a la izquierda
            issue_data['Type'] = issue_data['Priority']
            issue_data['Priority'] = issue_data['Status']
            issue_data['Status'] = issue_data['Deadline']
            issue_data['Deadline'] = issue_data['Due Date']
            issue_data['Due Date'] = issue_data['Created By']
            issue_data['Created By'] = issue_data['Created On']
            issue_data['Created On'] = ""
        
        return issue_data











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



















    def configure_table_columns(self):
        """
        Configura las columnas de la tabla seleccionando todas las disponibles.
        Esta función debe llamarse después de abrir el panel de ajustes.
        
        Returns:
            bool: True si la configuración fue exitosa, False en caso contrario
        """
        try:
            logger.info("Configurando columnas de la tabla para maximizar extracción de datos...")
            
            # 1. Hacer clic en la pestaña "Select Columns" (tercer ícono)
            if not self._click_select_columns_tab():
                logger.error("No se pudo hacer clic en la pestaña 'Select Columns'")
                return False
                
            # 2. Marcar la opción "Select All"
            if not self._click_select_all_checkbox():
                logger.error("No se pudo marcar la opción 'Select All'")
                return False
                
            # 3. Confirmar con OK
            if not self._confirm_selection():
                logger.error("No se pudo confirmar la selección con OK")
                return False
            
            logger.info("✅ Configuración de columnas completada exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al configurar columnas de tabla: {e}")
            return False

    def select_all_visible_columns(self):
        """
        Proceso completo para seleccionar todas las columnas visibles:
        1. Abre el panel de ajustes
        2. Configura todas las columnas
        
        Returns:
            bool: True si el proceso fue exitoso, False en caso contrario
        """
        try:
            logger.info("Iniciando proceso de selección de todas las columnas visibles...")
            
            # 1. Verificar si ya estamos en el panel de ajustes
            settings_open = self._verify_settings_panel_opened()
            
            # 2. Si no está abierto, abrir el panel de ajustes
            if not settings_open:
                logger.info("El panel de ajustes no está abierto, intentando abrir...")
                if hasattr(self, 'click_settings_button') and callable(getattr(self, 'click_settings_button')):
                    settings_open = self.click_settings_button()
                    
                    if not settings_open and hasattr(self, 'force_open_settings'):
                        logger.info("Intentando método alternativo para abrir ajustes...")
                        settings_open = self.force_open_settings()
                        
                if not settings_open:
                    logger.error("No se pudo abrir el panel de ajustes")
                    return False
                    
                # Esperar a que se abra completamente el panel
                time.sleep(2)
            
            # 3. Configurar las columnas visibles
            result = self.configure_table_columns()
            
            if result:
                logger.info("✅ Proceso de selección de columnas completado exitosamente")
            else:
                logger.warning("❌ Proceso de selección de columnas fallido")
                
            return result
            
        except Exception as e:
            logger.error(f"Error en proceso de selección de columnas: {e}")
            return False

    def _verify_settings_panel_opened(self):
        """
        Verifica si el panel de ajustes está abierto
        
        Returns:
            bool: True si el panel está abierto, False en caso contrario
        """
        try:
            # Esperamos un momento para que se cargue el panel si se acaba de abrir
            time.sleep(1)
            
            # Selectores para el panel de ajustes
            panel_selectors = [
                "//div[contains(@class, 'sapMDialog') and contains(@class, 'sapMPopup-CTX')]",
                "//div[contains(@class, 'sapMPopover') and contains(@class, 'sapMPopup-CTX')]",
                "//div[contains(text(), 'View Settings')]/ancestor::div[contains(@class, 'sapMDialogTitle')]",
                "//span[contains(text(), 'View Settings')]/ancestor::div[contains(@class, 'sapMDialog')]"
            ]
            
            # Buscar el panel con los selectores
            for selector in panel_selectors:
                elements = self.driver.find_elements(By.XPATH, selector)
                if elements and any(element.is_displayed() for element in elements):
                    logger.debug("Panel de ajustes detectado correctamente")
                    return True
            
            # Verificación adicional con JavaScript
            js_check = """
            return (function() {
                // Verificar diálogos visibles
                var dialogs = document.querySelectorAll('.sapMDialog, .sapMPopover');
                for (var i = 0; i < dialogs.length; i++) {
                    if (dialogs[i].offsetParent !== null) {
                        // Buscar título de configuración
                        var titleElements = dialogs[i].querySelectorAll('.sapMDialogTitle, .sapMTitle');
                        for (var j = 0; j < titleElements.length; j++) {
                            if (titleElements[j].textContent.includes('Settings') || 
                                titleElements[j].textContent.includes('View')) {
                                return true;
                            }
                        }
                        // Si hay algún diálogo visible con los íconos de columnas
                        var columnIcons = dialogs[i].querySelectorAll('.sapMTBShrinkItem');
                        if (columnIcons.length >= 3) { // Al menos 3 íconos
                            return true;
                        }
                    }
                }
                return false;
            })();
            """
            
            panel_detected = self.driver.execute_script(js_check)
            if panel_detected:
                logger.debug("Panel de ajustes detectado mediante JavaScript")
                return True
            
            logger.debug("No se detectó panel de ajustes abierto")
            return False
            
        except Exception as e:
            logger.error(f"Error al verificar panel de ajustes: {e}")
            return False

    def _click_select_columns_tab(self):
        """
        Hace clic en la pestaña "Select Columns" (tercer ícono)
        
        Returns:
            bool: True si el clic fue exitoso, False en caso contrario
        """
        try:
            logger.info("Intentando hacer clic en la pestaña 'Select Columns'...")
            
            # El tercer ícono suele corresponder a "Select Columns"
            # Intentaremos varios selectores para localizarlo
            
            # 1. Verificar si hay íconos de navegación visibles
            tab_selectors = [
                # Por posición (tercer ícono)
                "(//div[contains(@class, 'sapMDialogTitle')]/following-sibling::div//button)[3]",
                "(//div[contains(@class, 'sapMSegBBtn')])[3]",
                "(//div[contains(@class, 'sapMITBHead')]//div[contains(@class, 'sapMITBItem')])[3]",
                
                # Por ícono específico
                "//span[contains(@data-sap-ui, 'column') or contains(@data-sap-ui, 'table')]/ancestor::button",
                "//button[contains(@title, 'Column') or contains(@aria-label, 'Column')]",
                
                # Por contenedor específico
                "//div[contains(@class, 'sapMSegBBtnSel')]/following-sibling::div[2]",
                
                # Específico para el ícono de columnas
                "//span[contains(@class, 'sapUiIcon') and contains(@data-sap-ui, 'table-column')]/ancestor::button",
                "//span[contains(@class, 'sapUiIcon') and contains(@data-sap-ui, 'column')]/ancestor::button"
            ]
            
            # Intentar cada selector
            for selector in tab_selectors:
                elements = self.driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        # Scroll para asegurar visibilidad
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                        time.sleep(0.5)
                        
                        # Intentar clic con JavaScript
                        try:
                            self.driver.execute_script("arguments[0].click();", element)
                            logger.info("Clic en pestaña 'Select Columns' realizado con JavaScript")
                            time.sleep(1)
                            return True
                        except Exception as js_e:
                            logger.debug(f"Error en clic JavaScript: {js_e}")
                            try:
                                # Intentar clic normal
                                element.click()
                                logger.info("Clic en pestaña 'Select Columns' realizado con método normal")
                                time.sleep(1)
                                return True
                            except Exception as click_e:
                                logger.debug(f"Error en clic normal: {click_e}")
            
            # Si fallaron todos los selectores, intentar con JavaScript específico
            js_click_column_tab = """
            return (function() {
                // Buscar el panel de ajustes
                var dialogs = document.querySelectorAll('.sapMDialog, .sapMPopover');
                
                for (var i = 0; i < dialogs.length; i++) {
                    if (dialogs[i].offsetParent === null) continue; // No visible
                    
                    // Buscar todos los botones en el diálogo
                    var buttons = dialogs[i].querySelectorAll('button, .sapMSegBBtn');
                    
                    // Si hay al menos 3 botones, hacer clic en el tercero
                    if (buttons.length >= 3) {
                        buttons[2].click();
                        return true;
                    }
                    
                    // Buscar por ícono específico
                    var columnIcons = dialogs[i].querySelectorAll('.sapUiIcon');
                    for (var j = 0; j < columnIcons.length; j++) {
                        var iconData = columnIcons[j].getAttribute('data-sap-ui') || '';
                        if (iconData.includes('column') || iconData.includes('table')) {
                            // Buscar botón padre
                            var parentButton = columnIcons[j].closest('button') || 
                                            columnIcons[j].closest('.sapMSegBBtn');
                            if (parentButton) {
                                parentButton.click();
                                return true;
                            }
                        }
                    }
                }
                return false;
            })();
            """
            
            result = self.driver.execute_script(js_click_column_tab)
            if result:
                logger.info("Clic en pestaña 'Select Columns' realizado con JavaScript específico")
                time.sleep(1)
                return True
                
            logger.warning("No se pudo hacer clic en la pestaña 'Select Columns'")
            return False
            
        except Exception as e:
            logger.error(f"Error al hacer clic en pestaña 'Select Columns': {e}")
            return False

    def _click_select_all_checkbox(self):
        """
        Hace clic en la opción "Select All" para seleccionar todas las columnas
        
        Returns:
            bool: True si el clic fue exitoso, False en caso contrario
        """
        try:
            logger.info("Intentando hacer clic en 'Select All'...")
            
            # Esperar a que aparezca el panel de columnas
            time.sleep(1)
            
            # Selectores para el checkbox "Select All"
            select_all_selectors = [
                # Por texto exacto
                "//div[normalize-space(text())='Select All']/preceding-sibling::div//input[@type='checkbox']",
                "//div[normalize-space(text())='Select All']/preceding-sibling::div",
                "//span[normalize-space(text())='Select All']/preceding-sibling::span//input[@type='checkbox']",
                
                # Por texto aproximado
                "//div[contains(text(), 'Select All')]/preceding-sibling::div",
                "//span[contains(text(), 'Select All')]/preceding-sibling::span",
                
                # Por posición (primer checkbox en la lista)
                "(//input[@type='checkbox'])[1]",
                "(//div[contains(@class, 'sapMCb')])[1]",
                
                # Por clase específica del "Select All"
                "//div[contains(@class, 'sapMCbLabel') and contains(text(), 'Select All')]/preceding-sibling::div",
                "//div[contains(@class, 'SelectAll')]/input[@type='checkbox']"
            ]
            
            # Intentar cada selector
            for selector in select_all_selectors:
                elements = self.driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed():
                        # Scroll para asegurar visibilidad
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                        time.sleep(0.5)
                        
                        # Intentar clic
                        try:
                            self.driver.execute_script("arguments[0].click();", element)
                            logger.info("Clic en 'Select All' realizado con JavaScript")
                            time.sleep(0.5)
                            return True
                        except Exception as js_e:
                            logger.debug(f"Error en clic JavaScript: {js_e}")
                            try:
                                element.click()
                                logger.info("Clic en 'Select All' realizado con método normal")
                                time.sleep(0.5)
                                return True
                            except Exception as click_e:
                                logger.debug(f"Error en clic normal: {click_e}")
            
            # Método alternativo usando JavaScript para buscar y hacer clic
            js_click_select_all = """
            return (function() {
                // Buscar por texto
                var selectAllText = document.evaluate(
                    "//div[contains(text(), 'Select All')] | //span[contains(text(), 'Select All')]",
                    document,
                    null,
                    XPathResult.FIRST_ORDERED_NODE_TYPE,
                    null
                ).singleNodeValue;
                
                if (selectAllText) {
                    // Buscar el elemento checkbox asociado
                    var checkbox = null;
                    
                    // Método 1: Buscar en el elemento hermano anterior
                    var parent = selectAllText.parentElement;
                    if (parent && parent.previousElementSibling) {
                        checkbox = parent.previousElementSibling.querySelector('input[type="checkbox"]') ||
                                parent.previousElementSibling;
                    }
                    
                    // Método 2: Buscar por proximidad
                    if (!checkbox) {
                        checkbox = selectAllText.closest('.sapMCb') || 
                                selectAllText.previousElementSibling;
                    }
                    
                    // Si encontramos un elemento, hacer clic
                    if (checkbox) {
                        checkbox.click();
                        return true;
                    }
                }
                
                // Estrategia alternativa: hacer clic en el primer checkbox de la lista
                var checkboxes = document.querySelectorAll('input[type="checkbox"], .sapMCb');
                if (checkboxes.length > 0) {
                    checkboxes[0].click();
                    return true;
                }
                
                return false;
            })();
            """
            
            result = self.driver.execute_script(js_click_select_all)
            if result:
                logger.info("Clic en 'Select All' realizado con JavaScript específico")
                time.sleep(0.5)
                return True
                
            logger.warning("No se pudo hacer clic en 'Select All'")
            return False
            
        except Exception as e:
            logger.error(f"Error al hacer clic en 'Select All': {e}")
            return False

    def _confirm_selection(self):
        """
        Confirma la selección haciendo clic en el botón OK o usando Ctrl+Enter
        
        Returns:
            bool: True si la confirmación fue exitosa, False en caso contrario
        """
        try:
            logger.info("Intentando confirmar selección de columnas...")
            
            # Intentar primero con el botón OK
            ok_button_selectors = [
                "//button[contains(@class, 'sapMDialogOkButton') or contains(text(), 'OK')]",
                "//div[contains(@class, 'sapMBarRight')]//button[contains(@class, 'sapMBtn') and (contains(text(), 'OK') or contains(@aria-label, 'OK'))]",
                "//footer//button[contains(text(), 'OK')]",
                "//button[@title='OK' or @aria-label='OK']",
                "//div[contains(@class, 'sapMDialogFooter')]//button[contains(text(), 'OK')]"
            ]
            
            # Intentar cada selector
            for selector in ok_button_selectors:
                elements = self.driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        # Scroll para asegurar visibilidad
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                        time.sleep(0.5)
                        
                        # Intentar clic
                        try:
                            self.driver.execute_script("arguments[0].click();", element)
                            logger.info("Clic en botón 'OK' realizado con JavaScript")
                            time.sleep(1)  # Esperar a que se procese la acción
                            return True
                        except Exception as js_e:
                            logger.debug(f"Error en clic JavaScript: {js_e}")
                            try:
                                element.click()
                                logger.info("Clic en botón 'OK' realizado con método normal")
                                time.sleep(1)
                                return True
                            except Exception as click_e:
                                logger.debug(f"Error en clic normal: {click_e}")
            
            # Si falló el clic en OK, intentar con Ctrl+Enter
            logger.info("Intentando confirmar con Ctrl+Enter...")
            try:
                # Encontrar cualquier elemento enfocable dentro del diálogo
                focusable_elements = self.driver.find_elements(By.XPATH, 
                    "//div[contains(@class, 'sapMDialog')]//input | //div[contains(@class, 'sapMDialog')]//button")
                
                if focusable_elements:
                    # Hacemos clic en el elemento para asegurar el foco
                    focusable_elements[0].click()
                    time.sleep(0.5)
                    
                    # Enviamos Ctrl+Enter
                    actions = ActionChains(self.driver)
                    actions.key_down(Keys.CONTROL).send_keys(Keys.RETURN).key_up(Keys.CONTROL).perform()
                    logger.info("Combinación Ctrl+Enter enviada")
                    time.sleep(1)
                    return True
                else:
                    # Si no encontramos elementos, intentar en el cuerpo del diálogo
                    dialog_body = self.driver.find_element(By.XPATH, "//div[contains(@class, 'sapMDialog')]")
                    dialog_body.click()
                    time.sleep(0.5)
                    
                    # Enviamos Ctrl+Enter
                    actions = ActionChains(self.driver)
                    actions.key_down(Keys.CONTROL).send_keys(Keys.RETURN).key_up(Keys.CONTROL).perform()
                    logger.info("Combinación Ctrl+Enter enviada al cuerpo del diálogo")
                    time.sleep(1)
                    return True
            except Exception as key_e:
                logger.debug(f"Error al enviar Ctrl+Enter: {key_e}")
            
            # Último recurso: JavaScript para buscar y hacer clic en OK
            js_click_ok = """
            return (function() {
                // Buscar todos los botones en diálogos
                var dialogButtons = Array.from(document.querySelectorAll('.sapMDialog button, .sapMPopover button'))
                    .filter(function(btn) {
                        return btn.offsetParent !== null; // Visible
                    });
                
                // Buscar específicamente botones con texto "OK"
                var okButton = dialogButtons.find(function(btn) {
                    return btn.textContent.trim() === 'OK' || 
                        btn.getAttribute('aria-label') === 'OK' ||
                        btn.getAttribute('title') === 'OK';
                });
                
                if (okButton) {
                    okButton.click();
                    return true;
                }
                
                // Si no encontramos botón OK, buscar botones en el pie de diálogo
                var footerButtons = document.querySelectorAll('.sapMDialogFooter button, .sapMIBar button');
                if (footerButtons.length > 0) {
                    // El botón de confirmación suele ser el último
                    footerButtons[footerButtons.length - 1].click();
                    return true;
                }
                
                return false;
            })();
            """
            
            result = self.driver.execute_script(js_click_ok)
            if result:
                logger.info("Clic en 'OK' realizado con JavaScript específico")
                time.sleep(1)
                return True
                
            logger.warning("No se pudo confirmar la selección de columnas")
            return False
            
        except Exception as e:
            logger.error(f"Error al confirmar selección: {e}")
            return False
