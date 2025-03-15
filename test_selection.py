#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de prueba para verificar la funcionalidad de selección de cliente en SAP
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
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def test_customer_selection():
    """
    Prueba específica para la funcionalidad de selección de cliente
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
            
        # Prueba específica de selección de cliente
        logger.info(f"Probando selección de cliente para ERP: {erp_number}")
        
        # Verificar si ya están los valores
        if browser.verify_fields_have_expected_values(erp_number, project_id):
            logger.info("Los campos ya tienen los valores esperados")
            return True
            
        # Probar selección de cliente con el método mejorado
        selection_result = browser.select_customer_ui5_direct(erp_number)
        
        if selection_result:
            logger.info("✅ Selección de cliente exitosa con UI5 directo")
            
            # Verificación adicional para debug
            verification_result = browser._enhanced_client_verification(erp_number)
            if verification_result:
                logger.info("✅ Verificación de selección de cliente exitosa")
            else:
                logger.warning("⚠️ Verificación adicional falló aunque la selección reportó éxito")
                
            # Continuar con la selección de proyecto solo si es necesario
            if project_id and browser._verify_project_selection_strict(project_id):
                logger.info("El proyecto ya está seleccionado")
            elif project_id:
                if browser.select_project_ui5_direct(project_id):
                    logger.info("✅ Selección de proyecto exitosa")
                    
                    # Hacer clic en botón de búsqueda
                    if browser.click_search_button():
                        logger.info("✅ Clic en botón de búsqueda exitoso")
            
            return True  # El test es exitoso si la selección de cliente fue exitosa
        else:
            logger.error("❌ Todas las estrategias de selección de cliente fallaron")
            return False
        
    except Exception as e:
        logger.error(f"Error en prueba: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    
    
    
    
            
if __name__ == "__main__":
    result = test_customer_selection()
    if result:
        print("\n✅ Prueba completada con éxito")
    else:
        print("\n❌ Prueba falló")
    
    input("\nPresione Enter para salir...")
