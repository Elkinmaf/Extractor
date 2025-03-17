#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
column_selection_manager.py - Gestión de la selección de columnas en la interfaz SAP

Este módulo proporciona funciones específicas para interactuar con el diálogo
de selección de columnas en la interfaz SAP UI5/Fiori, permitiendo seleccionar
todas las columnas disponibles para una extracción completa de datos.
"""

import time
import logging
from typing import Optional, List, Dict, Union, Tuple
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException
)
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# Configurar logger
logger = logging.getLogger(__name__)

class ColumnSelectionManager:
    """
    Clase para gestionar la selección de columnas en la interfaz SAP
    """
    
    def __init__(self, driver: WebDriver):
        """
        Inicializa el gestor de selección de columnas
        
        Args:
            driver (WebDriver): Instancia activa del WebDriver
        """
        self.driver = driver
        self.settings_panel_opened = False
        self.column_tab_selected = False
    
    def select_all_columns(self) -> bool:
        """
        Realiza el proceso completo de selección de columnas:
        1. Abre el panel de ajustes (si es necesario)
        2. Hace clic en el tab "Select Columns"
        3. Marca la opción "Select All"
        4. Confirma los cambios con OK
        
        Returns:
            bool: True si el proceso fue exitoso, False en caso contrario
        """
        try:
            logger.info("Iniciando proceso de selección de todas las columnas...")
            
            # 1. Asegurar que el panel de ajustes esté abierto
            # (asumimos que ya está abierto por el flujo previo)
            if not self._verify_settings_panel_opened():
                logger.warning("Panel de ajustes no detectado, no se puede continuar")
                return False
                
            # 2. Hacer clic en la pestaña "Select Columns" (tercer ícono)
            if not self._click_select_columns_tab():
                logger.error("No se pudo hacer clic en la pestaña 'Select Columns'")
                return False
                
            # 3. Marcar la opción "Select All"
            if not self._click_select_all_checkbox():
                logger.error("No se pudo marcar la opción 'Select All'")
                return False
                
            # 4. Confirmar con OK
            if not self._confirm_selection():
                logger.error("No se pudo confirmar la selección con OK")
                return False
                
            logger.info("Proceso de selección de columnas completado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error durante el proceso de selección de columnas: {e}")
            return False
    
    def _verify_settings_panel_opened(self) -> bool:
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
                    logger.info("Panel de ajustes detectado correctamente")
                    self.settings_panel_opened = True
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
                logger.info("Panel de ajustes detectado mediante JavaScript")
                self.settings_panel_opened = True
                return True
            
            logger.warning("No se detectó panel de ajustes abierto")
            return False
            
        except Exception as e:
            logger.error(f"Error al verificar panel de ajustes: {e}")
            return False
    
    def _click_select_columns_tab(self) -> bool:
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
                            self.column_tab_selected = True
                            return True
                        except Exception as js_e:
                            logger.debug(f"Error en clic JavaScript: {js_e}")
                            try:
                                # Intentar clic normal
                                element.click()
                                logger.info("Clic en pestaña 'Select Columns' realizado con método normal")
                                time.sleep(1)
                                self.column_tab_selected = True
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
                self.column_tab_selected = True
                return True
                
            logger.warning("No se pudo hacer clic en la pestaña 'Select Columns'")
            return False
            
        except Exception as e:
            logger.error(f"Error al hacer clic en pestaña 'Select Columns': {e}")
            return False
    
    def _click_select_all_checkbox(self) -> bool:
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
    
    def _confirm_selection(self) -> bool:
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


# Función independiente para uso directo en el flujo de extracción
def configurar_columnas_visibles(driver: WebDriver) -> bool:
    """
    Configura las columnas visibles seleccionando todas las disponibles.
    Esta función está diseñada para ser llamada después de que el panel
    de ajustes ha sido abierto.
    
    Args:
        driver (WebDriver): WebDriver de Selenium con la sesión activa
        
    Returns:
        bool: True si la configuración fue exitosa, False en caso contrario
    """
    try:
        logger.info("Iniciando configuración de columnas visibles...")
        
        # Crear instancia del gestor
        column_manager = ColumnSelectionManager(driver)
        
        # Ejecutar el proceso de selección
        return column_manager.select_all_columns()
        
    except Exception as e:
        logger.error(f"Error al configurar columnas visibles: {e}")
        return False
