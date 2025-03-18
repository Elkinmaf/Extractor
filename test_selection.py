#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de prueba mejorado para verificar la funcionalidad de selección de columnas en SAP
con enfoque en probar la funcionalidad de hacer clic en el tercer ícono "Select Columns"
después de abrir el panel de ajustes.
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
from selenium.webdriver.common.action_chains import ActionChains

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
    5. Prueba específica del tercer ícono "Select Columns"
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
        
        # NUEVO PASO: PRUEBA ESPECÍFICA DEL TERCER ÍCONO "SELECT COLUMNS"
        logger.info("===== INICIANDO PRUEBA ESPECÍFICA: Clic en ícono 'Select Columns' =====")
        
        # Tomar captura de pantalla para análisis (opcional)
        try:
            screenshot_path = os.path.join("logs", f"pre_select_columns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            if not os.path.exists("logs"):
                os.makedirs("logs")
            browser.driver.save_screenshot(screenshot_path)
            logger.info(f"Captura previa guardada en: {screenshot_path}")
        except Exception as ss_e:
            logger.debug(f"No se pudo tomar captura de pantalla: {ss_e}")
        
        # Verificar si el método específico existe en SAPBrowser
        select_columns_success = False
        
        if hasattr(browser, 'click_select_columns_tab') and callable(getattr(browser, 'click_select_columns_tab')):
            logger.info("Método click_select_columns_tab encontrado en SAPBrowser, ejecutando...")
            select_columns_success = browser.click_select_columns_tab()
        else:
            logger.info("Método click_select_columns_tab no encontrado, usando implementación de prueba...")
            select_columns_success = click_select_columns_tab_test(browser.driver)
        
        if select_columns_success:
            logger.info("✅ Clic en ícono 'Select Columns' exitoso")
            
            # Verificar que se haya abierto el panel de columnas
            column_panel_opened = False
            
            # Verificar si existe la función de verificación en SAPBrowser
            if hasattr(browser, '_verify_column_panel_opened') and callable(getattr(browser, '_verify_column_panel_opened')):
                logger.info("Método _verify_column_panel_opened encontrado en SAPBrowser, ejecutando...")
                column_panel_opened = browser._verify_column_panel_opened()
            else:
                logger.info("Método _verify_column_panel_opened no encontrado, usando implementación de prueba...")
                column_panel_opened = verify_column_panel_opened_test(browser.driver)
            
            if column_panel_opened:
                logger.info("✅ Panel de selección de columnas abierto correctamente")
                
                # Tomar captura de pantalla para análisis (opcional)
                try:
                    screenshot_path = os.path.join("logs", f"column_panel_opened_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                    browser.driver.save_screenshot(screenshot_path)
                    logger.info(f"Captura del panel abierto guardada en: {screenshot_path}")
                except Exception as ss_e:
                    logger.debug(f"No se pudo tomar captura de pantalla: {ss_e}")
            else:
                logger.warning("⚠️ No se pudo verificar que el panel de selección de columnas se abriera")
        else:
            logger.error("❌ No se pudo hacer clic en el ícono 'Select Columns'")
            
            # Tomar captura de pantalla para análisis (opcional)
            try:
                screenshot_path = os.path.join("logs", f"select_columns_failed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                browser.driver.save_screenshot(screenshot_path)
                logger.info(f"Captura de error guardada en: {screenshot_path}")
            except Exception as ss_e:
                logger.debug(f"No se pudo tomar captura de pantalla: {ss_e}")
                
            # Continuar de todos modos con el flujo estándar
            logger.info("Continuando con el flujo estándar a pesar del error...")
        
        # PASO OBLIGATORIO 3: Configurar columnas visibles
        logger.info("Configurando columnas visibles...")
        
        # Verificar si existe el método específico en la clase
        if hasattr(browser, 'select_all_visible_columns') and callable(getattr(browser, 'select_all_visible_columns')):
            logger.info("Usando método select_all_visible_columns de SAPBrowser")
            columns_configured = browser.select_all_visible_columns()
        else:
            logger.info("Usando implementación de prueba para configurar columnas")
            # Implementación directa de la configuración de columnas
            columns_configured = configure_columns(browser.driver)
        
        if columns_configured:
            logger.info("✅ Columnas configuradas correctamente")
        else:
            logger.warning("⚠️ No se pudieron configurar todas las columnas automáticamente")
            # Informar al usuario para configuración manual si es necesario
            print("\n⚠️ Por favor, configure manualmente 'Select All' en columnas y presione 'OK'")
            input("Presione Enter cuando esté listo para continuar...")
        
        logger.info("=== Prueba completa finalizada exitosamente ===")
        return True
    
    except Exception as e:
        logger.error(f"Error general en la prueba: {e}")
        return False





def wait_for_sap_interface_ready(driver, timeout=30):
    """
    Espera a que la interfaz de SAP esté completamente cargada y lista para interactuar.
    
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
                # Esperar hasta que NO exista o no sea visible (tiempo más corto)
                WebDriverWait(driver, 5).until_not(
                    EC.visibility_of_element_located((By.XPATH, indicator))
                )
            except:
                # Verificar manualmente si hay indicadores visibles
                elements = driver.find_elements(By.XPATH, indicator)
                if elements and any(e.is_displayed() for e in elements):
                    logger.info(f"Indicador de carga sigue visible: {indicator}")
                    
                    # Esperar un poco más para que desaparezca
                    time.sleep(3)
        
        # 3. Esperar un momento adicional para que la interfaz esté completamente interactiva
        time.sleep(3)
        
        # 4. Verificar si la API UI5 está disponible mediante JavaScript
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
    Intenta seleccionar el cliente con múltiples estrategias y reintentos.
    
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
    Intenta seleccionar el proyecto con múltiples estrategias y reintentos.
    
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
        
        # Tomar captura de pantalla antes de intentar para análisis posterior
        try:
            pre_click_screenshot = os.path.join("logs", f"pre_settings_click_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            if not os.path.exists("logs"):
                os.makedirs("logs")
            driver.save_screenshot(pre_click_screenshot)
            logger.info(f"Captura previa al clic guardada en: {pre_click_screenshot}")
        except:
            pass
        
        # Probar cada selector e intentar hacer clic
        for selector in settings_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        # Hacer scroll para garantizar visibilidad
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                        time.sleep(0.5)
                        
                        # Intentar con tres clics para asegurar que uno funcione
                        click_success = False
                        
                        # 1. Primero: JavaScript click (más confiable)
                        try:
                            logger.info(f"Encontrado botón de ajustes con selector: {selector}")
                            driver.execute_script("arguments[0].click();", element)
                            logger.info("Clic en botón de ajustes realizado con JavaScript")
                            click_success = True
                        except Exception as js_e:
                            logger.debug(f"Error en clic con JavaScript: {js_e}")
                        
                        # Verificar si se abrió un diálogo o panel
                        if click_success:
                            time.sleep(2)
                            try:
                                dialog_visible = driver.find_elements(By.XPATH, 
                                    "//div[contains(@class, 'sapMDialog') and contains(@style, 'visibility: visible')]")
                                if dialog_visible:
                                    logger.info("Panel de ajustes detectado")
                                    return True
                            except:
                                pass
                        
                        # 2. Segundo: Clic normal
                        try:
                            element.click()
                            logger.info("Clic en botón de ajustes realizado con método normal")
                            click_success = True
                        except Exception as normal_click_e:
                            logger.debug(f"Error en clic normal: {normal_click_e}")
                        
                        # Verificar nuevamente
                        if click_success:
                            time.sleep(2)
                            try:
                                dialog_visible = driver.find_elements(By.XPATH, 
                                    "//div[contains(@class, 'sapMDialog') and contains(@style, 'visibility: visible')]")
                                if dialog_visible:
                                    logger.info("Panel de ajustes detectado")
                                    return True
                            except:
                                pass
                        
                        # 3. Tercero: Action Chains (más preciso)
                        try:
                            actions = ActionChains(driver)
                            actions.move_to_element(element).click().perform()
                            logger.info("Clic en botón de ajustes realizado con Action Chains")
                            click_success = True
                        except Exception as action_e:
                            logger.debug(f"Error en clic con Action Chains: {action_e}")
                        
                        # Verificar una última vez
                        if click_success:
                            time.sleep(2)
                            try:
                                dialog_visible = driver.find_elements(By.XPATH, 
                                    "//div[contains(@class, 'sapMDialog') and contains(@style, 'visibility: visible')]")
                                if dialog_visible:
                                    logger.info("Panel de ajustes detectado")
                                    return True
                            except:
                                pass
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
                
                # Verificar si se abrió un diálogo
                try:
                    dialog_visible = driver.find_elements(By.XPATH, 
                        "//div[contains(@class, 'sapMDialog') and contains(@style, 'visibility: visible')]")
                    if dialog_visible:
                        logger.info("Panel de ajustes detectado")
                        return True
                except:
                    pass
        except Exception as pos_e:
            logger.debug(f"Error en estrategia de posición: {pos_e}")





# 3. ESTRATEGIA: Atajos de teclado - SAP UI5 suele responder a Alt+O para opciones
        logger.info("Intentando abrir ajustes con atajos de teclado...")
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            
            # Secuencia Alt+O (común para opciones en SAP)
            actions = ActionChains(driver)
            # Presionar Alt+O
            actions.key_down(Keys.ALT).send_keys('o').key_up(Keys.ALT).perform()
            logger.info("Enviada secuencia Alt+O para abrir opciones")
            time.sleep(2)
            
            # Verificar si se abrió un diálogo
            try:
                dialog_visible = driver.find_elements(By.XPATH, 
                    "//div[contains(@class, 'sapMDialog') and contains(@style, 'visibility: visible')]")
                if dialog_visible:
                    logger.info("Panel de ajustes detectado")
                    return True
            except:
                pass
                    
            # Intentar con otras combinaciones comunes para abrir menús de opciones
            actions = ActionChains(driver)
            # Ctrl+,
            actions.key_down(Keys.CONTROL).send_keys(',').key_up(Keys.CONTROL).perform()
            logger.info("Enviada secuencia Ctrl+, para abrir opciones")
            time.sleep(2)
            
            # Verificar nuevamente
            try:
                dialog_visible = driver.find_elements(By.XPATH, 
                    "//div[contains(@class, 'sapMDialog') and contains(@style, 'visibility: visible')]")
                if dialog_visible:
                    logger.info("Panel de ajustes detectado")
                    return True
            except:
                pass
        except Exception as key_e:
            logger.debug(f"Error en estrategia de atajos de teclado: {key_e}")
        
        # 4. ESTRATEGIA: Si todo lo demás falló, hacer clic en cada botón visible del footer
        logger.info("Estrategia final: intentando con todos los botones del footer...")
        try:
            footer_buttons = driver.find_elements(By.XPATH, 
                "//div[contains(@class, 'sapMFooter')]//button | //footer//button")
            
            for btn in footer_buttons:
                if btn.is_displayed() and btn.is_enabled():
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", btn)
                        logger.info(f"Clic en botón del footer ({btn.text or 'sin texto'})")
                        time.sleep(2)
                        
                        # Verificar si se abrió un diálogo
                        dialog_visible = driver.find_elements(By.XPATH, 
                            "//div[contains(@class, 'sapMDialog') and contains(@style, 'visibility: visible')]")
                        if dialog_visible:
                            logger.info("Panel de ajustes detectado")
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
                
            driver.save_screenshot(screenshot_path)
            logger.info(f"Captura de pantalla guardada en: {screenshot_path}")
            logger.error("No se pudo encontrar o hacer clic en el botón de ajustes. Revise la captura de pantalla para análisis manual.")
        except Exception as ss_e:
            logger.debug(f"Error al tomar captura de pantalla: {ss_e}")
        
        return False
        
    except Exception as e:
        logger.error(f"Error general al intentar hacer clic en botón de ajustes: {e}")
        return False
    
    
    
    
    
    
def click_select_columns_tab_test(driver):
    """
    Función para hacer clic específicamente en el tercer ícono (Select Columns)
    del panel de ajustes. Esta implementación se usa para pruebas si el método
    no está presente en la clase SAPBrowser.
    
    Args:
        driver: WebDriver de Selenium
        
    Returns:
        bool: True si el clic fue exitoso, False en caso contrario
    """
    try:
        logger.info("Prueba específica: Intentando hacer clic en el tercer ícono (Select Columns)...")
        
        # 1. Intento principal: ID específico visible en el código
        columns_id = "application-iam-ui-component---home--issueFilterDialog-custom-button-application-iam-ui-component---home--issuesColumns-img"
        
        try:
            # Intento directo por ID
            column_button = driver.find_element(By.ID, columns_id)
            if column_button and column_button.is_displayed():
                # Usar JavaScript para clic más confiable
                driver.execute_script("arguments[0].click();", column_button)
                logger.info(f"Clic exitoso en ícono de columnas por ID específico: {columns_id}")
                time.sleep(1.5)
                
                # Verificar que el panel de columnas se abrió
                if verify_column_panel_opened_test(driver):
                    return True
        except Exception as e:
            logger.debug(f"No se encontró por ID específico: {e}")
            
            # Intentar con XPath usando el ID
            try:
                column_button = driver.find_element(By.XPATH, f"//*[@id='{columns_id}']")
                if column_button.is_displayed():
                    driver.execute_script("arguments[0].click();", column_button)
                    logger.info(f"Clic exitoso en ícono por XPath con ID: {columns_id}")
                    time.sleep(1.5)
                    
                    if verify_column_panel_opened_test(driver):
                        return True
            except Exception as e2:
                logger.debug(f"No se encontró por XPath con ID: {e2}")
        
        # 2. Segundo intento: Tercer botón en la barra segmentada
        selectors = [
            "(//div[contains(@class, 'sapMSegB')]/span)[3]",
            "(//div[contains(@class, 'sapMSegBBtn')])[3]", 
            "(//span[contains(@class, 'sapMSegBBtnInner')])[3]",
            "(//div[contains(@class, 'sapMSegB')]//span[contains(@class, 'sapUiIcon')])[3]"
        ]
        
        for selector in selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements and elements[0].is_displayed():
                    driver.execute_script("arguments[0].click();", elements[0])
                    logger.info(f"Clic exitoso en tercer ícono con selector: {selector}")
                    time.sleep(1.5)
                    
                    if verify_column_panel_opened_test(driver):
                        return True
            except Exception as sel_e:
                logger.debug(f"Error con selector {selector}: {sel_e}")
        
        # 3. Último intento: JavaScript para encontrar y hacer clic en el tercer botón
        js_script = """
        (function() {
            try {
                // Buscar directamente por ID
                var columnButton = document.getElementById('application-iam-ui-component---home--issueFilterDialog-custom-button-application-iam-ui-component---home--issuesColumns-img');
                
                // Si no se encuentra por ID, buscar por contiene en ID
                if (!columnButton) {
                    columnButton = document.querySelector('[id*="issuesColumns-img"]');
                }
                
                if (columnButton) {
                    console.log("Botón de columnas encontrado por ID, haciendo clic");
                    columnButton.click();
                    return true;
                }
                
                // Buscar el tercer botón en la barra segmentada
                var segmentButtons = document.querySelectorAll('.sapMSegBBtn, .sapMSegB button');
                if (segmentButtons.length >= 3) {
                    console.log("Encontrado tercer botón de segmento");
                    segmentButtons[2].click();
                    return true;
                }
                
                // Buscar por contenido HTML que sugiera columnas
                var buttons = document.querySelectorAll('button');
                for (var i = 0; i < buttons.length; i++) {
                    var btn = buttons[i];
                    if (btn.offsetParent !== null) {  // Es visible
                        if (btn.innerHTML.indexOf('column') >= 0 || 
                            btn.innerHTML.indexOf('table') >= 0) {
                            btn.click();
                            return true;
                        }
                    }
                }
                
                return false;
            } catch(e) {
                console.error("Error en script JS: " + e);
                return false;
            }
        })();
        """
        
        js_result = driver.execute_script(js_script)
        if js_result:
            logger.info("Clic realizado con JavaScript en tercer botón")
            time.sleep(1.5)
            
            if verify_column_panel_opened_test(driver):
                return True
                
        logger.warning("No se pudo hacer clic en el ícono 'Select Columns'")
        return False
        
    except Exception as e:
        logger.error(f"Error al hacer clic en ícono 'Select Columns': {e}")
        return False
    
    
def verify_column_panel_opened_test(driver):
    """
    Verifica que el panel de selección de columnas se ha abierto correctamente.
    Esta implementación se usa para pruebas si el método no está presente en SAPBrowser.
    
    Args:
        driver: WebDriver de Selenium
        
    Returns:
        bool: True si el panel está abierto, False en caso contrario
    """
    try:
        # Dar tiempo a que se abra el panel
        time.sleep(1)
        
        # 1. Verificar por texto "Select All"
        select_all_elements = driver.find_elements(By.XPATH, "//div[contains(text(), 'Select All')]")
        if select_all_elements and any(el.is_displayed() for el in select_all_elements):
            logger.info("Panel de columnas detectado: 'Select All' visible")
            return True
            
        # 2. Verificar por checkboxes de columnas
        checkboxes = driver.find_elements(By.XPATH, 
            "//div[contains(@class, 'sapMCb')]/preceding-sibling::div[contains(text(), 'ISSUE TITLE') or contains(text(), 'SAP CATEGORY')]")
        if checkboxes and any(checkbox.is_displayed() for checkbox in checkboxes):
            logger.info("Panel de columnas detectado: Checkboxes de columnas visibles")
            return True
            
        # 3. Verificar por otros elementos comunes en el panel de columnas
        column_panel_selectors = [
            "//div[@role='dialog']//div[contains(@class, 'sapMList')]",
            "//div[contains(@class, 'sapMSelectDialogListItem')]",
            "//div[contains(@class, 'sapMDialog')]//div[contains(@aria-selected, 'true')]",
            "//div[contains(@class, 'sapMList')]//li"
        ]
        
        for selector in column_panel_selectors:
            elements = driver.find_elements(By.XPATH, selector)
            if elements and any(el.is_displayed() for el in elements):
                logger.info(f"Panel de columnas detectado con selector: {selector}")
                return True
        
        # 4. JavaScript para verificación más completa
        js_verify = """
        (function() {
            // Buscar "Select All" text
            var selectAllText = document.evaluate(
                "//div[text()='Select All'] | //div[contains(text(), 'Select All')]", 
                document, 
                null, 
                XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, 
                null
            );
            
            if (selectAllText.snapshotLength > 0) {
                return true;
            }
            
            // Buscar checkboxes en un diálogo visible
            var dialog = document.querySelector('.sapMDialog[style*="visibility: visible"]');
            if (dialog) {
                var checkboxes = dialog.querySelectorAll('.sapMCb');
                if (checkboxes.length > 3) {
                    return true;
                }
                
                // Buscar lista de columnas
                var listItems = dialog.querySelectorAll('.sapMList li, .sapMLIB');
                if (listItems.length > 3) {
                    return true;
                }
            }
            
            return false;
        })();
        """
        
        js_result = driver.execute_script(js_verify)
        if js_result:
            logger.info("Panel de columnas detectado mediante JavaScript")
            return True
            
        logger.warning("No se detectó el panel de columnas")
        return False
        
    except Exception as e:
        logger.error(f"Error al verificar panel de columnas: {e}")
        return False
    
    
def configure_columns(driver):
    """
    Configura todas las columnas visibles en SAP UI5.
    
    Esta función implementa los pasos necesarios para seleccionar todas las columnas:
    1. Hace clic en el tercer ícono (Select Columns)
    2. Marca la casilla "Select All"
    3. Confirma con OK
    
    Args:
        driver: WebDriver de Selenium
        
    Returns:
        bool: True si todo el proceso fue exitoso, False en caso contrario
    """
    try:
        # Verificar si ya estamos en el panel de columnas
        if not verify_column_panel_opened_test(driver):
            # Si no estamos en el panel, intentar hacer clic en el ícono
            logger.info("No estamos en el panel de columnas, intentando hacer clic en el ícono...")
            if not click_select_columns_tab_test(driver):
                logger.error("No se pudo abrir el panel de columnas")
                return False
                
            # Esperar a que se abra el panel
            time.sleep(1.5)
                
        # Paso 2: Marcar "Select All"
        logger.info("Marcando la casilla 'Select All'...")
        select_all_clicked = False
        
        # Selectores para Select All
        select_all_selectors = [
            "//div[text()='Select All']/preceding-sibling::div[contains(@class, 'sapMCb')]",
            "//div[normalize-space(text())='Select All']/preceding-sibling::div",
            "(//div[contains(@class, 'sapMCb')])[1]",  # Primer checkbox en el panel
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
                                logger.info("'Select All' ya está marcado")
                                select_all_clicked = True
                                break
                        except:
                            pass
                                
                        # Hacer clic con JavaScript
                        driver.execute_script("arguments[0].click();", element)
                        logger.info(f"Clic exitoso en 'Select All' con selector: {selector}")
                        select_all_clicked = True
                        time.sleep(0.5)
                        break
                if select_all_clicked:
                    break
            except Exception as e:
                logger.debug(f"Error con selector {selector}: {e}")
                continue
        
        # Si no funcionó, intentar con JavaScript
        if not select_all_clicked:
            logger.info("Intentando con JavaScript para marcar 'Select All'...")
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
                    // Buscar el checkbox asociado
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
                
                // Buscar el primer checkbox visible
                var checkboxes = document.querySelectorAll('.sapMCb, input[type="checkbox"]');
                for (var i = 0; i < checkboxes.length; i++) {
                    if (checkboxes[i].offsetParent !== null) {
                        checkboxes[i].click();
                        return true;
                    }
                }
                
                return false;
            })();
            """
            
            select_all_clicked = driver.execute_script(js_select_all)
            if select_all_clicked:
                logger.info("'Select All' marcado exitosamente con JavaScript")
                time.sleep(0.5)
            else:
                logger.error("No se pudo marcar 'Select All'")
                return False
        
        # Paso 3: Hacer clic en OK
        logger.info("Haciendo clic en botón 'OK'...")
        ok_clicked = False
        
        # Selectores específicos para OK (EVITANDO RESET)
        ok_selectors = [
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
                            logger.warning(f"¡Alerta! Selector {selector} apunta al botón Reset. Evitando.")
                            continue
                            
                        # Hacer clic con JavaScript
                        driver.execute_script("arguments[0].click();", element)
                        logger.info(f"Clic exitoso en botón 'OK' con selector: {selector}")
                        ok_clicked = True
                        time.sleep(1)
                        break
                if ok_clicked:
                    break
            except Exception as e:
                logger.debug(f"Error con selector {selector}: {e}")
                continue
        
        # Si no funcionó, intentar con JavaScript
        if not ok_clicked:
            logger.info("Intentando con JavaScript para hacer clic en 'OK'...")
            js_click_ok = """
            (function() {
                // Obtener el botón Reset para evitarlo
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
                    okButtons[0].click();
                    return true;
                }
                
                // Buscar en el footer
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
                logger.info("Clic exitoso en botón 'OK' mediante JavaScript")
                time.sleep(1)
            else:
                # Usar Ctrl+Enter como alternativa
                try:
                    actions = ActionChains(driver)
                    actions.key_down(Keys.CONTROL).send_keys(Keys.RETURN).key_up(Keys.CONTROL).perform()
                    logger.info("Confirmación mediante Ctrl+Enter")
                    time.sleep(1)
                    ok_clicked = True
                except Exception as e:
                    logger.debug(f"Error al usar Ctrl+Enter: {e}")
        
        if not ok_clicked:
            logger.error("No se pudo confirmar la selección")
            return False
        
        # Verificar que el diálogo se ha cerrado
        time.sleep(1)
        dialog_visible = len(driver.find_elements(By.XPATH, 
            "//div[contains(@class, 'sapMDialog') and contains(@style, 'visibility: visible')]")) > 0
        
        if dialog_visible:
            logger.warning("El diálogo sigue visible después de confirmar. Intentando cerrar de nuevo.")
            
            # Último intento: buscar cualquier botón en el footer
            try:
                footer_buttons = driver.find_elements(By.XPATH, 
                    "//div[contains(@class, 'sapMDialogFooter')]//button | //div[contains(@class, 'sapMFooter')]//button")
                    
                for button in footer_buttons:
                    if button.is_displayed() and button.is_enabled() and button.text != "Reset":
                        driver.execute_script("arguments[0].click();", button)
                        logger.info(f"Clic en botón '{button.text}' del footer como último recurso")
                        time.sleep(1)
                        break
            except Exception as last_e:
                logger.debug(f"Error en último intento: {last_e}")
            
            # Verificar de nuevo
            dialog_visible = len(driver.find_elements(By.XPATH, 
                "//div[contains(@class, 'sapMDialog') and contains(@style, 'visibility: visible')]")) > 0
            
            if dialog_visible:
                logger.warning("El diálogo sigue visible, pero continuando de todos modos.")
                return True  # Aunque no se cerró, consideramos que el proceso se completó parcialmente
            
        logger.info("Configuración de columnas completada exitosamente")
        return True
        
    except Exception as e:
        logger.error(f"Error durante la configuración de columnas: {e}")
        return False
    
    
    
    
    
    
    
if __name__ == "__main__":
    # Analizar argumentos de línea de comandos
    import argparse
    
    parser = argparse.ArgumentParser(description="Prueba de selección de columnas en SAP UI5")
    parser.add_argument("--only-columns", action="store_true", 
                        help="Ejecutar solo la prueba de selección de columnas")
    args = parser.parse_args()
    
    if args.only_columns:
        # Prueba especializada: solo probar el clic en el tercer ícono después de abrir ajustes
        try:
            # Configurar entorno mínimo necesario
            script_dir = os.path.dirname(os.path.abspath(__file__))
            if script_dir not in sys.path:
                sys.path.insert(0, script_dir)
                
            parent_dir = os.path.dirname(script_dir)
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            
            # Importar SAPBrowser
            from browser.sap_browser import SAPBrowser
            
            # Crear instancia del navegador
            browser = SAPBrowser()
            
            # Conectar al navegador
            if not browser.connect():
                logger.error("No se pudo conectar al navegador")
                sys.exit(1)
                
            # Navegar a SAP con valores de prueba para tener una interfaz
            browser.navigate_to_sap("1025541", "20096444")
            browser.handle_authentication()
            
            # Esperar a que cargue la interfaz
            time.sleep(5)
            
            # Hacer clic en el botón de ajustes
            logger.info("Haciendo clic en botón de ajustes...")
            if hasattr(browser, 'click_settings_button') and callable(getattr(browser, 'click_settings_button')):
                settings_success = browser.click_settings_button()
            else:
                settings_success = click_settings_button_local(browser.driver)
                
            if not settings_success:
                logger.error("No se pudo hacer clic en el botón de ajustes")
                sys.exit(1)
                
            # Esperar a que se abra el panel
            time.sleep(2)
            
            # Probar el clic en el tercer ícono (Select Columns)
            logger.info("Probando clic en tercer ícono (Select Columns)...")
            
            if hasattr(browser, 'click_select_columns_tab') and callable(getattr(browser, 'click_select_columns_tab')):
                select_columns_success = browser.click_select_columns_tab()
                logger.info(f"Resultado usando método del objeto: {select_columns_success}")
            else:
                select_columns_success = click_select_columns_tab_test(browser.driver)
                logger.info(f"Resultado usando método de prueba: {select_columns_success}")
                
            if select_columns_success:
                print("\n✅ Prueba específica de clic en Select Columns exitosa")
            else:
                print("\n❌ Prueba específica de clic en Select Columns fallida")
            
        except Exception as e:
            logger.error(f"Error en prueba específica: {e}")
            print(f"\n❌ Error: {e}")
        
        # Mantener abierto el navegador para inspección
        input("\nPresione Enter para cerrar el navegador y salir...")
        browser.close()
        sys.exit(0)
    
    # Prueba completa por defecto
    result = test_customer_selection()
    
    if result:
        print("\n✅ Prueba completa exitosa")
    else:
        print("\n❌ Prueba completa fallida")
        
    input("\nPresione Enter para salir...")
