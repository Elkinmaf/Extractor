#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de prueba mejorado para verificar la funcionalidad de selección de cliente en SAP
con espera adecuada de carga de interfaz y manejo de errores mejorado.
"""

import os
import sys
import time
import logging
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def test_customer_selection():
    """
    Prueba específica para la funcionalidad de selección de cliente
    con manejo mejorado de la espera de carga de la interfaz
    """
    # Importar desde el contexto del proyecto
    try:
        # Asegurar que estamos en el directorio correcto para importaciones
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Añadir el directorio actual al path para permitir importaciones
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
        
        # Ahora importamos los módulos necesarios
        from browser.sap_browser import SAPBrowser
        
        logger.info("=== Iniciando prueba de selección de cliente ===")
        
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
        
        # *** MEJORA 1: Esperar a que la interfaz esté completamente cargada ***
        logger.info("Esperando a que la interfaz de SAP esté completamente cargada...")
        if not wait_for_sap_interface_ready(browser.driver):
            logger.warning("No se pudo confirmar que la interfaz esté completamente cargada, pero continuando...")
        
        # *** MEJORA 2: Verificar el estado actual antes de intentar seleccionar ***
        logger.info("Verificando si ya están seleccionados los valores esperados...")
        if browser.verify_fields_have_expected_values(erp_number, project_id):
            logger.info("Los campos ya tienen los valores esperados, no es necesario seleccionar")
            # Continuar con la prueba de proyecto solo para verificar
            wait_and_test_project_selection(browser, project_id)
            return True
        
        # Prueba específica de selección de cliente con espera adicional
        logger.info(f"Probando selección de cliente para ERP: {erp_number}")
        
        # *** MEJORA 3: Ejecutar selección de cliente con reintentos ***
        client_selected = select_client_with_retries(browser, erp_number)
        
        if client_selected:
            logger.info(f"✅ Cliente {erp_number} seleccionado exitosamente")
            
            # Continuar con la selección de proyecto
            wait_and_test_project_selection(browser, project_id)
            return True
        else:
            logger.error(f"❌ Todas las estrategias de selección de cliente fallaron")
            return False
        
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
        try:
            if browser.select_customer_ui5_direct(erp_number):
                logger.info(f"Cliente {erp_number} seleccionado con método UI5 directo en intento {attempt+1}")
                return True
        except Exception as e:
            logger.warning(f"Error en método UI5 directo: {e}")
        
        # Estrategia 2: Método automatizado general
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
                    if browser._verify_client_selection_strict(erp_number):
                        logger.info(f"Cliente {erp_number} seleccionado con JavaScript agresivo")
                        return True
            except Exception as e:
                logger.warning(f"Error en método JavaScript agresivo: {e}")
    
    # Si llegamos aquí, todos los intentos fallaron
    return False


def wait_and_test_project_selection(browser, project_id):
    """
    Espera a que se pueda seleccionar el proyecto y prueba la selección
    
    Args:
        browser: Instancia de SAPBrowser
        project_id: ID del proyecto
        
    Returns:
        bool: True si la selección fue exitosa, False en caso contrario
    """
    try:
        # Esperar a que el campo de proyecto esté disponible
        logger.info("Esperando a que el campo de proyecto esté disponible...")
        
        # Criterios para detectar que el proyecto está listo para ser seleccionado
        project_ready = False
        attempts = 0
        max_attempts = 5
        
        while not project_ready and attempts < max_attempts:
            attempts += 1
            
            # Verificar si ya está seleccionado
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
                logger.info(f"Esperando campo de proyecto... intento {attempts}/{max_attempts}")
                time.sleep(3)
        
        if not project_ready:
            logger.warning("No se pudo detectar campo de proyecto después de múltiples intentos")
            return False
            
        # Intentar seleccionar el proyecto
        logger.info(f"Probando selección de proyecto {project_id}...")
        if browser.select_project_ui5_direct(project_id):
            logger.info(f"✅ Proyecto {project_id} seleccionado exitosamente")
            
            # Verificar búsqueda final
            if browser.click_search_button():
                logger.info("Búsqueda iniciada correctamente")
                return True
        else:
            logger.warning(f"No se pudo seleccionar proyecto {project_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error en prueba de selección de proyecto: {e}")
        return False


if __name__ == "__main__":
    result = test_customer_selection()
    if result:
        print("\n✅ Prueba completada con éxito")
    else:
        print("\n❌ Prueba falló")
    
    input("\nPresione Enter para salir...")
