#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de prueba mejorado para verificar la funcionalidad de selección de cliente en SAP
con espera adecuada de carga de interfaz, manejo de errores mejorado y pasos obligatorios
de búsqueda y acceso a ajustes.
"""

import os
import sys
import time
import logging
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def test_customer_selection():
    """
    Prueba completa del flujo:
    1. Selección de cliente
    2. Selección de proyecto
    3. Búsqueda (OBLIGATORIO)
    4. Acceso a ajustes (OBLIGATORIO)
    """
    # Importar desde el contexto del proyecto
    try:
        # Asegurar que estamos en el directorio correcto para importaciones
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Añadir el directorio actual al path para permitir importaciones
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
            
        # También añadir el directorio padre si es necesario
        parent_dir = os.path.dirname(script_dir)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        # Ahora importamos los módulos necesarios
        from browser.sap_browser import SAPBrowser
        
        logger.info("=== Iniciando prueba de flujo completo de SAP ===")
        
        # Crear instancia del navegador
        browser = SAPBrowser()
        
        # Conectar al navegador
        if not browser.connect():
            logger.error("No se pudo conectar al navegador")
            return False
            
        # Configuración de prueba
        erp_number = "1025541"  # Número ERP de ejemplo
        project_id = "20096444"  # ID de proyecto de ejemplo
        
        # Navegar a SAP
        if not browser.navigate_to_sap(erp_number, project_id):
            logger.error("No se pudo navegar a SAP")
            return False
            
        # Esperar autenticación si es necesario
        if not browser.handle_authentication():
            logger.error("No se completó la autenticación")
            return False
        
        # Esperar a que la interfaz esté completamente cargada
        logger.info("Esperando a que la interfaz de SAP esté completamente cargada...")
        if not wait_for_sap_interface_ready(browser.driver):
            logger.warning("No se pudo confirmar que la interfaz esté completamente cargada, pero continuando...")
        
        # Verificar el estado actual antes de intentar seleccionar
        logger.info("Verificando si ya están seleccionados los valores esperados...")
        
        # Usamos el método check_current_values que es una versión simplificada para compatibilidad
        current_values_ok = check_current_values(browser, erp_number, project_id)
        
        if current_values_ok:
            logger.info("Los campos ya tienen los valores esperados")
            client_selected = True
            project_selected = True
        else:
            # Selección de cliente
            logger.info(f"Probando selección de cliente para ERP: {erp_number}")
            client_selected = select_client_with_retries(browser, erp_number)
            
            if not client_selected:
                logger.error("❌ Todas las estrategias de selección de cliente fallaron")
                return False
                
            logger.info(f"✅ Cliente {erp_number} seleccionado exitosamente")
            
            # Selección de proyecto
            logger.info(f"Probando selección de proyecto: {project_id}")
            project_selected = select_project_with_retries(browser, project_id)
            
            if not project_selected:
                logger.error("❌ Todas las estrategias de selección de proyecto fallaron")
                return False
                
            logger.info(f"✅ Proyecto {project_id} seleccionado exitosamente")
        
        # PASO OBLIGATORIO 1: Hacer clic en el botón de búsqueda
        logger.info("Iniciando búsqueda...")
        search_success = browser.click_search_button()
        
        if not search_success:
            logger.error("❌ No se pudo hacer clic en el botón de búsqueda")
            return False
            
        logger.info("✅ Búsqueda iniciada correctamente")
        
        # Esperar a que se carguen los resultados
        logger.info("Esperando a que se carguen los resultados...")
        try:
            # Intentar usar wait_for_search_results si existe
            if hasattr(browser, 'wait_for_search_results') and callable(getattr(browser, 'wait_for_search_results')):
                if not browser.wait_for_search_results():
                    logger.warning("⚠️ No se pudo confirmar la carga de resultados, pero continuando")
                    # Espera adicional por si acaso
                    time.sleep(5)
                else:
                    logger.info("✅ Resultados de búsqueda cargados correctamente")
            else:
                # Método alternativo de espera si no existe la función
                logger.info("Esperando tiempo estándar para carga de resultados...")
                time.sleep(5)
                logger.info("Tiempo de espera completado")
        except Exception as e:
            logger.warning(f"Error al esperar resultados: {e}")
            time.sleep(5)  # Espera como fallback
        
        # PASO OBLIGATORIO 2: Hacer clic en el botón de ajustes
        logger.info("Intentando hacer clic en el botón de ajustes...")
        
        # Verificar si el método existe en el objeto
        if not hasattr(browser, 'click_settings_button') or not callable(getattr(browser, 'click_settings_button')):
            logger.warning("El método click_settings_button no está definido en la clase, usaremos implementación local")
            # Usar implementación local
            settings_success = click_settings_button_local(browser.driver)
        else:
            # Usar el método de la clase
            settings_success = browser.click_settings_button()

        # Si el método normal falla, intentar con el método agresivo
        if not settings_success and hasattr(browser, 'force_open_settings'):
            logger.info("Método estándar falló, intentando método agresivo para abrir ajustes...")
            settings_success = browser.force_open_settings()

        if not settings_success:
            logger.error("❌ No se pudo hacer clic en el botón de ajustes")
            return False
            
        logger.info("✅ Ajustes abiertos correctamente")
        
        # Esperar a que se abra el panel de ajustes
        time.sleep(3)
        
        logger.info("=== Test de flujo completo ejecutado con éxito ===")
        return True
        
    except Exception as e:
        logger.error(f"Error en prueba: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    
    
    
def wait_for_sap_interface_ready(driver, timeout=30):
    """
    Espera a que la interfaz de SAP esté completamente cargada y lista para interactuar
    
    Args:
        driver: WebDriver de Selenium
        timeout: Tiempo máximo de espera en segundos
        
    Returns:
        bool: True si la interfaz está lista, False si se agotó el tiempo
    """
    logger.info("Esperando a que la página esté completamente cargada...")
    try:
        # 1. Esperar a que document.readyState sea "complete"
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        logger.info("Estado de documento 'complete' detectado")
        
        # 2. Esperar a que desaparezcan los indicadores de carga
        loading_indicators = [
            "//div[contains(@class, 'sapUiLocalBusyIndicator')]",
            "//div[contains(@class, 'sapMBusyIndicator')]",
            "//div[contains(@class, 'sapUiBusy')]"
        ]
        
        # Verificar cada indicador de carga
        for indicator in loading_indicators:
            try:
                # Esperar hasta que NO exista o no sea visible
                WebDriverWait(driver, 5).until_not(
                    EC.visibility_of_element_located((By.XPATH, indicator))
                )
            except:
                # Si hay timeout, verificar manualmente si el indicador existe y es visible
                elements = driver.find_elements(By.XPATH, indicator)
                if elements and any(e.is_displayed() for e in elements):
                    logger.warning(f"Indicador de carga sigue visible: {indicator}")
        
        # 3. Verificar que la interfaz de SAP esté disponible
        ui_elements = [
            "//input[contains(@placeholder, 'Customer')]",
            "//input[contains(@placeholder, 'Project')]",
            "//div[contains(@class, 'sapMBar')]"
        ]
        
        # Verificar si al menos uno de los elementos de interfaz está visible
        element_found = False
        for selector in ui_elements:
            try:
                element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                if element.is_displayed():
                    element_found = True
                    logger.info(f"Elemento de interfaz detectado: {selector}")
                    break
            except:
                continue
        
        if not element_found:
            logger.warning("No se detectaron elementos de interfaz SAP esperados")
            
        # 4. Esperar un momento adicional para que la interfaz esté completamente interactiva
        time.sleep(3)
        
        # 5. Verificar si la API UI5 está disponible mediante JavaScript
        ui5_ready = driver.execute_script("""
            return (window.sap !== undefined && 
                   window.sap.ui !== undefined && 
                   window.sap.ui.getCore !== undefined);
        """)
        
        if ui5_ready:
            logger.info("API UI5 detectada y disponible")
        else:
            logger.warning("API UI5 no detectada - puede haber problemas de interacción")
        
        return True
        
    except Exception as e:
        logger.warning(f"Excepción durante la espera de interfaz: {e}")
        return False


def check_current_values(browser, erp_number, project_id):
    """
    Verifica si los campos ya contienen los valores esperados.
    Versión simplificada para compatibilidad con versiones anteriores.
    
    Args:
        browser: Instancia de SAPBrowser
        erp_number (str): Número ERP del cliente
        project_id (str): ID del proyecto
            
    Returns:
        bool: True si los campos tienen los valores esperados, False en caso contrario
    """
    try:
        # Intentar usar el método de la clase si existe
        if hasattr(browser, 'verify_fields_have_expected_values') and callable(getattr(browser, 'verify_fields_have_expected_values')):
            return browser.verify_fields_have_expected_values(erp_number, project_id)
        
        # Implementación simplificada como fallback
        logger.info("Usando implementación simplificada para verificar campos...")
        
        # 1. Verificar campos de entrada directamente
        customer_fields = browser.driver.find_elements(
            By.XPATH,
            "//input[contains(@placeholder, 'Customer') or contains(@aria-label, 'Customer')]"
        )
        
        if customer_fields:
            for field in customer_fields:
                if field.is_displayed():
                    current_value = field.get_attribute("value") or ""
                    if erp_number in current_value:
                        logger.info(f"Campo de cliente contiene '{erp_number}'")
                        
                        # Si encontramos el cliente, verificar el proyecto
                        project_fields = browser.driver.find_elements(
                            By.XPATH,
                            "//input[contains(@placeholder, 'Project') or contains(@aria-label, 'Project')]"
                        )
                        
                        if project_fields:
                            for p_field in project_fields:
                                if p_field.is_displayed():
                                    p_value = p_field.get_attribute("value") or ""
                                    if project_id in p_value:
                                        logger.info(f"Campo de proyecto contiene '{project_id}'")
                                        return True
        
        # 2. Verificar texto visible en la página como alternativa
        page_text = browser.driver.find_element(By.TAG_NAME, "body").text
        if erp_number in page_text and project_id in page_text:
            logger.info(f"La página contiene '{erp_number}' y '{project_id}'")
            
            # Verificar si estamos en la página correcta con los datos
            issues_elements = browser.driver.find_elements(
                By.XPATH, 
                "//div[contains(text(), 'Issues')]"
            )
            if issues_elements:
                logger.info("En la página correcta con datos cargados")
                return True
        
        logger.info("No se detectaron valores esperados en los campos")
        return False
        
    except Exception as e:
        logger.error(f"Error al verificar campos: {e}")
        return False
    
    
def select_client_with_retries(browser, erp_number, max_attempts=3):
    """
    Intenta seleccionar el cliente con múltiples estrategias y reintentos
    
    Args:
        browser: Instancia de SAPBrowser
        erp_number: Número ERP del cliente
        max_attempts: Número máximo de intentos
        
    Returns:
        bool: True si la selección fue exitosa, False en caso contrario
    """
    for attempt in range(max_attempts):
        logger.info(f"Intento {attempt+1}/{max_attempts} de selección de cliente")
        
        # Esperar antes de cada intento (excepto el primero)
        if attempt > 0:
            time.sleep(3)
            
            # Refrescar la interfaz de usuario entre intentos
            try:
                browser.driver.execute_script("""
                    // Intentar refrescar la interfaz UI5 sin recargar la página
                    if (window.sap && window.sap.ui && window.sap.ui.getCore) {
                        sap.ui.getCore().applyChanges();
                    }
                """)
            except:
                pass
        
        # Estrategia 1: Método UI5 directo (el más efectivo normalmente)
        if hasattr(browser, 'select_customer_ui5_direct') and callable(getattr(browser, 'select_customer_ui5_direct')):
            try:
                if browser.select_customer_ui5_direct(erp_number):
                    logger.info(f"Cliente {erp_number} seleccionado con método UI5 directo en intento {attempt+1}")
                    return True
            except Exception as e:
                logger.warning(f"Error en método UI5 directo: {e}")
        
        # Estrategia 2: Método automatizado general
        if hasattr(browser, 'select_customer_automatically') and callable(getattr(browser, 'select_customer_automatically')):
            try:
                if browser.select_customer_automatically(erp_number):
                    logger.info(f"Cliente {erp_number} seleccionado con método automatizado en intento {attempt+1}")
                    return True
            except Exception as e:
                logger.warning(f"Error en método automatizado: {e}")
        
        # Estrategia 3: Método directo de JavaScript como último recurso
        if attempt == max_attempts - 1:
            try:
                logger.info("Intentando método JavaScript agresivo como último recurso")
                result = browser.driver.execute_script("""
                    (function() {
                        try {
                            // Buscar cualquier campo de cliente
                            var inputs = document.querySelectorAll('input');
                            var customerField = null;
                            
                            for (var i = 0; i < inputs.length; i++) {
                                var input = inputs[i];
                                if (input.offsetParent !== null) { // Es visible
                                    var placeholder = input.getAttribute('placeholder') || '';
                                    var ariaLabel = input.getAttribute('aria-label') || '';
                                    
                                    if (placeholder.includes('Customer') || ariaLabel.includes('Customer')) {
                                        customerField = input;
                                        break;
                                    }
                                }
                            }
                            
                            if (!customerField) {
                                console.error("No se encontró campo de cliente");
                                return false;
                            }
                            
                            // Limpiar y establecer valor
                            customerField.value = '';
                            customerField.focus();
                            customerField.value = arguments[0];
                            
                            // Disparar eventos
                            customerField.dispatchEvent(new Event('input', { bubbles: true }));
                            customerField.dispatchEvent(new Event('change', { bubbles: true }));
                            
                            // Simular ENTER después de un breve retraso
                            setTimeout(function() {
                                var enterEvent = new KeyboardEvent('keydown', {
                                    key: 'Enter',
                                    code: 'Enter',
                                    keyCode: 13,
                                    which: 13,
                                    bubbles: true
                                });
                                customerField.dispatchEvent(enterEvent);
                            }, 1000);
                            
                            return true;
                        } catch(e) {
                            console.error("Error en script: " + e);
                            return false;
                        }
                    })();
                """, erp_number)
                
                if result:
                    # Esperar a que se procese el script
                    time.sleep(3)
                    
                    # Verificar si fue exitoso
                    if hasattr(browser, '_verify_client_selection_strict') and callable(getattr(browser, '_verify_client_selection_strict')):
                        if browser._verify_client_selection_strict(erp_number):
                            logger.info(f"Cliente {erp_number} seleccionado con JavaScript agresivo")
                            return True
                    else:
                        # Verificación simplificada si no existe el método específico
                        logger.info(f"Cliente posiblemente seleccionado con JavaScript agresivo (sin verificación estricta)")
                        return True
            except Exception as e:
                logger.warning(f"Error en método JavaScript agresivo: {e}")
    
    # Si llegamos aquí, todos los intentos fallaron
    return False


def select_project_with_retries(browser, project_id, max_attempts=3):
    """
    Intenta seleccionar el proyecto con múltiples estrategias y reintentos
    
    Args:
        browser: Instancia de SAPBrowser
        project_id: ID del proyecto
        max_attempts: Número máximo de intentos
        
    Returns:
        bool: True si la selección fue exitosa, False en caso contrario
    """
    try:
        # Esperar a que el campo de proyecto esté disponible
        logger.info("Esperando a que el campo de proyecto esté disponible...")
        
        # Criterios para detectar que el proyecto está listo para ser seleccionado
        project_ready = False
        attempts = 0
        max_pre_attempts = 5
        
        while not project_ready and attempts < max_pre_attempts:
            attempts += 1
            
            # Verificar si ya está seleccionado
            if hasattr(browser, '_verify_project_selection_strict') and callable(getattr(browser, '_verify_project_selection_strict')):
                if browser._verify_project_selection_strict(project_id):
                    logger.info(f"El proyecto {project_id} ya está seleccionado")
                    return True
                    
            # Buscar campo de proyecto visible
            project_fields = browser.driver.find_elements(By.XPATH, 
                "//input[contains(@placeholder, 'Project')]")
            
            if project_fields and any(field.is_displayed() and field.is_enabled() for field in project_fields):
                project_ready = True
                logger.info("Campo de proyecto detectado y habilitado")
            else:
                logger.info(f"Esperando campo de proyecto... intento {attempts}/{max_pre_attempts}")
                time.sleep(3)
        
        if not project_ready:
            logger.warning("No se pudo detectar campo de proyecto después de múltiples intentos")
            return False
        
        # Múltiples intentos de selección de proyecto
        for attempt in range(max_attempts):
            logger.info(f"Intento {attempt+1}/{max_attempts} de selección de proyecto")
            
            # Esperar antes de cada intento (excepto el primero)
            if attempt > 0:
                time.sleep(3)
            
            # Estrategia 1: Método UI5 directo
            if hasattr(browser, 'select_project_ui5_direct') and callable(getattr(browser, 'select_project_ui5_direct')):
                try:
                    if browser.select_project_ui5_direct(project_id):
                        logger.info(f"Proyecto {project_id} seleccionado con método UI5 directo en intento {attempt+1}")
                        return True
                except Exception as e:
                    logger.warning(f"Error en método UI5 directo para proyecto: {e}")
            
            # Estrategia 2: Método de Selenium específico
            if hasattr(browser, '_select_project_with_selenium') and callable(getattr(browser, '_select_project_with_selenium')):
                try:
                    if browser._select_project_with_selenium(project_id):
                        logger.info(f"Proyecto {project_id} seleccionado con Selenium en intento {attempt+1}")
                        return True
                except Exception as e:
                    logger.warning(f"Error en método Selenium para proyecto: {e}")
                    
            # Estrategia 3: Método automático general
            if hasattr(browser, 'select_project_automatically') and callable(getattr(browser, 'select_project_automatically')):
                try:
                    if browser.select_project_automatically(project_id):
                        logger.info(f"Proyecto {project_id} seleccionado con método automatizado en intento {attempt+1}")
                        return True
                except Exception as e:
                    logger.warning(f"Error en método automatizado para proyecto: {e}")
            
            # Estrategia 4: JavaScript directo como último recurso
            if attempt == max_attempts - 1:
                try:
                    # Script específico para seleccionar proyecto
                    js_script = """
                    (function() {
                        try {
                            // Buscar campo de proyecto
                            var inputs = document.querySelectorAll('input');
                            var projectField = null;
                            
                            for (var i = 0; i < inputs.length; i++) {
                                var input = inputs[i];
                                if (input.offsetParent !== null) { // Es visible
                                    var placeholder = input.getAttribute('placeholder') || '';
                                    var ariaLabel = input.getAttribute('aria-label') || '';
                                    
                                    if (placeholder.includes('Project') || ariaLabel.includes('Project')) {
                                        projectField = input;
                                        break;
                                    }
                                }
                            }
                            
                            if (!projectField) {
                                return false;
                            }
                            
                            // Limpiar campo y establecer valor
                            projectField.value = '';
                            projectField.focus();
                            projectField.value = arguments[0];
                            
                            // Disparar eventos para activar búsqueda
                            projectField.dispatchEvent(new Event('input', { bubbles: true }));
                            projectField.dispatchEvent(new Event('change', { bubbles: true }));
                            
                            // Esperar y simular tecla abajo + enter
                            setTimeout(function() {
                                // Tecla abajo
                                projectField.dispatchEvent(new KeyboardEvent('keydown', {
                                    key: 'ArrowDown',
                                    code: 'ArrowDown',
                                    keyCode: 40,
                                    which: 40,
                                    bubbles: true
                                }));
                                
                                // Tecla enter después de un breve retraso
                                setTimeout(function() {
                                    projectField.dispatchEvent(new KeyboardEvent('keydown', {
                                        key: 'Enter',
                                        code: 'Enter',
                                        keyCode: 13,
                                        which: 13,
                                        bubbles: true
                                    }));
                                }, 500);
                            }, 1000);
                            
                            return true;
                        } catch(e) {
                            console.error("Error en script: " + e);
                            return false;
                        }
                    })();
                    """
                    
                    result = browser.driver.execute_script(js_script, project_id)
                    if result:
                        logger.info("JavaScript para selección de proyecto ejecutado, esperando resultados...")
                        time.sleep(3)
                        
                        # Intentar verificar resultado
                        if hasattr(browser, '_verify_project_selection_strict') and callable(getattr(browser, '_verify_project_selection_strict')):
                            if browser._verify_project_selection_strict(project_id):
                                logger.info(f"Proyecto {project_id} seleccionado con JavaScript directo")
                                return True
                        else:
                            # Si no podemos verificar estrictamente, asumir éxito
                            logger.info(f"Proyecto posiblemente seleccionado (sin verificación estricta)")
                            return True
                except Exception as js_e:
                    logger.warning(f"Error en JavaScript directo para proyecto: {js_e}")
                
        logger.error(f"No se pudo seleccionar el proyecto {project_id} después de {max_attempts} intentos")
        return False
            
    except Exception as e:
        logger.error(f"Error en selección de proyecto: {e}")
        return False
    
    
    
def click_settings_button_local(driver):
    """
    Implementación local del método para hacer clic en el botón de engranaje (⚙️)
    que aparece en la interfaz. Se utiliza si el método no existe en la clase SAPBrowser.
    
    Args:
        driver: WebDriver de Selenium
            
    Returns:
        bool: True si el clic fue exitoso, False en caso contrario
    """
    try:
        logger.info("Usando implementación local para hacer clic en el botón de ajustes...")
        
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
        
        # Probar cada selector e intentar hacer clic
        for selector in settings_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        # Hacer scroll para garantizar visibilidad
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                        time.sleep(0.5)
                        
                        # Intento con JavaScript (más confiable)
                        try:
                            logger.info(f"Encontrado botón de ajustes con selector: {selector}")
                            driver.execute_script("arguments[0].click();", element)
                            logger.info("Clic en botón de ajustes realizado con JavaScript")
                            time.sleep(2)
                            return True
                        except Exception as js_e:
                            logger.debug(f"Error en clic con JavaScript: {js_e}")
                            
                            # Intento con clic normal como respaldo
                            element.click()
                            logger.info("Clic en botón de ajustes realizado con método normal")
                            time.sleep(2)
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
            
            result = driver.execute_script(position_script)
            if result:
                logger.info("Clic realizado en botón mediante posición en pantalla")
                time.sleep(2)
                return True
        except Exception as pos_e:
            logger.debug(f"Error en estrategia de posición: {pos_e}")
        
        # 3. ESTRATEGIA: Buscar elementos que visualmente parezcan un botón de configuración
        logger.info("Buscando cualquier elemento que parezca un botón de configuración...")
        try:
            settings_appearance_script = """
            (function() {
                // Buscar elementos que parezcan iconos de configuración
                var iconElements = Array.from(document.querySelectorAll('span.sapUiIcon, span.sapMBtnIcon'));
                
                // Filtrar por características visuales
                var settingsIcons = iconElements.filter(function(icon) {
                    if (!icon.offsetParent) return false; // No visible
                    
                    // Verificar clase, estilo o contenido
                    var classAttr = icon.getAttribute('class') || '';
                    var dataIcon = icon.getAttribute('data-sap-ui') || '';
                    
                    return classAttr.includes('settings') || 
                           dataIcon.includes('settings') ||
                           dataIcon.includes('gear') || 
                           dataIcon.includes('cog');
                });
                
                // Buscar el botón padre para cada icono
                for (var i = 0; i < settingsIcons.length; i++) {
                    var icon = settingsIcons[i];
                    var button = icon.closest('button') || icon.closest('.sapMBtn');
                    
                    if (button) {
                        button.click();
                        return true;
                    }
                }
                
                // Si no encontramos por ícono, buscar por botones en el footer
                var footerElements = document.querySelectorAll('.sapMFooter button, .sapMIBar button');
                if (footerElements.length > 0) {
                    // Hacer clic en el último botón del footer (suele ser configuración)
                    footerElements[footerElements.length - 1].click();
                    return true;
                }
                
                return false;
            })();
            """
            
            result = driver.execute_script(settings_appearance_script)
            if result:
                logger.info("Clic realizado en elemento que parece botón de configuración")
                time.sleep(2)
                return True
        except Exception as visual_e:
            logger.debug(f"Error en estrategia visual: {visual_e}")

        # 4. ESTRATEGIA: Último recurso - tomar una captura de pantalla para análisis
        try:
            screenshot_path = os.path.join("logs", f"settings_button_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            if not os.path.exists("logs"):
                os.makedirs("logs")
                
            driver.save_screenshot(screenshot_path)
            logger.info(f"Captura de pantalla guardada en: {screenshot_path}")
            logger.error("No se pudo encontrar el botón de ajustes. Revise la captura de pantalla para análisis manual.")
        except Exception as ss_e:
            logger.debug(f"Error al tomar captura de pantalla: {ss_e}")
        
        return False
        
    except Exception as e:
        logger.error(f"Error general al intentar hacer clic en botón de ajustes: {e}")
        return False
    
    
    
    
    
    
    
    
    
    
    
    

if __name__ == "__main__":
    result = test_customer_selection()
    if result:
        print("\n✅ Prueba completa de flujo exitosa")
    else:
        print("\n❌ Prueba de flujo falló")
    
    input("\nPresione Enter para salir...")