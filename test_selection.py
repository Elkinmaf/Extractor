#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de prueba para verificar la navegación por teclado en el panel de columnas de SAP.
Ejecuta la secuencia exacta de pulsaciones de teclas para seleccionar todas las columnas.
"""

import os
import sys
import time
import logging
from datetime import datetime
from selenium.webdriver.common.by import By

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def test_keyboard_navigation():
    """
    Prueba la funcionalidad de navegación por teclado para seleccionar columnas
    """
    try:
        # Asegurar paths de importación correctos
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
            
        parent_dir = os.path.dirname(script_dir)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
            
        # Crear directorio para logs y capturas
        logs_dir = os.path.join(script_dir, "logs")
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
            
        # Importar SAPBrowser
        from browser.sap_browser import SAPBrowser
        
        # 1. Iniciar el navegador
        logger.info("=== Iniciando prueba de navegación por teclado para selección de columnas ===")
        browser = SAPBrowser()
        
        if not browser.connect():
            logger.error("❌ No se pudo conectar al navegador")
            return False
            
        logger.info("✅ Navegador conectado correctamente")
        
        # 2. Navegar a SAP
        erp_number = "1025541"  # Valores de prueba
        project_id = "20096444"  # Valores de prueba
        
        logger.info(f"Navegando a SAP con ERP={erp_number}, Proyecto={project_id}")
        browser.navigate_to_sap(erp_number, project_id)
        
        # Manejar autenticación si es necesario
        logger.info("Verificando si se requiere autenticación...")
        browser.handle_authentication()
        
        # Esperar a que cargue la interfaz
        logger.info("Esperando a que cargue la interfaz...")
        time.sleep(5)
        
        # Tomar captura para verificar estado inicial
        browser.driver.save_screenshot(os.path.join(logs_dir, "01_initial_state.png"))
        
        # 3. Navegar por la interfaz para llegar a la vista de issues
        logger.info("Seleccionando cliente y proyecto...")
        browser.select_customer_automatically(erp_number)
        time.sleep(2)
        browser.select_project_automatically(project_id)
        time.sleep(2)
        
        # Hacer clic en el botón de búsqueda
        logger.info("Haciendo clic en botón de búsqueda...")
        browser.click_search_button()
        time.sleep(3)
        
        
        # Tomar captura antes de hacer clic en ajustes
        browser.driver.save_screenshot(os.path.join(logs_dir, "02_before_settings.png"))
        
        # 4. PASO PRINCIPAL: Hacer clic en el botón de ajustes
        logger.info("PASO 1: Haciendo clic en el botón de ajustes...")
        
        if not browser.click_settings_button():
            logger.error("❌ Error al hacer clic en el botón de ajustes")
            browser.driver.save_screenshot(os.path.join(logs_dir, "error_settings_button.png"))
            return False
            
        logger.info("✅ Botón de ajustes cliqueado exitosamente")
        
        # Esperar a que se abra el panel
        time.sleep(2)
        browser.driver.save_screenshot(os.path.join(logs_dir, "03_settings_panel_opened.png"))
        
        # 5. PASO PRINCIPAL: Usar navegación por teclado para seleccionar columnas
        logger.info("PASO 2: Ejecutando select_all_visible_columns con navegación por teclado (7 tabs, 2 flechas, Enter)...")
        
        # Verificar que el método existe
        if not hasattr(browser, 'select_all_visible_columns'):
            logger.error("❌ El método select_all_visible_columns no está implementado en SAPBrowser")
            return False
            
        # Ejecutar el método principal
        result = browser.select_all_visible_columns()
        
        # Tomar captura del resultado
        browser.driver.save_screenshot(os.path.join(logs_dir, "04_after_column_selection.png"))
        
        if result:
            logger.info("✅ Selección de columnas completada exitosamente")
        else:
            logger.error("❌ La selección de columnas falló")
            return False
        
        # 6. Probar cada etapa por separado (solo para fines de depuración)
        logger.info("PASO BONUS: Probando cada etapa individualmente para depuración...")
        
        # Hacer clic nuevamente en ajustes
        if browser.click_settings_button():
            logger.info("Botón de ajustes cliqueado nuevamente para pruebas individuales")
            time.sleep(2)
            
            # Test 1: Select Columns (7 tabs, 2 flechas, Enter)
            logger.info("Test 1: Navegación a pestaña 'Select Columns' (7 tabs, 2 flechas, Enter)...")
            browser.driver.save_screenshot(os.path.join(logs_dir, "05_before_columns_navigation.png"))
            
            if hasattr(browser, 'navigate_to_select_columns_with_keyboard'):
                if browser.navigate_to_select_columns_with_keyboard():
                    logger.info("✅ Navegación a pestaña 'Select Columns' exitosa")
                    browser.driver.save_screenshot(os.path.join(logs_dir, "06_after_columns_navigation.png"))
                    
                    # Test 2: Select All (3 tabs, Enter)
                    logger.info("Test 2: Selección de 'Select All' (3 tabs, Enter)...")
                    
                    if hasattr(browser, '_click_select_all_checkbox_with_keyboard'):
                        if browser._click_select_all_checkbox_with_keyboard():
                            logger.info("✅ Selección de 'Select All' exitosa")
                            browser.driver.save_screenshot(os.path.join(logs_dir, "07_after_select_all.png"))
                            
                            # Test 3: Confirmar con OK (2 tabs, Enter)
                            logger.info("Test 3: Confirmación con OK (2 tabs, Enter)...")
                            
                            if hasattr(browser, '_confirm_selection_with_keyboard'):
                                if browser._confirm_selection_with_keyboard():
                                    logger.info("✅ Confirmación exitosa")
                                    browser.driver.save_screenshot(os.path.join(logs_dir, "08_after_confirm.png"))
                                else:
                                    logger.warning("⚠️ Confirmación falló")
                                    browser.driver.save_screenshot(os.path.join(logs_dir, "error_confirm.png"))
                            else:
                                logger.warning("⚠️ Método _confirm_selection_with_keyboard no implementado")
                        else:
                            logger.warning("⚠️ Selección de 'Select All' falló")
                            browser.driver.save_screenshot(os.path.join(logs_dir, "error_select_all.png"))
                    else:
                        logger.warning("⚠️ Método _click_select_all_checkbox_with_keyboard no implementado")
                else:
                    logger.warning("⚠️ Navegación a pestaña de columnas falló")
                    browser.driver.save_screenshot(os.path.join(logs_dir, "error_columns_navigation.png"))
            else:
                logger.warning("⚠️ Método navigate_to_select_columns_with_keyboard no implementado")

        # Prueba completada con éxito
        logger.info("=== Prueba completada con éxito ===")
        logger.info(f"Capturas de pantalla guardadas en: {logs_dir}")
        return True
        
    except Exception as e:
        logger.error(f"Error durante la prueba: {e}")
        if 'browser' in locals() and browser.driver:
            browser.driver.save_screenshot(os.path.join(logs_dir, "critical_error.png"))
        return False
    finally:
        # Esperar confirmación para continuar (si se desea inspeccionar)
        input("\nPresione Enter para cerrar navegador y finalizar prueba...")
        
        # Cerrar navegador si está abierto
        if 'browser' in locals() and hasattr(browser, 'driver') and browser.driver:
            browser.driver.quit()

if __name__ == "__main__":
    success = test_keyboard_navigation()
    
    if success:
        print("\n✅ PRUEBA EXITOSA: La navegación por teclado funciona correctamente")
        sys.exit(0)
    else:
        print("\n❌ PRUEBA FALLIDA: La navegación por teclado no funciona correctamente")
        sys.exit(1)