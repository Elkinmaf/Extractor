"""

Módulo principal para la automatización del navegador con Selenium.

Proporciona funcionalidades específicas para interactuar con aplicaciones SAP UI5/Fiori.

"""



import os
import time
import logging
import re
import time



from datetime import datetime

import tkinter as tk

from tkinter import messagebox

from typing import Optional, List, Dict, Union, Tuple



# Importaciones de Selenium

from selenium import webdriver

from selenium.webdriver.chrome.service import Service

import time
import logging


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
from config.settings import BROWSER_TIMEOUT



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
            logger.errorcls(f"Error durante la navegación por teclado: {e}")
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













    def click_select_columns_button(driver):

        """

        Hace clic en el botón 'Select Columns' usando Selenium.

        

        Args:

            driver: WebDriver de Selenium.

            

        Returns:

            bool: True si el clic fue exitoso, False en caso contrario.

        """

        try:

            # Esperar a que el elemento esté presente

            time.sleep(2)  # Espera estática para asegurar que el panel de ajustes se cargue



            # Usar el selector XPath proporcionado

            select_columns_button = driver.find_element(By.XPATH, "//*[@id='application-iam-ui-component---home--issuesColumns-img']")

            

            # Usar JavaScript para hacer clic (más confiable en SAP UI5)

            driver.execute_script("arguments[0].click();", select_columns_button)

            logger.info("Clic en botón 'Select Columns' realizado con éxito.")

            

            # Esperar un momento para que la UI procese el clic

            time.sleep(1)

            

            return True

            

        except Exception as e:

            logger.error(f"Error al intentar hacer clic en el botón 'Select Columns': {e}")

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




    def scroll_to_load_all_items(self, total_expected=100, max_attempts=30):
        """
        Método mejorado para cargar todos los elementos mediante scroll optimizado para SAP UI5/Fiori.
        Implementa múltiples técnicas para asegurar la carga completa de filas.
        
        Args:
            total_expected (int): Número total de elementos esperados
            max_attempts (int): Número máximo de intentos de scroll
                
        Returns:
            int: Número de elementos cargados
        """
        logger.info(f"Iniciando carga de {total_expected} elementos...")
        
        previous_rows_count = 0
        no_change_count = 0
        loaded_rows = 0
        
        # Optimizar para mejor rendimiento
        try:
            self.driver.execute_script("""
                // Desactivar animaciones para mejorar rendimiento
                document.querySelectorAll('*').forEach(el => {
                    if(el.style) {
                        el.style.animationDuration = '0.001s';
                        el.style.transitionDuration = '0.001s';
                    }
                });
            """)
        except Exception as e:
            logger.debug(f"Error al optimizar página: {e}")
        
        # Lista para registrar contenido único y evitar falsos positivos con duplicados
        unique_content = set()
        
        # Bucle principal de scroll
        for attempt in range(max_attempts):
            try:
                # 1. PRIMERA ESTRATEGIA: Buscar y hacer clic en botones "Show More"
                more_clicked = False
                show_more_patterns = [
                    "//span[contains(text(), 'Show More')]",
                    "//button[contains(text(), 'Show More')]",
                    "//div[contains(text(), 'Show More')]",
                    "//span[contains(text(), 'Load More')]",
                    "//button[contains(text(), 'Load More')]",
                    "//span[contains(text(), 'More')]",
                    "//span[contains(text(), 'Ver más')]",
                    "//button[contains(text(), 'Más')]",
                    "//a[contains(text(), 'Show More')]"
                ]
                
                for xpath in show_more_patterns:
                    buttons = self.driver.find_elements(By.XPATH, xpath)
                    for button in buttons:
                        if button.is_displayed():
                            # Hacer scroll al botón para asegurar visibilidad
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                            time.sleep(0.5)
                            
                            # Intentar primero con JavaScript click
                            try:
                                self.driver.execute_script("arguments[0].click();", button)
                                logger.info(f"Haciendo clic en botón '{button.text}'")
                                more_clicked = True
                                time.sleep(2)  # Esperar a que carguen nuevos elementos
                                break
                            except:
                                # Si falla, intentar con click normal
                                try:
                                    button.click()
                                    logger.info(f"Clic normal en botón '{button.text}'")
                                    more_clicked = True
                                    time.sleep(2)
                                    break
                                except:
                                    continue
                    
                    if more_clicked:
                        break
                
                # 2. SEGUNDA ESTRATEGIA: Scroll en contenedores específicos de SAP
                if not more_clicked:
                    scroll_script = """
                    (function() {
                        var scrolled = false;
                        
                        // Lista de posibles contenedores SAP
                        var containers = [
                            document.querySelector('.sapMList'),
                            document.querySelector('.sapMTable'),
                            document.querySelector('.sapMListItems'),
                            document.querySelector('.sapUiTable'),
                            document.querySelector('.sapMPage'),
                            document.querySelector('[role="grid"]'),
                            document.querySelector('[role="list"]')
                        ];
                        
                        // Intentar scroll en cada contenedor
                        for (var i = 0; i < containers.length; i++) {
                            var container = containers[i];
                            if (container) {
                                var originalScrollTop = container.scrollTop;
                                container.scrollTop += 500;
                                
                                if (container.scrollTop > originalScrollTop) {
                                    scrolled = true;
                                    console.log("Scroll efectivo en contenedor SAP UI5");
                                }
                            }
                        }
                        
                        // Si ningún scroll específico funcionó, usar scroll general
                        if (!scrolled) {
                            window.scrollTo(0, document.body.scrollHeight);
                        }
                        
                        return scrolled;
                    })();
                    """
                    
                    try:
                        self.driver.execute_script(scroll_script)
                        logger.info(f"Ejecutando scroll en contenedores SAP (intento {attempt+1})")
                    except Exception as e:
                        logger.debug(f"Error en script de scroll: {e}")
                        
                        # Alternativa: scroll normal
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                # 3. Esperar carga de contenido
                time.sleep(2)
                
                # 4. Contar filas actualmente visibles
                rows = find_table_rows(self.driver, highlight=False)
                current_rows_count = len(rows) if rows else 0
                
                # Verificar si hay contenido nuevo usando texto de filas
                new_content_found = False
                if rows:
                    for row in rows:
                        try:
                            row_text = row.text.strip()
                            # Solo considerar filas con contenido sustancial
                            if row_text and len(row_text) > 15 and row_text not in unique_content:
                                unique_content.add(row_text)
                                new_content_found = True
                        except:
                            pass
                
                # Registrar progreso periódicamente
                if attempt % 5 == 0 or new_content_found:
                    logger.info(f"Intento {attempt+1}: {len(unique_content)} filas únicas detectadas de {total_expected} esperadas")
                
                # Verificación de progreso
                if current_rows_count > previous_rows_count or new_content_found:
                    # Hay progreso, reiniciar contador de intentos sin cambios
                    no_change_count = 0
                    previous_rows_count = current_rows_count
                    loaded_rows = max(loaded_rows, current_rows_count)
                else:
                    no_change_count += 1
                    
                    # Si no hay cambios por varios intentos, aplicar estrategias alternativas
                    if no_change_count % 3 == 0:
                        # Cada 3 intentos sin cambios, aplicar estrategia diferente
                        
                        if no_change_count % 6 == 0:
                            # Estrategia 1: Enviar tecla Page Down
                            try:
                                body = self.driver.find_element(By.TAG_NAME, "body")
                                body.send_keys(Keys.PAGE_DOWN)
                                logger.info("Aplicando estrategia de Page Down")
                            except:
                                pass
                        else:
                            # Estrategia 2: Scroll progresivo
                            try:
                                height = self.driver.execute_script("return document.body.scrollHeight")
                                # Hacer scroll progresivo en varias etapas
                                for step in [0.3, 0.6, 0.9]:
                                    self.driver.execute_script(f"window.scrollTo(0, {int(height * step)});")
                                    time.sleep(0.3)
                                logger.info("Aplicando estrategia de scroll progresivo")
                            except:
                                pass
                
                # Criterios de finalización mejorados
                if no_change_count >= 8:
                    # Si no hay cambios después de varios intentos con todas las estrategias
                    logger.info(f"No hay nuevos elementos después de {no_change_count} intentos, finalizando")
                    break
                    
                # Si llegamos al número esperado de elementos
                if len(unique_content) >= total_expected:
                    logger.info(f"Se han cargado {len(unique_content)} elementos, ≥ {total_expected} esperados")
                    break
                    
            except Exception as e:
                logger.warning(f"Error durante el scroll en intento {attempt+1}: {e}")
        
        # Calculamos el resultado final
        coverage = (len(unique_content) / total_expected) * 100 if total_expected > 0 else 0
        logger.info(f"Scroll completado. Cobertura: {coverage:.2f}% ({len(unique_content)}/{total_expected})")
        
        return len(unique_content)
        

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

        

        

        

        

        

        

        

    def find_table_rows(self, highlight=False):

        """

        Encuentra todas las filas de una tabla SAP UI5 utilizando la función importada

        

        Args:

            highlight (bool): Si es True, resalta la primera fila encontrada

            

        Returns:

            list: Lista de elementos WebElement que representan filas de la tabla

        """

        from browser.element_finder import find_table_rows

        return find_table_rows(self.driver, highlight)

        









        

        



    def extract_issues_data(self):

        """

        Extrae datos de issues desde la tabla con procesamiento mejorado

        

        Returns:

            list: Lista de diccionarios con los datos de cada issue

        """

        # Para mantener compatibilidad con el código existente, simplemente

        # llamamos al método optimizado

        return self.extract_issues_data_optimized()  

  

  

        

        

        

        

        

        

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











    def navigate_ui_with_keyboard(self):

        """

        Navega en la interfaz de SAP usando secuencias específicas de teclado.

        Sigue una secuencia precisa de tabs y pulsaciones para llegar a la configuración de columnas.

        

        La secuencia es:

        1. Click en el título para establecer el foco

        2. 3 tabs y enter para hacer búsqueda

        3. 18 tabs y enter para abrir ajustes

        4. 5 tabs, 2 flechas derecha y enter para select columns

        

        Returns:

            bool: True si la navegación completa fue exitosa, False en caso contrario

        """

        try:

            logger.info("Iniciando navegación por teclado en la interfaz de SAP...")

            

            # 1. Dar click en el título "Issues and Actions Overview" para establecer el foco

            title_elements = self.driver.find_elements(By.XPATH, 

                "//div[contains(text(), 'Issues and Actions Overview')] | //span[contains(text(), 'Issues and Actions Overview')]")

            

            if title_elements:

                for element in title_elements:

                    if element.is_displayed():

                        # Hacer scroll y click en el título

                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)

                        time.sleep(0.5)

                        self.driver.execute_script("arguments[0].click();", element)

                        logger.info("✅ Click en título realizado - foco establecido")

                        time.sleep(1)

                        break

            else:

                # Alternativa: click en cualquier parte visible de la ventana principal

                self.driver.find_element(By.TAG_NAME, "body").click()

                logger.info("Click en body como alternativa para establecer foco")

                time.sleep(1)

                

            # Crear ActionChains para la secuencia de teclas

            from selenium.webdriver.common.action_chains import ActionChains

            from selenium.webdriver.common.keys import Keys

            

            actions = ActionChains(self.driver)

            

            # 2. Pulsar 3 tabs y enter (Botón Search)

            logger.info("Enviando 3 TABs y ENTER para el botón de búsqueda...")

            for _ in range(3):

                actions.send_keys(Keys.TAB)

                actions.pause(0.5)  # Pausa entre teclas

            actions.send_keys(Keys.ENTER)

            actions.perform()

            

            # Esperar a que se ejecute la búsqueda

            time.sleep(3)

            logger.info("✅ Búsqueda realizada")

            

            # Crear nueva secuencia (resetear actions)

            actions = ActionChains(self.driver)

            

            # 3. Pulsar 18 tabs y enter (Botón Settings)

            logger.info("Enviando 18 TABs y ENTER para el botón de ajustes...")

            for _ in range(18):

                actions.send_keys(Keys.TAB)

                actions.pause(0.3)  # Pausa entre teclas

            actions.send_keys(Keys.ENTER)

            actions.perform()

            

            # Esperar a que se abra el panel de ajustes

            time.sleep(2)

            logger.info("✅ Panel de ajustes abierto")

            

            # Verificar que el panel de ajustes esté abierto

            if not self._verify_settings_panel_opened():

                logger.warning("⚠️ No se detectó el panel de ajustes abierto")

                return False

            

            # Crear nueva secuencia (resetear actions)

            actions = ActionChains(self.driver)

            

            # 4. Pulsar 5 tabs, 2 flechas derecha y enter (Seleccionar columnas)

            logger.info("Enviando 5 TABs, 2 flechas derecha y ENTER para seleccionar columnas...")

            for _ in range(5):

                actions.send_keys(Keys.TAB)

                actions.pause(0.3)

            for _ in range(2):

                actions.send_keys(Keys.ARROW_RIGHT)

                actions.pause(0.3)

            actions.send_keys(Keys.ENTER)

            actions.perform()

            

            # Esperar a que se abra el panel de columnas

            time.sleep(2)

            

            # Verificar si estamos en el panel de selección de columnas

            if self._verify_column_panel_opened():

                logger.info("✅ Navegación por teclado completada con éxito")

                return True

            else:

                logger.warning("⚠️ No se detectó el panel de selección de columnas")

                return False

                

        except Exception as e:

            logger.error(f"Error durante la navegación por teclado: {e}")

            return False



    def select_all_columns_and_confirm(self):

        """

        Selecciona todas las columnas y confirma la selección una vez en el panel de columnas.

        Esta función debe ejecutarse después de navegar al panel de selección de columnas.

        

        La secuencia es:

        1. 3 tabs y enter para marcar "Select All"

        2. 2 tabs y enter para confirmar con OK

        

        Returns:

            bool: True si todo el proceso fue exitoso, False en caso contrario

        """

        try:

            logger.info("Seleccionando todas las columnas con navegación por teclado...")

            

            from selenium.webdriver.common.action_chains import ActionChains

            from selenium.webdriver.common.keys import Keys

            

            # Verificar que estamos en el panel de columnas

            if not self._verify_column_panel_opened():

                logger.warning("No estamos en el panel de selección de columnas")

                return False

            

            # 1. Marcar "Select All" con 3 tabs y enter

            actions = ActionChains(self.driver)

            logger.info("Enviando 3 TABs y ENTER para marcar 'Select All'...")

            for _ in range(3):

                actions.send_keys(Keys.TAB)

                actions.pause(0.3)

            actions.send_keys(Keys.ENTER)

            actions.perform()

            

            # Esperar a que se procese la selección

            time.sleep(1)

            logger.info("✅ 'Select All' marcado")

            

            # 2. Confirmar con OK usando 2 tabs y enter

            actions = ActionChains(self.driver)

            logger.info("Enviando 2 TABs y ENTER para confirmar con OK...")

            for _ in range(2):

                actions.send_keys(Keys.TAB)

                actions.pause(0.3)

            actions.send_keys(Keys.ENTER)

            actions.perform()

            

            # Esperar a que se cierre el panel

            time.sleep(2)

            

            # Verificar que el panel se cerró (ya no está visible)

            panel_closed = not self._verify_column_panel_opened() and not self._verify_settings_panel_opened()

            

            if panel_closed:

                logger.info("✅ Selección de columnas completada y confirmada con éxito")

                return True

            else:

                logger.warning("⚠️ No se pudo confirmar que los paneles se cerraron")

                return False

                

        except Exception as e:

            logger.error(f"Error durante la selección de columnas: {e}")

            return False



    def navigate_and_select_all_columns(self):

        """

        Ejecuta el proceso completo de navegación por teclado para llegar a la configuración

        de columnas, seleccionar todas, y confirmar la selección.

        

        Este método integra los pasos de: 

        1. Navegación por teclado a través de la interfaz

        2. Selección de todas las columnas

        3. Confirmación de la selección

        

        Returns:

            bool: True si todo el proceso fue exitoso, False en caso contrario

        """

        try:

            logger.info("Iniciando proceso completo de navegación y selección de columnas...")

            

            # Paso 1: Navegación por teclado hasta el panel de selección de columnas

            navigation_success = self.navigate_ui_with_keyboard()

            

            if not navigation_success:

                logger.error("❌ No se pudo completar la navegación por teclado")

                return False

                

            # Breve pausa para estabilización

            time.sleep(1)

            

            # Paso 2: Seleccionar todas las columnas y confirmar

            selection_success = self.select_all_columns_and_confirm()

            

            if not selection_success:

                logger.error("❌ No se pudo completar la selección de columnas")

                return False

                

            logger.info("✅ Proceso completo de navegación y selección de columnas finalizado con éxito")

            return True

            

        except Exception as e:

            logger.error(f"Error en el proceso completo de navegación y selección: {e}")

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







    def click_columns_tab_precise(driver):

            """

            Función precisa para hacer clic en el tercer ícono (columnas)

            del panel de configuración.

            

            Args:

                driver: WebDriver de Selenium con el panel de ajustes ya abierto

                    

            Returns:

                bool: True si el clic fue exitoso, False en caso contrario

            """

            try:

                # Esperar a que la interfaz se cargue completamente

                time.sleep(1.5)

                

                # Intento 1: ID específico del ícono de columnas

                try:

                    column_icon = driver.find_element(By.XPATH, 

                        "//*[@id='application-iam-ui-component---home--issueFilterDialog-custom-button-application-iam-ui-component---home--issuesColumns-img']")

                    if column_icon and column_icon.is_displayed():

                        driver.execute_script("arguments[0].click();", column_icon)

                        print("✅ Clic exitoso en el ícono de columnas por ID específico")

                        time.sleep(1)

                        return True

                except Exception as e:

                    print(f"ID específico no encontrado: {e}")



                # Intento 2: JavaScript para seleccionar el tercer botón

                js_script = """

                return (function() {

                    // Encontrar la barra de segmentos

                    var segment = document.querySelector('.sapMSegB');

                    if (segment) {

                        // Obtener todos los botones visibles

                        var buttons = Array.from(segment.querySelectorAll('.sapMSegBBtn')).filter(

                            button => button.offsetParent !== null

                        );

                        

                        // Si hay al menos 3 botones, hacer clic en el tercero

                        if (buttons.length >= 3) {

                            buttons[2].click();

                            return true;

                        }

                    }

                    return false;

                })();

                """

                

                result = driver.execute_script(js_script)

                if result:

                    print("✅ Clic exitoso en el tercer botón de segmento mediante JavaScript")

                    time.sleep(1)

                    return True

                

                # Intento 3: Por posición usando XPath

                selector = "(//div[contains(@class, 'sapMSegBBtn')])[3]"

                elements = driver.find_elements(By.XPATH, selector)

                if elements and elements[0].is_displayed():

                    driver.execute_script("arguments[0].click();", elements[0])

                    print(f"✅ Clic exitoso en tercer ícono con selector: {selector}")

                    time.sleep(1)

                    return True

                    

                # Intento 4: Enfoque directo a todos los divs y clic en el tercero

                buttons = driver.find_elements(By.XPATH, "//div[contains(@class, 'sapMSegB')]//div")

                for i, button in enumerate(buttons):

                    if i == 2 and button.is_displayed():  # El tercer elemento (índice 2)

                        driver.execute_script("arguments[0].click();", button)

                        print("✅ Clic exitoso en tercer elemento por índice")

                        time.sleep(1)

                        return True

                        

                print("❌ No se pudo hacer clic en el ícono de columnas")

                return False

                    

            except Exception as e:

                print(f"Error al intentar hacer clic en el ícono de columnas: {e}")

                return False

















    def configure_columns_avoiding_reset(driver):

        """

        Configura todas las columnas visibles evitando específicamente el botón Reset.

        

        Esta función realiza los tres pasos necesarios:

        1. Hace clic en el tercer ícono (columns) evitando el botón Reset

        2. Marca la casilla "Select All"

        3. Confirma con OK

        

        Args:

            driver: WebDriver de Selenium con el panel de ajustes ya abierto

            

        Returns:

            bool: True si todo el proceso fue exitoso, False en caso contrario

        """

        try:

            # 1. Hacer clic en el ícono de columnas (evitando Reset)

            print("Paso 1: Haciendo clic en el ícono de columnas (evitando Reset)...")

            if not click_columns_tab_precise(driver):

                print("❌ No se pudo hacer clic en el ícono de columnas correctamente")

                return False

                

            # Esperar a que se cargue la lista de columnas

            time.sleep(1)

            

            # 2. Marcar "Select All"

            print("Paso 2: Marcando la casilla 'Select All'...")

            select_all_clicked = False

            

            # Selectores para la casilla "Select All"

            select_all_selectors = [

                # Por texto exacto

                "//div[text()='Select All']/preceding-sibling::div[contains(@class, 'sapMCb')]",

                "//div[normalize-space(text())='Select All']/preceding-sibling::div",

                

                # Por ID específico visible en la captura

                "//div[@id='application-iam-ui-component---home--issueSettingsDialogColumnListCheckBoxAll-CbBg']",

                

                # Por clase y posición (primer checkbox en el panel)

                "(//div[contains(@class, 'sapMCb')])[1]",

                "(//div[contains(@class, 'sapMCbMark')])[1]"

            ]

            

            # Intentar cada selector

            for selector in select_all_selectors:

                try:

                    elements = driver.find_elements(By.XPATH, selector)

                    for element in elements:

                        if element.is_displayed():

                            # Verificar si ya está marcado

                            try:

                                aria_checked = element.get_attribute("aria-checked")

                                if aria_checked == "true":

                                    print("✅ 'Select All' ya está marcado")

                                    select_all_clicked = True

                                    break

                            except:

                                pass

                                

                            # Hacer clic con JavaScript

                            driver.execute_script("arguments[0].click();", element)

                            print(f"✅ Clic exitoso en 'Select All' con selector: {selector}")

                            select_all_clicked = True

                            time.sleep(0.5)

                            break

                    if select_all_clicked:

                        break

                except Exception as e:

                    print(f"Error con selector para Select All {selector}: {e}")

                    continue

            

            # Si no se pudo marcar con los selectores, intentar con JavaScript

            if not select_all_clicked:

                js_select_all = """

                (function() {

                    // Buscar el texto "Select All"

                    var selectAllText = document.evaluate(

                        "//div[text()='Select All'] | //span[text()='Select All']", 

                        document, 

                        null, 

                        XPathResult.FIRST_ORDERED_NODE_TYPE, 

                        null

                    ).singleNodeValue;

                    

                    if (selectAllText) {

                        // Buscar el checkbox asociado con el texto

                        var checkbox = null;

                        

                        // Verificar si el elemento padre tiene un hermano anterior que sea el checkbox

                        if (selectAllText.parentElement && selectAllText.parentElement.previousElementSibling) {

                            checkbox = selectAllText.parentElement.previousElementSibling;

                        }

                        

                        // Verificar si el elemento ya tiene el checkbox como hijo

                        if (!checkbox) {

                            checkbox = selectAllText.parentElement.querySelector('.sapMCb, input[type="checkbox"]');

                        }

                        

                        // Si encontramos el checkbox, verificar si ya está marcado

                        if (checkbox) {

                            var isChecked = checkbox.getAttribute('aria-checked') === 'true';

                            if (isChecked) {

                                console.log('Select All ya está marcado');

                                return true;

                            }

                            

                            // Hacer clic en el checkbox

                            checkbox.click();

                            return true;

                        }

                    }

                    

                    // Alternativa: buscar el primer checkbox visible en el diálogo

                    var dialog = document.querySelector('.sapMDialog, .sapMPopover');

                    if (dialog) {

                        var checkboxes = dialog.querySelectorAll('.sapMCb, input[type="checkbox"]');

                        for (var i = 0; i < checkboxes.length; i++) {

                            if (checkboxes[i].offsetParent !== null) {

                                // Verificar si ya está marcado

                                var isChecked = checkboxes[i].getAttribute('aria-checked') === 'true';

                                if (isChecked) {

                                    console.log('Primer checkbox ya está marcado');

                                    return true;

                                }

                                

                                // Hacer clic en el primer checkbox visible

                                checkboxes[i].click();

                                return true;

                            }

                        }

                    }

                    

                    return false;

                })();

                """

                

                select_all_clicked = driver.execute_script(js_select_all)

                if select_all_clicked:

                    print("✅ Clic exitoso en 'Select All' mediante JavaScript")

                    time.sleep(0.5)

                else:

                    print("❌ No se pudo marcar la casilla 'Select All'")

                    return False

            

            # 3. Hacer clic en OK

            print("Paso 3: Haciendo clic en botón 'OK'...")

            ok_clicked = False

            

            # Selectores para el botón OK (EVITANDO RESET)

            ok_selectors = [

                # Selectores específicos para OK que excluyen Reset

                "//div[contains(@class, 'sapMBarRight')]//button[text()='OK']",

                "//button[text()='OK' and not(preceding-sibling::button[text()='Reset'])]",

                "//footer//button[text()='OK']",

                "//div[contains(@class, 'sapMDialogFooter')]//button[text()='OK']"

            ]

            

            # Intentar cada selector

            for selector in ok_selectors:

                try:

                    elements = driver.find_elements(By.XPATH, selector)

                    for element in elements:

                        if element.is_displayed() and element.is_enabled():

                            # Verificar explícitamente que NO es el botón Reset

                            if element.text == "Reset":

                                print(f"¡Alerta! Selector {selector} apunta al botón Reset. Evitando.")

                                continue

                                

                            # Hacer clic con JavaScript

                            driver.execute_script("arguments[0].click();", element)

                            print(f"✅ Clic exitoso en botón 'OK' con selector: {selector}")

                            ok_clicked = True

                            time.sleep(1)

                            break

                    if ok_clicked:

                        break

                except Exception as e:

                    print(f"Error con selector para OK {selector}: {e}")

                    continue

            

            # Si no se pudo hacer clic con los selectores, intentar con JavaScript

            if not ok_clicked:

                js_click_ok = """

                (function() {

                    // Obtener el botón Reset para evitarlo explícitamente

                    var resetButton = Array.from(document.querySelectorAll('button')).find(

                        function(btn) { return btn.textContent === 'Reset' && btn.offsetParent !== null; }

                    );

                    

                    // Buscar botones OK

                    var okButtons = Array.from(document.querySelectorAll('button')).filter(function(btn) {

                        return btn.textContent === 'OK' && 

                            btn.offsetParent !== null && 

                            !btn.disabled && 

                            btn !== resetButton;

                    });

                    

                    if (okButtons.length > 0) {

                        // Verificar que no es el botón Reset

                        if (resetButton) {

                            var resetRect = resetButton.getBoundingClientRect();

                            var okRect = okButtons[0].getBoundingClientRect();

                            

                            // Si están muy cerca en la misma posición, podría ser confusión

                            if (Math.abs(resetRect.x - okRect.x) < 100 && Math.abs(resetRect.y - okRect.y) < 20) {

                                console.log('Posible confusión con botón Reset. Buscando alternativa.');

                                // Buscar otro botón OK más lejos

                                for (var i = 1; i < okButtons.length; i++) {

                                    var altOkRect = okButtons[i].getBoundingClientRect();

                                    if (Math.abs(resetRect.x - altOkRect.x) >= 100 || Math.abs(resetRect.y - altOkRect.y) >= 20) {

                                        okButtons[i].click();

                                        return true;

                                    }

                                }

                            }

                        }

                        

                        // Hacer clic en el primer botón OK

                        okButtons[0].click();

                        return true;

                    }

                    

                    // Buscar en los botones de la barra inferior o footer

                    var dialogFooter = document.querySelector('.sapMDialogFooter, .sapMBarRight, footer');

                    if (dialogFooter) {

                        var footerButtons = dialogFooter.querySelectorAll('button');

                        for (var i = 0; i < footerButtons.length; i++) {

                            var btn = footerButtons[i];

                            if (btn.textContent === 'OK' && 

                                btn.offsetParent !== null && 

                                !btn.disabled && 

                                btn !== resetButton) {

                                btn.click();

                                return true;

                            }

                        }

                    }

                    

                    return false;

                })();

                """

                

                ok_clicked = driver.execute_script(js_click_ok)

                if ok_clicked:

                    print("✅ Clic exitoso en botón 'OK' mediante JavaScript")

                    time.sleep(1)

                else:

                    # Último recurso: usar Ctrl+Enter

                    try:

                        # Enfocar cualquier elemento dentro del diálogo

                        actions = ActionChains(driver)

                        actions.key_down(Keys.CONTROL).send_keys(Keys.RETURN).key_up(Keys.CONTROL).perform()

                        print("✅ Confirmación mediante Ctrl+Enter")

                        time.sleep(1)

                        ok_clicked = True

                    except Exception as e:

                        print(f"Error al intentar Ctrl+Enter: {e}")

                        

                    if not ok_clicked:

                        print("❌ No se pudo hacer clic en el botón 'OK'")

                        return False

            

            print("✅ Configuración de columnas completada exitosamente")

            return True

            

        except Exception as e:

            print(f"Error durante la configuración de columnas: {e}")

            return False

















    def click_select_columns_tab(self):

        """

        Hace clic en la pestaña 'Select Columns' del panel de ajustes de forma precisa

        y confiable utilizando el ID exacto del elemento.

        

        Este método debe ser llamado después de abrir el panel de ajustes con

        click_settings_button().

        

        Returns:

            bool: True si el clic fue exitoso y se abrió el panel de columnas, False en caso contrario

        """

        try:

            logger.info("Intentando hacer clic en el ícono 'Select Columns'...")

            

            # Esperar para asegurar que la interfaz esté completamente cargada

            time.sleep(1.5)

            

            # 1. ESTRATEGIA PRINCIPAL: Usar el ID exacto identificado en la inspección del DOM

            select_columns_id = "application-iam-ui-component---home--issueFilterDialog-custom-button-application-iam-ui-component---home--issuesColumns"

            

            try:

                # Intentar localizar por ID exacto

                select_columns_btn = self.driver.find_element(By.ID, select_columns_id)

                if select_columns_btn and select_columns_btn.is_displayed():

                    # Hacer scroll para asegurar visibilidad

                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", select_columns_btn)

                    time.sleep(0.5)

                    

                    # Usar JavaScript para un clic más confiable en SAP UI5

                    self.driver.execute_script("arguments[0].click();", select_columns_btn)

                    logger.info("Clic exitoso en 'Select Columns' usando ID exacto")

                    time.sleep(1.5)  # Esperar a que se abra el panel

                    

                    # Verificar que el panel de columnas se abrió correctamente

                    if self._verify_column_panel_opened():

                        return True

            except Exception as e:

                logger.debug(f"No se pudo encontrar el botón por ID principal: {e}")

                

                # Intentar con XPath usando el mismo ID

                try:

                    select_columns_xpath = f"//*[@id='{select_columns_id}']"

                    select_columns_btn = self.driver.find_element(By.XPATH, select_columns_xpath)

                    

                    if select_columns_btn.is_displayed():

                        self.driver.execute_script("arguments[0].click();", select_columns_btn)

                        logger.info("Clic exitoso en 'Select Columns' usando XPath con ID")

                        time.sleep(1.5)

                        

                        if self._verify_column_panel_opened():

                            return True

                except Exception as ex:

                    logger.debug(f"No se pudo encontrar el botón por XPath con ID: {ex}")

            

            # 2. ESTRATEGIA ALTERNATIVA: Usar el ID de la imagen dentro del botón

            img_id = "application-iam-ui-component---home--issueFilterDialog-custom-button-application-iam-ui-component---home--issuesColumns-img"

            

            try:

                img_element = self.driver.find_element(By.ID, img_id)

                if img_element:

                    # Obtener el elemento padre (el botón)

                    select_columns_btn = self.driver.execute_script("return arguments[0].parentNode.parentNode.parentNode;", img_element)

                    if select_columns_btn:

                        self.driver.execute_script("arguments[0].click();", select_columns_btn)

                        logger.info("Clic exitoso en 'Select Columns' a través del elemento imagen")

                        time.sleep(1.5)

                        

                        if self._verify_column_panel_opened():

                            return True

            except Exception as e:

                logger.debug(f"No se pudo encontrar el botón a través de la imagen: {e}")

            

            # 3. ESTRATEGIA POSICIONAL: Tercer botón en la barra segmentada

            selectors = [

                "(//div[contains(@class, 'sapMSegB')]/ul/li)[3]",

                "(//li[contains(@class, 'sapMSegBBtn')])[3]",

                "(//div[@role='option' and @aria-posinset='3'])",

                "//li[@aria-posinset='3' and @aria-label='Select Columns']"

            ]

            

            for selector in selectors:

                try:

                    elements = self.driver.find_elements(By.XPATH, selector)

                    for element in elements:

                        if element.is_displayed():

                            # Verificar si es el botón correcto mediante título o texto

                            title = element.get_attribute("title") or ""

                            aria_label = element.get_attribute("aria-label") or ""

                            

                            if "column" in title.lower() or "column" in aria_label.lower():

                                # Hacer scroll y clic

                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)

                                time.sleep(0.5)

                                self.driver.execute_script("arguments[0].click();", element)

                                logger.info(f"Clic exitoso en 'Select Columns' usando selector posicional: {selector}")

                                time.sleep(1.5)

                                

                                if self._verify_column_panel_opened():

                                    return True

                except Exception as e:

                    logger.debug(f"Error con selector {selector}: {e}")

                    continue

            

            # 4. ESTRATEGIA JAVASCRIPT: Script personalizado para identificar y hacer clic en el tercer botón

            js_script = """

            (function() {

                try {

                    // Buscar por ID exacto

                    var button = document.getElementById('application-iam-ui-component---home--issueFilterDialog-custom-button-application-iam-ui-component---home--issuesColumns');

                    if (button && button.offsetParent !== null) {

                        button.click();

                        return true;

                    }

                    

                    // Buscar por contenido del título

                    var buttons = document.querySelectorAll('li[title="Select Columns"], li[aria-label="Select Columns"]');

                    for (var i = 0; i < buttons.length; i++) {

                        if (buttons[i].offsetParent !== null) {

                            buttons[i].click();

                            return true;

                        }

                    }

                    

                    // Buscar tercer botón en barra segmentada

                    var segmentedButtons = document.querySelectorAll('.sapMSegB li, .sapMSegBBtn');

                    if (segmentedButtons.length >= 3) {

                        // Verificar que estamos en el panel correcto

                        for (var i = 0; i < segmentedButtons.length; i++) {

                            if (i === 2 && segmentedButtons[i].offsetParent !== null) {

                                segmentedButtons[i].click();

                                return true;

                            }

                        }

                    }

                    

                    return false;

                } catch(e) {

                    console.error("Error en script de selección de columnas: " + e);

                    return false;

                }

            })();

            """

            

            try:

                result = self.driver.execute_script(js_script)

                if result:

                    logger.info("Clic exitoso en 'Select Columns' mediante script JavaScript")

                    time.sleep(1.5)

                    

                    if self._verify_column_panel_opened():

                        return True

            except Exception as e:

                logger.debug(f"Error en script JavaScript: {e}")

            

            logger.warning("No se pudo hacer clic en el ícono 'Select Columns' después de agotar todas las estrategias")

            return False

            

        except Exception as e:

            logger.error(f"Error general al intentar hacer clic en 'Select Columns': {e}")

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
            return issue_data  # Devolver datos sin procesar en caso de error
        
        
        
        
        
        
        
        
        
        
    def extract_all_issues(self):
        """
        Método robusto para extraer issues con múltiples estrategias de scroll.
        
        Returns:
            list: Lista de diccionarios con datos de issues
        """
        try:
            logger.info("🚀 Iniciando extracción dinámica de issues...")
            
            # 1. Optimizar rendimiento de página
            try:
                from browser.element_finder import optimize_page_performance
                optimize_page_performance(self.driver)
                logger.info("✅ Rendimiento de página optimizado")
            except Exception as perf_error:
                logger.warning(f"⚠️ Error en optimización de rendimiento: {perf_error}")
            
            # 2. Detectar número total de issues
            total_issues = self._detect_total_issues_from_tab()
            logger.info(f"📊 Total de issues detectados: {total_issues}")
            
            # 3. Estrategias de scroll múltiples
            scroll_strategies = [
                self._scroll_for_more_items,
                self._scroll_standard_ui5_table,
                self._scroll_responsive_table,
                self._scroll_grid_table
            ]
            
            # Ejecutar cada estrategia de scroll
            for strategy in scroll_strategies:
                try:
                    logger.info(f"🔄 Aplicando estrategia de scroll: {strategy.__name__}")
                    strategy(total_issues)
                except Exception as scroll_error:
                    logger.debug(f"❌ Error en estrategia de scroll {strategy.__name__}: {scroll_error}")
            
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
    
    
    
    
    






    def optimize_sap_table_loading(self, total_expected_rows=100):
        """
        Método integral para optimizar la carga de tablas SAP con múltiples estrategias.
        
        Args:
            total_expected_rows (int): Número aproximado de filas esperadas
        
        Returns:
            int: Número de filas cargadas
        """
        try:
            logger.info(f"🚀 Iniciando optimización de carga de tabla SAP: {total_expected_rows} filas esperadas")
            
            # Estrategias de scroll y carga
            scroll_strategies = [
                self._scroll_sap_list_container,
                self._scroll_sap_grid_container,
                self._scroll_page_bottom,
                self._click_show_more_buttons
            ]
            
            unique_content = set()
            loaded_rows = 0
            max_attempts = 10
            
            for attempt in range(max_attempts):
                logger.info(f"🔄 Intento de carga {attempt + 1}/{max_attempts}")
                
                # Aplicar cada estrategia de scroll
                for strategy in scroll_strategies:
                    try:
                        strategy()
                        time.sleep(2)  # Esperar a que carguen nuevos elementos
                    except Exception as strategy_error:
                        logger.debug(f"Error en estrategia {strategy.__name__}: {strategy_error}")
                
                # Detectar filas actuales
                current_rows = find_table_rows_optimized(self.driver)
                
                # Verificar contenido único
                new_content_found = False
                for row in current_rows:
                    try:
                        row_text = row.text.strip()
                        if row_text and len(row_text) > 15 and row_text not in unique_content:
                            unique_content.add(row_text)
                            new_content_found = True
                    except:
                        pass
                
                # Actualizar conteo de filas
                loaded_rows = len(unique_content)
                
                # Criterios de finalización
                coverage = (loaded_rows / total_expected_rows * 100) if total_expected_rows > 0 else 0
                logger.info(f"📊 Progreso: {loaded_rows} filas ({coverage:.2f}%)")
                
                if (
                    loaded_rows >= total_expected_rows or 
                    coverage >= 95 or 
                    not new_content_found
                ):
                    logger.info("✅ Carga de tabla completada")
                    break
            
            logger.info(f"🏁 Carga finalizada: {loaded_rows} filas únicas")
            return loaded_rows
        
        except Exception as e:
            logger.error(f"Error crítico en optimización de tabla: {e}")
            return 0

    def _scroll_sap_list_container(self):
        """Scroll en contenedores de lista SAP"""
        try:
            self.driver.execute_script("""
                const containers = [
                    document.querySelector('.sapMList'),
                    document.querySelector('.sapMListItems'),
                    document.querySelector('.sapMTable')
                ];
                
                containers.forEach(container => {
                    if (container) {
                        container.scrollTop = container.scrollHeight;
                    }
                });
            """)
            time.sleep(1)
        except Exception as e:
            logger.debug(f"Error en scroll de lista SAP: {e}")

    def _scroll_sap_grid_container(self):
        """Scroll en contenedores de grid SAP"""
        try:
            self.driver.execute_script("""
                const gridContainers = [
                    document.querySelector('[role="grid"]'),
                    document.querySelector('.sapUiTable'),
                    document.querySelector('.sapUiTableCtrlScr')
                ];
                
                gridContainers.forEach(container => {
                    if (container) {
                        container.scrollTop = container.scrollHeight;
                    }
                });
            """)
            time.sleep(1)
        except Exception as e:
            logger.debug(f"Error en scroll de grid SAP: {e}")

    def _scroll_page_bottom(self):
        """Scroll al final de la página"""
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
        except Exception as e:
            logger.debug(f"Error en scroll de página: {e}")    
    
    
    
    
                
    def _detect_total_issues_from_tab(self):
        """
        Detecta el número total de issues directamente desde la pestaña "Issues (n)"
        utilizando múltiples estrategias para mayor robustez.
        
        Returns:
            int: Número total de issues o 0 si no se puede detectar
        """
        try:
            logger.info("Detectando número total de issues desde la pestaña...")
            
            # Estrategia 1: Buscar específicamente la pestaña Issues con número
            tab_selectors = [
                "//div[contains(@class, 'sapMITBTab')]//*[contains(text(), 'Issues')]",
                "//div[contains(@class, 'sapMITBContent')]//span[contains(text(), 'Issues')]",
                "//div[@role='tab']//*[contains(text(), 'Issues')]",
                "//li[@role='tab']//*[contains(text(), 'Issues')]",
                "//div[contains(text(), 'Issues') and contains(text(), '(')]",
                "//span[contains(text(), 'Issues') and contains(text(), '(')]",
                "//li[contains(text(), 'Issues') and contains(text(), '(')]"
            ]
            
            for selector in tab_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            text = element.text.strip()
                            if '(' in text and ')' in text:
                                # Extraer número entre paréntesis
                                match = re.search(r'\((\d+)\)', text)
                                if match:
                                    total = int(match.group(1))
                                    logger.info(f"Total de issues detectado: {total} (desde pestaña)")
                                    return total
                except Exception as e:
                    logger.debug(f"Error con selector {selector}: {e}")
                    continue
            
            # Estrategia 2: Usar JavaScript para buscar en todos los elementos visibles
            js_script = """
            (function() {
                // Buscar en todos los elementos visibles
                var elements = document.querySelectorAll('*');
                for (var i = 0; i < elements.length; i++) {
                    var el = elements[i];
                    if (el.offsetParent !== null) {  // Elemento visible
                        var text = el.textContent || '';
                        
                        // Buscar patrón "Issues(número)" o "Issues (número)"
                        var match = text.match(/Issues\s*\((\d+)\)/i);
                        if (match && match[1]) {
                            return parseInt(match[1], 10);
                        }
                    }
                }
                
                // Buscar patrón alternativo "N of M" o similar
                var countElements = document.querySelectorAll('.sapMListNoData, .sapMMessageToast, .sapMListInfo');
                for (var j = 0; j < countElements.length; j++) {
                    var countEl = countElements[j];
                    if (countEl.offsetParent !== null) {
                        var countText = countEl.textContent || '';
                        
                        // Patrones como "10 of 103" o "Showing 10 of 103"
                        var countMatch = countText.match(/\d+\s+of\s+(\d+)/i);
                        if (countMatch && countMatch[1]) {
                            return parseInt(countMatch[1], 10);
                        }
                    }
                }
                
                return 0;  // No se encontró
            })();
            """
            
            result = self.driver.execute_script(js_script)
            if result and result > 0:
                logger.info(f"Total de issues detectado: {result} (mediante JavaScript)")
                return result
            
            # Estrategia 3: Buscar en gráficos o estadísticas visibles
            chart_selectors = [
                "//div[contains(@class, 'sapSuiteUiCommonsChartItem')]",
                "//div[contains(@class, 'sapVizFrame')]",
                "//div[contains(@class, 'sapMPanel')]//div[contains(@class, 'sapMText')]"
            ]
            
            for selector in chart_selectors:
                elements = self.driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed():
                        text = element.text.strip()
                        # Buscar números que podrían ser el total
                        numbers = re.findall(r'\b(\d+)\b', text)
                        if numbers:
                            # Tomar el número más grande como posible total
                            largest = max([int(n) for n in numbers])
                            if largest > 10:  # Asumir que es un total si es razonablemente grande
                                logger.info(f"Posible total de issues detectado: {largest} (desde gráfico/panel)")
                                return largest
            
            # Si aún no se ha detectado, intentar hacer clic en la pestaña Issues y luego buscar de nuevo
            try:
                issues_tab_selectors = [
                    "//div[contains(text(), 'Issues')]",
                    "//span[contains(text(), 'Issues')]",
                    "//div[@role='tab' and contains(., 'Issues')]"
                ]
                
                tab_clicked = False
                for selector in issues_tab_selectors:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            # Hacer scroll al elemento para asegurar visibilidad
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                            time.sleep(0.5)
                            
                            # Intentar hacer clic
                            self.driver.execute_script("arguments[0].click();", element)
                            logger.info(f"Clic en pestaña Issues realizado")
                            tab_clicked = True
                            time.sleep(1)
                            break
                    
                    if tab_clicked:
                        break
                
                if tab_clicked:
                    # Intentar de nuevo detectar el número después del clic
                    for selector in tab_selectors:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            if element.is_displayed():
                                text = element.text.strip()
                                if '(' in text and ')' in text:
                                    match = re.search(r'\((\d+)\)', text)
                                    if match:
                                        total = int(match.group(1))
                                        logger.info(f"Total de issues detectado: {total} (después de clic en pestaña)")
                                        return total
            except Exception as e:
                logger.debug(f"Error al intentar hacer clic en pestaña Issues: {e}")
            
            # Último recurso: Contar las filas visibles y asumir un número más alto
            try:
                rows = find_table_rows(self.driver, highlight=False)
                if rows:
                    visible_count = len(rows)
                    # Asumir que hay más filas que no son visibles inicialmente
                    estimated_total = max(visible_count * 3, 100)
                    logger.warning(f"No se detectó total exacto de issues. Estimando {estimated_total} basado en {visible_count} filas visibles")
                    return estimated_total
            except Exception as e:
                logger.debug(f"Error al contar filas visibles: {e}")
            
            # Si todo falla, usar un valor predeterminado
            logger.warning("No se pudo detectar el número total de issues, usando valor predeterminado (100)")
            return 100
        
        except Exception as e:
            # Add a general exception handler to catch any unexpected errors
            logger.error(f"Error al detectar número total de issues: {e}")
            return 100  # Return default value in case of any unexpected error
    
    
    
    

    def _scroll_for_more_items(self, total_expected=100, max_attempts=15):
        """
        Método avanzado para cargar todos los elementos en tablas SAP UI5/Fiori.
        
        Implementa múltiples estrategias de scroll para maximizar la carga de elementos.
        
        Args:
            total_expected (int): Número total de elementos esperados
            max_attempts (int): Número máximo de intentos de scroll
        
        Returns:
            int: Número de elementos cargados
        """
        try:
            logger.info(f"🔄 Iniciando scroll para cargar {total_expected} elementos...")
            
            # Conjunto para rastrear contenido único
            unique_content = set()
            previous_rows_count = 0
            no_change_count = 0
            loaded_rows = 0
            
            # Estrategias de scroll
            scroll_strategies = [
                # Scroll general de página
                lambda: self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);"),
                
                # Scroll en contenedores SAP específicos
                lambda: self.driver.execute_script("""
                    var containers = [
                        document.querySelector('.sapMList'),
                        document.querySelector('.sapMListItems'),
                        document.querySelector('.sapMTable'),
                        document.querySelector('[role="grid"]')
                    ];
                    
                    containers.forEach(function(container) {
                        if (container) {
                            container.scrollTop = container.scrollHeight;
                        }
                    });
                """),
                
                # Intentar encontrar y hacer clic en botones "Show More"
                lambda: self._click_show_more_buttons()
            ]
            
            for attempt in range(max_attempts):
                logger.info(f"🔍 Intento de scroll {attempt + 1}/{max_attempts}")
                
                # Aplicar estrategias de scroll
                for strategy in scroll_strategies:
                    try:
                        strategy()
                        time.sleep(2)  # Esperar a que carguen nuevos elementos
                    except Exception as e:
                        logger.debug(f"Error en estrategia de scroll: {e}")
                
                # Detectar filas actuales
                try:
                    rows = find_table_rows_optimized(self.driver, highlight=False)
                    current_rows_count = len(rows) if rows else 0
                    
                    # Verificar contenido único
                    new_content_found = False
                    if rows:
                        for row in rows:
                            try:
                                row_text = row.text.strip()
                                if row_text and len(row_text) > 15 and row_text not in unique_content:
                                    unique_content.add(row_text)
                                    new_content_found = True
                            except:
                                pass
                    
                    # Evaluar progreso
                    if current_rows_count > previous_rows_count or new_content_found:
                        previous_rows_count = current_rows_count
                        loaded_rows = max(loaded_rows, current_rows_count)
                        no_change_count = 0
                        
                        # Registro de progreso
                        coverage = (loaded_rows / total_expected * 100) if total_expected > 0 else 0
                        logger.info(f"📊 Progreso: {loaded_rows} filas ({coverage:.2f}%)")
                    else:
                        no_change_count += 1
                    
                    # Criterios de finalización
                    if (
                        loaded_rows >= total_expected or 
                        no_change_count >= 5 or 
                        coverage >= 95
                    ):
                        logger.info("✅ Carga de elementos completada")
                        break
                
                except Exception as detection_error:
                    logger.debug(f"Error detectando filas: {detection_error}")
            
            logger.info(f"🏁 Carga finalizada: {loaded_rows} filas de {total_expected} esperadas")
            return loaded_rows
        
        except Exception as e:
            logger.error(f"Error crítico en scroll: {e}")
            return 0
        
    def _click_show_more_buttons(self):
        """
        Método auxiliar para encontrar y hacer clic en botones 'Show More' o similares.
        
        Returns:
            bool: True si se hizo clic en al menos un botón, False en caso contrario
        """
        try:
            # Patrones de selectores para botones de carga adicional
            show_more_patterns = [
                "//span[contains(text(), 'Show More')]",
                "//button[contains(text(), 'Show More')]",
                "//div[contains(text(), 'Show More')]",
                "//span[contains(text(), 'Load More')]",
                "//button[contains(text(), 'Load More')]",
                "//span[contains(text(), 'Más')]",
                "//button[contains(text(), 'Más')]"
            ]
            
            for xpath in show_more_patterns:
                try:
                    buttons = self.driver.find_elements(By.XPATH, xpath)
                    for button in buttons:
                        if button.is_displayed():
                            logger.info(f"Haciendo clic en botón '{button.text}'")
                            
                            # Intentar JavaScript click primero
                            try:
                                self.driver.execute_script("arguments[0].click();", button)
                            except:
                                # Fallback a click normal
                                button.click()
                            
                            time.sleep(1.5)  # Esperar a que carguen nuevos elementos
                            return True
                except Exception as e:
                    logger.debug(f"Error con selector {xpath}: {e}")
            
            return False
        except Exception as e:
            logger.error(f"Error en búsqueda de botones 'Show More': {e}")
            return False





    def extract_row_data(row):
        """
        Extract data from a single row with robust column mapping for SAP UI5 table.
        
        Args:
            row (WebElement): Row WebElement to extract data from
        
        Returns:
            dict: Extracted row data or None
        """
        try:
            # Detailed column selectors for SAP UI5 table
            cell_selectors = [
                ".//div[@role='gridcell']",
                ".//td",
                ".//span[@role='gridcell']",
                ".//*[contains(@class, 'sapMListTblCell')]"
            ]
            
            # Precise column mapping based on the screenshot
            column_map = [
                'ISSUE TITLE', 'SAP CATEGORY', 'SO NUMBER', 'SESSION', 
                'PROJECT', 'SYSTEM ID', 'PRIORITY', 'DUE DATE', 
                'STATUS', 'COMMENT', 'LANGUAGE', 'ASSIGNED ROLE', 
                'CREATED BY', 'CREATED ON', 'LAST CHANGED BY', 
                'LAST CHANGED ON', 'SERVICE', 'DEADLINE'
            ]
            
            # Find cells using multiple strategies
            cells = None
            for selector in cell_selectors:
                try:
                    cells = row.find_elements(By.XPATH, selector)
                    if cells and len(cells) >= 5:  # Ensure we have meaningful data
                        break
                except Exception:
                    continue
            
            if not cells or len(cells) < 5:
                return None
            
            # Extract data with more robust text extraction
            row_data = {}
            for i, cell in enumerate(cells[:len(column_map)]):
                try:
                    # Multiple text extraction methods
                    text_methods = [
                        lambda c: c.text.strip(),
                        lambda c: c.get_attribute('textContent').strip(),
                        lambda c: c.get_attribute('innerText').strip(),
                        lambda c: c.get_attribute('title').strip()
                    ]
                    
                    cell_text = ''
                    for method in text_methods:
                        try:
                            cell_text = method(cell)
                            if cell_text:
                                break
                        except:
                            continue
                    
                    # Store in row data if meaningful
                    if cell_text and len(cell_text) > 1:
                        row_data[column_map[i]] = cell_text
                
                except Exception as cell_error:
                    logger.debug(f"Cell extraction error for column {column_map[i]}: {cell_error}")
            
            # Ensure we have meaningful data
            return row_data if len(row_data) > 3 else None
        
        except Exception as row_error:
            logger.error(f"Row extraction error: {row_error}")
            return None
        
        
        
        
                
    def wait_for_table_load(self, timeout=30):
        """
        Wait for table to load with multiple load indicators.
        
        Args:
            timeout (int): Maximum time to wait for table load, default 30 seconds
        
        Returns:
            bool: True if table loaded successfully
        """
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            from selenium.common.exceptions import TimeoutException

            load_indicators = [
                (By.XPATH, "//div[contains(@class, 'sapMListNoData')]"),
                (By.XPATH, "//div[contains(@class, 'sapUiLocalBusyIndicator')]"),
                (By.XPATH, "//*[@role='row']"),
                (By.XPATH, "//div[@role='gridcell']")
            ]
            
            # Intentar cargar al menos uno de los indicadores
            for indicator in load_indicators:
                try:
                    WebDriverWait(self.driver, timeout).until(
                        EC.presence_of_element_located(indicator)
                    )
                    return True
                except TimeoutException:
                    logger.debug(f"Indicador no encontrado: {indicator}")
                    continue
            
            logger.warning("No se encontraron indicadores de carga de tabla")
            return False
        
        except Exception as e:
            logger.error(f"Error al esperar la carga de la tabla: {e}")
            return False
        
    
    
    
    
    
    
    
    
    
    def advanced_table_detection():
        """
        Advanced table detection using JavaScript.
        
        Returns:
            bool: True if table detected
        """
        detection_script = """
        return (function() {
            const tables = document.querySelectorAll(
                '.sapMListTbl, [role="grid"], .sapUiTableCtrl'
            );
            return tables.length > 0;
        })();
        """
        return self.driver.execute_script(detection_script)

    def optimize_page_performance(self):
        """
        Optimize page performance for data extraction by disabling animations 
        and removing loading indicators.
        
        Returns:
            bool: True if optimization was successful
        """
        try:
            perf_script = """
            (function() {
                // Disable animations
                document.querySelectorAll('*').forEach(el => {
                    if (el.style) {
                        el.style.animationDuration = '0.001s';
                        el.style.transitionDuration = '0.001s';
                    }
                });
            
                // Remove loading indicators
                const indicators = [
                    '.sapUiLocalBusyIndicator',
                    '.sapMBusyIndicator'
                ];
            
                indicators.forEach(selector => {
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(el => {
                        el.style.display = 'none';
                    });
                });
            
                return true;
            })();
            """
            return self.driver.execute_script(perf_script)
        except Exception as e:
            logger.error(f"Error optimizing page performance: {e}")
            return False












    def find_table_rows_optimized(driver, highlight=False):
        """
        Encuentra filas de tabla en interfaces SAP UI5/Fiori con estrategias múltiples.
        
        Args:
            driver: WebDriver de Selenium
            highlight (bool): Si se debe resaltar la primera fila encontrada
        
        Returns:
            list: Lista de elementos WebElement que representan filas
        """
        try:
            logger.info("🔍 Buscando filas de tabla con selectores optimizados...")
            
            # Estrategias de selectores para encontrar filas
            row_selector_strategies = [
                # Selectores específicos de SAP UI5
                {
                    'selector': "//tr[contains(@class, 'sapMLIB') and not(contains(@class, 'sapMListTblHeader'))]",
                    'description': "Filas estándar SAP con clase sapMLIB"
                },
                {
                    'selector': "//div[@role='row' and not(contains(@class, 'sapUiTableHeaderRow'))]",
                    'description': "Filas con rol de fila en grid"
                },
                {
                    'selector': "//li[contains(@class, 'sapMLIB') and not(contains(@class, 'sapMListNoData'))]",
                    'description': "Filas en vista de lista SAP"
                },
                {
                    'selector': "//div[contains(@class, 'sapMListItems')]/div[contains(@class, 'sapMLIB')]",
                    'description': "Filas en contenedor de lista SAP"
                }
            ]
            
            # Encontrar filas válidas
            valid_rows = []
            for strategy in row_selector_strategies:
                try:
                    # Buscar elementos con el selector actual
                    rows = driver.find_elements(By.XPATH, strategy['selector'])
                    
                    # Filtrar filas válidas
                    filtered_rows = [
                        row for row in rows 
                        if (
                            row.is_displayed() and  # Visible
                            row.text and  # Tiene contenido
                            len(row.text.strip()) > 5  # Más de 5 caracteres
                        )
                    ]
                    
                    # Si encontramos filas, registrar y agregar
                    if filtered_rows:
                        logger.info(f"✅ Encontradas {len(filtered_rows)} filas con selector: {strategy['description']}")
                        valid_rows.extend(filtered_rows)
                        break  # Salir después de encontrar filas válidas
                
                except Exception as selector_error:
                    logger.debug(f"❌ Error con selector {strategy['selector']}: {selector_error}")
            
            # Método de último recurso: JavaScript para encontrar filas
            if not valid_rows:
                try:
                    js_rows_script = """
                    function findTableRows() {
                        const potentialRowSelectors = [
                            '.sapMLIB',
                            '[role="row"]',
                            '.sapMListItems > div',
                            'tr:not(.sapMListTblHeader)'
                        ];
                        
                        for (let selector of potentialRowSelectors) {
                            const rows = document.querySelectorAll(selector);
                            const validRows = Array.from(rows).filter(row => 
                                row.offsetParent !== null &&  // Visible
                                row.textContent.trim().length > 5  // Contenido significativo
                            );
                            
                            if (validRows.length > 0) {
                                return validRows;
                            }
                        }
                        
                        return [];
                    }
                    
                    return findTableRows();
                    """
                    
                    js_rows = driver.execute_script(js_rows_script)
                    
                    if js_rows:
                        logger.info(f"✅ Encontradas {len(js_rows)} filas mediante JavaScript")
                        valid_rows = js_rows
                
                except Exception as js_error:
                    logger.error(f"❌ Error en búsqueda JavaScript de filas: {js_error}")
            
            # Resaltar primera fila si se solicita
            if highlight and valid_rows:
                try:
                    driver.execute_script(
                        "arguments[0].style.border='3px solid red'", 
                        valid_rows[0]
                    )
                except:
                    logger.debug("No se pudo resaltar la primera fila")
            
            logger.info(f"🏁 Total de filas encontradas: {len(valid_rows)}")
            return valid_rows
        
        except Exception as e:
            logger.error(f"Error crítico al buscar filas: {e}")
            return []    
            
    def extract_issues_data_optimized(self):
        """
        Extrae datos de issues usando métodos optimizados con soporte para 18 columnas.
        
        Returns:
            list: Lista de diccionarios con los datos de cada issue
        """
        try:
            logger.info("Iniciando extracción optimizada de issues con soporte para 18 columnas...")
            
            # Esperar a que cargue la página inicial
            logger.info("Esperando que cargue la página inicial...")
            time.sleep(3)
            
            # Ejecutar optimizaciones en la página
            try:
                optimization_script = """
                // Deshabilitar animaciones
                document.querySelectorAll('*').forEach(el => {
                    if(el.style) {
                        el.style.animationDuration = '0.001s';
                        el.style.transitionDuration = '0.001s';
                    }
                });
                
                // Mejorar velocidad de scroll
                document.body.style.overflow = 'auto';
                
                // Deshabilitar indicadores de carga
                document.querySelectorAll('.sapUiLocalBusyIndicator').forEach(el => {
                    if(el) el.style.display = 'none';
                });
                
                return true;
                """
                self.driver.execute_script(optimization_script)
                logger.info("Página optimizada para extracción")
            except Exception as e:
                logger.debug(f"Error optimizando página: {e}")
            
            # Obtener el número exacto de issues desde la pestaña "Issues (X)"
            issue_count = None
            try:
                tab_element = self.driver.find_element(By.XPATH, "//div[contains(text(), 'Issues') and contains(text(), '(')]")
                tab_text = tab_element.text
                match = re.search(r'\((\d+)\)', tab_text)
                if match:
                    issue_count = int(match.group(1))
                    logger.info(f"Número exacto de issues según la pestaña: {issue_count}")
            except Exception as e:
                logger.warning(f"No se pudo determinar el número exacto de issues: {e}")
                issue_count = 100  # Valor predeterminado
                
                
                
                
                
                
                
                
                
                
                
                
    # Las filas ya deberían estar cargadas por el método scroll_to_load_all_items
            rows = find_table_rows_optimized(self.driver)
            
            if not rows:
                logger.warning("No se encontraron filas para extraer datos")
                return []
                
            logger.info(f"Procesando {len(rows)} filas encontradas")
            
            # Detectar encabezados para mapear columnas correctamente
            header_map = self._detect_table_headers_enhanced()
            logger.info(f"Encabezados detectados: {header_map}")
            
            # Extraer y procesar datos
            issues_data = []
            for index, row in enumerate(rows):
                try:
                    # Obtener celdas con método optimizado
                    cells = get_row_cells_optimized(row)
                    
                    if not cells or len(cells) < 3:
                        logger.debug(f"Fila {index} no tiene suficientes celdas, saltando...")
                        continue
                    
                    # Extraer datos de las celdas con soporte para 18 columnas
                    issue_data = self._extract_row_data_with_headers(cells, header_map)
                    
                    # Verificar que tenemos al menos un título (dato mínimo)
                    if not issue_data.get("Title"):
                        # Si no tenemos título, pero tenemos texto en la fila
                        row_text = row.text.strip() if row.text else ""
                        if row_text:
                            # Usar la primera línea como título
                            lines = row_text.split('\n')
                            issue_data["Title"] = lines[0]
                            
                            
                            
                            
                            
    # Filtrar elementos de control de UI
                    if issue_data.get("Title") and not any(control in issue_data["Title"].lower() 
                                            for control in ["show more", "show less", "load more"]):
                        issues_data.append(issue_data)
                    
                    # Actualizar progreso periódicamente
                    if (index + 1) % 20 == 0:
                        logger.info(f"Procesadas {index + 1} filas de {len(rows)}")
                    
                except Exception as e:
                    logger.debug(f"Error al procesar fila {index}: {e}")
            
            logger.info(f"Extracción completada: {len(issues_data)} issues extraídos")
            return issues_data
            
        except Exception as e:
            logger.error(f"Error en la extracción de datos: {e}")
            return []
        
        
        




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
            
        except Exception as e:
            logger.error(f"Error al detectar encabezados: {e}")
            return {}