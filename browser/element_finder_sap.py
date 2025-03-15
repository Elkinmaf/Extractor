#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
element_finder_sap.py - Funciones específicas para interfaces SAP UI5/Fiori
---
Este módulo extiende las funcionalidades básicas de element_finder.py con
métodos especializados para trabajar con la interfaz de SAP, incluyendo
componentes específicos como ComboBox, Input, Table, y otros elementos
de SAP UI5.
"""

import time
import logging
from typing import List, Union, Dict, Any, Optional, Tuple
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException
)

# Importar funciones base y configuraciones
from browser.element_finder import (
    find_element, 
    find_elements,
    click_element_safely,
    optimize_browser_performance,
    wait_for_element
)
from config.settings import TIMEOUTS, SELECTORS

# Configurar logger
logger = logging.getLogger(__name__)

def find_sap_input(
    driver: WebDriver, 
    placeholder_or_label: str, 
    timeout: float = TIMEOUTS["element_visibility"]
) -> Optional[WebElement]:
    """
    Encuentra un campo de entrada SAP UI5 por su placeholder o etiqueta
    
    Args:
        driver (WebDriver): WebDriver de Selenium
        placeholder_or_label (str): Texto del placeholder o la etiqueta asociada
        timeout (float): Tiempo de espera en segundos
        
    Returns:
        WebElement or None: El campo de entrada encontrado o None
    """
    # Lista de selectores para encontrar el campo
    selectors = [
        f"//input[contains(@placeholder, '{placeholder_or_label}')]",
        f"//input[contains(@aria-label, '{placeholder_or_label}')]",
        f"//label[contains(text(), '{placeholder_or_label}')]/following::input[1]",
        f"//span[contains(text(), '{placeholder_or_label}')]/following::input[1]",
        f"//div[contains(text(), '{placeholder_or_label}')]/following::input[1]",
        f"//bdi[contains(text(), '{placeholder_or_label}')]/ancestor::div[contains(@class, 'sapMLabel')]/following::input[1]"
    ]
    
    # Intentar con cada selector
    return find_element(driver, selectors, By.XPATH, timeout)

def find_sap_combobox(
    driver: WebDriver, 
    label_text: str, 
    timeout: float = TIMEOUTS["element_visibility"]
) -> Optional[WebElement]:
    """
    Encuentra un control ComboBox de SAP UI5 por su etiqueta
    
    Args:
        driver (WebDriver): WebDriver de Selenium
        label_text (str): Texto de la etiqueta asociada
        timeout (float): Tiempo de espera en segundos
        
    Returns:
        WebElement or None: El ComboBox encontrado o None
    """
    # Lista de selectores para encontrar el ComboBox
    selectors = [
        f"//div[contains(@class, 'sapMComboBox')]/input[contains(@aria-label, '{label_text}')]",
        f"//label[contains(text(), '{label_text}')]/following::div[contains(@class, 'sapMComboBox')][1]/input",
        f"//span[contains(text(), '{label_text}')]/following::div[contains(@class, 'sapMComboBox')][1]/input",
        f"//div[contains(@class, 'sapMComboBoxContainer')]//input[contains(@aria-label, '{label_text}')]"
    ]
    
    # También podemos buscar usando JavaScript UI5
    try:
        js_script = """
        var comboboxes = [];
        if (window.sap && window.sap.ui && window.sap.ui.getCore) {
            comboboxes = sap.ui.getCore().byFieldGroupId().filter(function(c) {
                return (c.getMetadata().getName() === 'sap.m.ComboBox' || 
                       c.getMetadata().getName() === 'sap.m.Select') &&
                       ((c.getPlaceholder && c.getPlaceholder().indexOf(arguments[0]) > -1) ||
                        (c.getAriaLabelledBy && c.getAriaLabelledBy().length > 0));
            });
            
            if (comboboxes.length > 0) {
                return comboboxes[0].getId();
            }
        }
        return null;
        """
        
        combo_id = driver.execute_script(js_script, label_text)
        if combo_id:
            try:
                element = driver.find_element(By.ID, combo_id)
                return element
            except:
                pass
    except Exception as e:
        logger.debug(f"Error en búsqueda de combobox con JavaScript: {e}")
    
    # Intentar con cada selector si la búsqueda con JavaScript falló
    return find_element(driver, selectors, By.XPATH, timeout)

def interact_with_sap_dropdown(
    driver: WebDriver, 
    input_field: WebElement, 
    value: str, 
    select_first_match: bool = True,
    timeout: float = TIMEOUTS["dropdown_delay"]
) -> bool:
    """
    Interactúa con un dropdown de SAP UI5, ingresando valor y seleccionando una opción
    
    Args:
        driver (WebDriver): WebDriver de Selenium
        input_field (WebElement): Campo de entrada del dropdown
        value (str): Valor a ingresar
        select_first_match (bool): Si debe seleccionar automáticamente la primera opción
        timeout (float): Tiempo a esperar para que aparezca el dropdown
        
    Returns:
        bool: True si la interacción fue exitosa, False en caso contrario
    """
    try:
        # Asegurar que el campo está visible y enfocado
        click_element_safely(driver, input_field)
        
        # Limpiar el campo
        input_field.clear()
        
        # En SAP UI5, a veces clear() no funciona bien, intentar múltiples métodos
        driver.execute_script("arguments[0].value = '';", input_field)
        input_field.send_keys(Keys.CONTROL + "a")
        input_field.send_keys(Keys.DELETE)
        time.sleep(0.5)
        
        # Ingresar el valor caracter por caracter (mejor para UI5)
        for char in value:
            input_field.send_keys(char)
            time.sleep(0.1)  # Breve pausa entre caracteres
        
        time.sleep(timeout)  # Esperar a que aparezca el dropdown
        
        # Verificar si aparecieron sugerencias
        dropdown_visible = False
        
        # Métodos para verificar si el dropdown está visible
        dropdown_selectors = [
            "//div[contains(@class, 'sapMPopover') and contains(@style, 'visibility: visible')]",
            "//div[contains(@class, 'sapMSelectList') and not(contains(@style, 'display: none'))]",
            "//ul[contains(@class, 'sapMListItems') and not(contains(@style, 'display: none'))]"
        ]
        
        for selector in dropdown_selectors:
            if is_element_present(driver, selector):
                dropdown_visible = True
                break
        
        if dropdown_visible and select_first_match:
            # Seleccionar el primer elemento con diferentes métodos
            try:
                # Método 1: Usar flecha DOWN y ENTER
                input_field.send_keys(Keys.DOWN)
                time.sleep(0.5)
                input_field.send_keys(Keys.ENTER)
                logger.debug("Seleccionada primera opción con DOWN+ENTER")
                return True
            except Exception as e1:
                logger.debug(f"Error al seleccionar con teclas: {e1}")
                try:
                    # Método 2: Hacer clic en el primer elemento del dropdown
                    item_selectors = [
                        "//div[contains(@class, 'sapMPopover')]//li[1]",
                        "//div[contains(@class, 'sapMSelectList')]//li[1]",
                        "//ul[contains(@class, 'sapMListItems')]//li[1]"
                    ]
                    
                    for selector in item_selectors:
                        items = driver.find_elements(By.XPATH, selector)
                        if items:
                            click_element_safely(driver, items[0])
                            logger.debug("Seleccionada primera opción con clic")
                            return True
                except Exception as e2:
                    logger.debug(f"Error al hacer clic en elemento dropdown: {e2}")
                    
                    # Método 3: JavaScript para seleccionar el primer elemento
                    try:
                        js_script = """
                        var popups = document.querySelectorAll('.sapMPopover, .sapMDialog, .sapMSelectList');
                        for (var i = 0; i < popups.length; i++) {
                            if (popups[i].offsetParent !== null) {  // Verificar si es visible
                                var items = popups[i].querySelectorAll('li, .sapMLIB');
                                if (items.length > 0) {
                                    items[0].click();
                                    return true;
                                }
                            }
                        }
                        return false;
                        """
                        
                        result = driver.execute_script(js_script)
                        if result:
                            logger.debug("Seleccionada primera opción con JavaScript")
                            return True
                    except Exception as e3:
                        logger.debug(f"Error en método JavaScript: {e3}")
        
        # Si no se pudo seleccionar automáticamente o no debíamos hacerlo, presionar ENTER
        input_field.send_keys(Keys.ENTER)
        time.sleep(0.5)
        
        # Verificar resultado
        field_value = input_field.get_attribute("value")
        if field_value and (field_value.strip() == value.strip() or len(field_value.strip()) > 0):
            logger.debug(f"Valor establecido correctamente: {field_value}")
            return True
        else:
            logger.warning(f"Posible error: valor actual '{field_value}' no coincide con el esperado '{value}'")
            return False
            
    except Exception as e:
        logger.error(f"Error en interacción con dropdown: {e}")
        return False

def find_sap_button(
    driver: WebDriver,
    text_or_title: str,
    timeout: float = TIMEOUTS["element_visibility"]
) -> Optional[WebElement]:
    """
    Encuentra un botón de SAP UI5 por su texto o título
    
    Args:
        driver (WebDriver): WebDriver de Selenium
        text_or_title (str): Texto o título del botón
        timeout (float): Tiempo de espera en segundos
        
    Returns:
        WebElement or None: El botón encontrado o None
    """
    selectors = [
        f"//button[contains(text(), '{text_or_title}')]",
        f"//button[@title='{text_or_title}']",
        f"//button[contains(@title, '{text_or_title}')]",
        f"//button[contains(@aria-label, '{text_or_title}')]",
        f"//span[contains(text(), '{text_or_title}')]/ancestor::button",
        f"//bdi[contains(text(), '{text_or_title}')]/ancestor::button"
    ]
    
    # También podemos buscar usando JavaScript UI5
    try:
        js_script = """
        var buttons = [];
        if (window.sap && window.sap.ui && window.sap.ui.getCore) {
            buttons = sap.ui.getCore().byFieldGroupId().filter(function(c) {
                return c.getMetadata().getName() === 'sap.m.Button' &&
                      ((c.getText && c.getText().indexOf(arguments[0]) > -1) ||
                       (c.getTooltip && c.getTooltip().indexOf(arguments[0]) > -1));
            });
            
            if (buttons.length > 0) {
                return buttons[0].getId();
            }
        }
        return null;
        """
        
        button_id = driver.execute_script(js_script, text_or_title)
        if button_id:
            try:
                element = driver.find_element(By.ID, button_id)
                return element
            except:
                pass
    except Exception as e:
        logger.debug(f"Error en búsqueda de botón con JavaScript: {e}")
    
    return find_element(driver, selectors, By.XPATH, timeout)

def find_and_click_sap_tab(
    driver: WebDriver,
    tab_text: str,
    timeout: float = TIMEOUTS["element_visibility"]
) -> bool:
    """
    Encuentra y hace clic en una pestaña de SAP UI5 por su texto
    
    Args:
        driver (WebDriver): WebDriver de Selenium
        tab_text (str): Texto de la pestaña
        timeout (float): Tiempo de espera en segundos
        
    Returns:
        bool: True si la operación fue exitosa, False en caso contrario
    """
    selectors = [
        f"//div[@role='tab' and contains(text(), '{tab_text}')]",
        f"//li[@role='tab']//div[contains(text(), '{tab_text}')]",
        f"//div[contains(@class, 'sapMITBTab')]/descendant::*[contains(text(), '{tab_text}')]",
        f"//div[contains(@class, 'sapMITBText') and contains(text(), '{tab_text}')]/..",
        f"//a[contains(@class, 'sapMITBItem') and contains(., '{tab_text}')]"
    ]
    
    tab_element = find_element(driver, selectors, By.XPATH, timeout)
    
    if tab_element:
        return click_element_safely(driver, tab_element)
    
    # Si no se encontró con los selectores, intentar usar API UI5
    try:
        js_script = """
        var tabFound = false;
        if (window.sap && window.sap.ui && window.sap.ui.getCore) {
            // Buscar todos los controles de tipo IconTabBar o TabContainer
            var tabBars = sap.ui.getCore().byFieldGroupId().filter(function(c) {
                return c.getMetadata().getName() === 'sap.m.IconTabBar' || 
                      c.getMetadata().getName() === 'sap.m.TabContainer';
            });
            
            // Para cada TabBar, buscar la pestaña por texto
            for (var i = 0; i < tabBars.length; i++) {
                var tabs = tabBars[i].getItems ? tabBars[i].getItems() : [];
                for (var j = 0; j < tabs.length; j++) {
                    if (tabs[j].getText && tabs[j].getText().indexOf(arguments[0]) > -1) {
                        // Hacer clic en la pestaña usando la API de UI5
                        tabBars[i].setSelectedItem(tabs[j]);
                        if (tabs[j].firePress) {
                            tabs[j].firePress();
                        }
                        tabFound = true;
                        break;
                    }
                }
                if (tabFound) break;
            }
        }
        return tabFound;
        """
        
        result = driver.execute_script(js_script, tab_text)
        if result:
            logger.info(f"Pestaña '{tab_text}' seleccionada usando API de UI5")
            time.sleep(1)  # Esperar a que se procese el cambio de pestaña
            return True
    except Exception as e:
        logger.debug(f"Error en selección de pestaña con JavaScript: {e}")
    
    logger.warning(f"No se pudo encontrar o hacer clic en la pestaña '{tab_text}'")
    return False

def is_sap_busy_indicator_visible(
    driver: WebDriver,
    timeout: float = 0.5
) -> bool:
    """
    Verifica si el indicador de ocupado de SAP está visible
    
    Args:
        driver (WebDriver): WebDriver de Selenium
        timeout (float): Tiempo de espera máximo en segundos
        
    Returns:
        bool: True si el indicador está visible, False en caso contrario
    """
    selectors = [
        "//div[contains(@class, 'sapUiLocalBusyIndicator')]",
        "//div[contains(@class, 'sapMBusyIndicator')]",
        "//div[contains(@class, 'sapUiBusy')]"
    ]
    
    for selector in selectors:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            for element in elements:
                if element.is_displayed():
                    return True
        except:
            continue
    
    return False

def wait_for_sap_busy_indicator_to_disappear(
    driver: WebDriver,
    timeout: float = TIMEOUTS["page_load"]
) -> bool:
    """
    Espera a que el indicador de ocupado de SAP desaparezca
    
    Args:
        driver (WebDriver): WebDriver de Selenium
        timeout (float): Tiempo máximo de espera en segundos
        
    Returns:
        bool: True si el indicador desapareció, False si se agotó el tiempo
    """
    start_time = time.time()
    poll_interval = 0.2  # Intervalo de verificación en segundos
    
    while time.time() - start_time < timeout:
        if not is_sap_busy_indicator_visible(driver, 0.1):
            # Esperar un poco más para asegurar que la carga está completa
            time.sleep(0.5)
            return True
        
        time.sleep(poll_interval)
    
    logger.warning(f"Timeout esperando a que desaparezca el indicador de ocupado ({timeout}s)")
    return False

def get_sap_message_box_text(driver: WebDriver) -> Optional[str]:
    """
    Obtiene el texto de un cuadro de mensaje SAP si está presente
    
    Args:
        driver (WebDriver): WebDriver de Selenium
        
    Returns:
        str or None: Texto del mensaje o None si no hay mensaje
    """
    selectors = [
        "//div[contains(@class, 'sapMMsgBox')]/div[contains(@class, 'sapMDialogScrollCont')]",
        "//div[contains(@class, 'sapMMessageDialog')]//div[contains(@class, 'sapMDialogScrollCont')]",
        "//span[contains(@class, 'sapMMsgBoxText')]"
    ]
    
    message_element = find_element(driver, selectors, By.XPATH, 0.5, wait_for_visibility=False)
    if message_element:
        return message_element.text.strip()
    
    return None

def dismiss_sap_message_box(driver: WebDriver) -> bool:
    """
    Cierra un cuadro de mensaje SAP si está presente
    
    Args:
        driver (WebDriver): WebDriver de Selenium
        
    Returns:
        bool: True si se cerró el mensaje, False en caso contrario
    """
    try:
        # Buscar botones típicos de los cuadros de mensaje SAP
        button_selectors = [
            "//div[contains(@class, 'sapMMsgBox')]//button[contains(text(), 'OK')]",
            "//div[contains(@class, 'sapMMsgBox')]//button[contains(text(), 'Close')]",
            "//div[contains(@class, 'sapMMsgBox')]//button[contains(text(), 'Cancel')]",
            "//div[contains(@class, 'sapMMessageDialog')]//button[contains(text(), 'OK')]",
            "//div[contains(@class, 'sapMMessageDialog')]//button[contains(text(), 'Close')]",
            "//div[contains(@class, 'sapMDialog')]//button[contains(@class, 'sapMDialogCloseButton')]"
        ]
        
        for selector in button_selectors:
            buttons = driver.find_elements(By.XPATH, selector)
            for button in buttons:
                if button.is_displayed():
                    click_element_safely(driver, button)
                    logger.info("Mensaje SAP cerrado")
                    time.sleep(0.5)  # Breve pausa para que se procese el cierre
                    return True
        
        # Si no encontramos botones específicos, intentar con la tecla Escape
        body = driver.find_element(By.TAG_NAME, "body")
        body.send_keys(Keys.ESCAPE)
        time.sleep(0.5)
        
        # Verificar si el mensaje sigue visible
        if not is_element_present(driver, "//div[contains(@class, 'sapMMsgBox')] | //div[contains(@class, 'sapMMessageDialog')]"):
            logger.info("Mensaje SAP cerrado con tecla Escape")
            return True
            
        return False
    except Exception as e:
        logger.debug(f"Error al cerrar mensaje SAP: {e}")
        return False

def find_sap_table(driver: WebDriver) -> Optional[WebElement]:
    """
    Encuentra una tabla SAP UI5 en la página
    
    Args:
        driver (WebDriver): WebDriver de Selenium
        
    Returns:
        WebElement or None: Elemento de la tabla o None si no se encuentra
    """
    table_selectors = [
        "//table[contains(@class, 'sapMListTbl')]",
        "//div[contains(@class, 'sapMList')]",
        "//div[contains(@class, 'sapUiTable')]"
    ]
    
    return find_element(driver, table_selectors, By.XPATH, timeout=5)

def get_sap_table_data(
    driver: WebDriver, 
    max_rows: int = 1000,
    include_headers: bool = True
) -> Tuple[List[str], List[List[str]]]:
    """
    Extrae datos completos de una tabla SAP UI5
    
    Args:
        driver (WebDriver): WebDriver de Selenium
        max_rows (int): Número máximo de filas a extraer
        include_headers (bool): Si se deben incluir los encabezados
        
    Returns:
        tuple: (headers, rows) donde headers es una lista de strings y rows es una lista de listas
    """
    # Detectar encabezados
    headers = []
    if include_headers:
        header_map = detect_table_headers(driver)
        if header_map:
            # Ordenar los encabezados por su índice
            sorted_headers = sorted(header_map.items(), key=lambda x: x[1])
            headers = [header for header, _ in sorted_headers]
        
        if not headers:
            # Intento alternativo de obtener encabezados
            header_selectors = [
                "//table[contains(@class, 'sapMListTbl')]//th",
                "//div[contains(@class, 'sapMListTblHeaderCell')]",
                "//div[@role='columnheader']"
            ]
            
            for selector in header_selectors:
                header_elements = driver.find_elements(By.XPATH, selector)
                if header_elements:
                    headers = [h.text.strip() for h in header_elements if h.text.strip()]
                    break
    
    # Obtener filas
    rows = []
    table_rows = find_table_rows(driver, highlight=False)
    
    # Limitar el número de filas a procesar
    table_rows = table_rows[:max_rows] if len(table_rows) > max_rows else table_rows
    
    for row in table_rows:
        try:
            cells = get_row_cells(row)
            if cells:
                row_data = [cell.text.strip() for cell in cells]
                if any(row_data):  # Asegurar que al menos un valor no esté vacío
                    rows.append(row_data)
        except StaleElementReferenceException:
            # La fila puede haberse vuelto obsoleta, continuar con la siguiente
            continue
        except Exception as e:
            logger.debug(f"Error extrayendo datos de fila: {e}")
            continue
    
    return headers, rows

def extract_sap_form_data(driver: WebDriver) -> Dict[str, str]:
    """
    Extrae los datos de un formulario SAP UI5
    
    Args:
        driver (WebDriver): WebDriver de Selenium
        
    Returns:
        dict: Datos del formulario con etiquetas como claves y valores como valores
    """
    result = {}
    
    try:
        # Buscar los pares etiqueta-valor del formulario
        label_selectors = [
            "//label[contains(@class, 'sapMLabel')]",
            "//div[contains(@class, 'sapMText') and ./following-sibling::div]"
        ]
        
        for selector in label_selectors:
            labels = driver.find_elements(By.XPATH, selector)
            for label in labels:
                try:
                    label_text = label.text.strip()
                    if not label_text or ":" not in label_text:
                        continue
                    
                    # Eliminar el colon del final si existe
                    label_key = label_text.rstrip(":")
                    
                    # Buscar el valor asociado a esta etiqueta
                    value_element = None
                    
                    # Intentar diferentes métodos para encontrar el valor
                    try:
                        # Método 1: Buscar elementos cercanos que puedan contener el valor
                        value_element = label.find_element(By.XPATH, 
                            "./following-sibling::div[1] | ./following-sibling::input[1] | ./following-sibling::textarea[1]")
                    except:
                        try:
                            # Método 2: Buscar por 'for' de la etiqueta
                            element_id = label.get_attribute("for")
                            if element_id:
                                value_element = driver.find_element(By.ID, element_id)
                        except:
                            pass
                    
                    # Si encontramos un elemento de valor, obtener su texto o valor
                    if value_element:
                        value = value_element.text.strip()
                        if not value:  # Si el texto está vacío, puede ser un campo de entrada
                            value = value_element.get_attribute("value") or ""
                        
                        result[label_key] = value
                except Exception as e:
                    logger.debug(f"Error procesando etiqueta {label_text if 'label_text' in locals() else 'desconocida'}: {e}")
        
        # Buscar también por pares Input-Label usando UI5
        try:
            js_script = """
            var result = {};
            if (window.sap && window.sap.ui && window.sap.ui.getCore) {
                var inputs = sap.ui.getCore().byFieldGroupId().filter(function(c) {
                    return (c.getMetadata().getName() === 'sap.m.Input' || 
                           c.getMetadata().getName() === 'sap.m.TextArea' ||
                           c.getMetadata().getName() === 'sap.m.ComboBox') &&
                           c.getLabels && c.getLabels().length > 0;
                });
                
                inputs.forEach(function(input) {
                    try {
                        var label = input.getLabels()[0];
                        if (label && label.getText) {
                            var labelText = label.getText().replace(/:$/, '');
                            var value = input.getValue ? input.getValue() : '';
                            if (labelText && value) {
                                result[labelText] = value;
                            }
                        }
                    } catch(e) {}
                });
            }
            return result;
            """
            
            js_result = driver.execute_script(js_script)
            if js_result and isinstance(js_result, dict):
                # Combinar con los resultados existentes
                result.update(js_result)
        except Exception as e:
            logger.debug(f"Error en extracción de formulario con JavaScript: {e}")
    
    except Exception as e:
        logger.error(f"Error en extracción de datos de formulario: {e}")
    
    return result

def check_sap_ui5_loaded(driver: WebDriver, timeout: float = 10) -> bool:
    """
    Verifica si la biblioteca SAP UI5 ha cargado completamente
    
    Args:
        driver (WebDriver): WebDriver de Selenium
        timeout (float): Tiempo máximo de espera en segundos
        
    Returns:
        bool: True si UI5 ha cargado, False en caso contrario
    """
    try:
        # Script para verificar si UI5 está disponible y completamente cargado
        js_script = """
        return (
            window.sap !== undefined && 
            window.sap.ui !== undefined && 
            window.sap.ui.getCore !== undefined &&
            window.sap.ui.getCore().isReady === true
        );
        """
        
        # Esperar hasta que UI5 esté listo
        start_time = time.time()
        while time.time() - start_time < timeout:
            result = driver.execute_script(js_script)
            if result:
                logger.info("SAP UI5 cargado completamente")
                return True
            time.sleep(0.5)
        
        logger.warning(f"Timeout esperando a que cargue SAP UI5 ({timeout}s)")
        return False
    except Exception as e:
        logger.error(f"Error al verificar carga de SAP UI5: {e}")
        return False

def wait_for_sap_navigation_complete(driver: WebDriver, timeout: float = TIMEOUTS["page_load"]) -> bool:
    """
    Espera a que se complete la navegación en una aplicación SAP
    
    Args:
        driver (WebDriver): WebDriver de Selenium
        timeout (float): Tiempo máximo de espera en segundos
        
    Returns:
        bool: True si la navegación se completó, False en caso contrario
    """
    try:
        # Paso 1: Esperar a que se complete el estado de readyState
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        # Paso 2: Esperar a que desaparezca cualquier indicador de ocupado
        busy_start = time.time()
        while time.time() - busy_start < timeout:
            if not is_sap_busy_indicator_visible(driver):
                # No hay indicador de ocupado visible
                break
            time.sleep(0.5)
        
        # Paso 3: Esperar a que UI5 complete su inicialización
        check_sap_ui5_loaded(driver, min(5, timeout / 2))  # Usar un timeout menor para esta verificación
        
        # Paso 4: Esperar un momento para que se completen posibles operaciones AJAX
        time.sleep(1)
        
        logger.info("Navegación SAP completada")
        return True
    except TimeoutException:
        logger.warning(f"Timeout esperando a que se complete la navegación SAP ({timeout}s)")
        return False
    except Exception as e:
        logger.error(f"Error al esperar navegación SAP: {e}")
        return False

# Funciones específicas para la extracción de issues en SAP

def extract_issue_cell_value(cell: WebElement, data_type: str = "text") -> str:
    """
    Extrae el valor de una celda de issue con manejo especial para diferentes tipos de datos
    
    Args:
        cell (WebElement): Celda a procesar
        data_type (str): Tipo de dato a extraer ("text", "status", "priority", "date")
        
    Returns:
        str: Valor extraído de la celda
    """
    try:
        if data_type == "status":
            # Para estados, buscar el texto del estado y cualquier información de color/clase
            status_text = cell.text.strip()
            status_class = cell.get_attribute("class") or ""
            
            # Intentar determinar estado por clase CSS
            status_mapping = {
                "success": "DONE",
                "warning": "IN PROGRESS",
                "error": "OPEN",
                "information": "READY"
            }
            
            for css_class, mapped_status in status_mapping.items():
                if css_class in status_class.lower():
                    # Si el texto no contiene el estado mapeado, combinar ambos
                    if mapped_status not in status_text.upper():
                        if status_text:
                            return f"{mapped_status} - {status_text}"
                        else:
                            return mapped_status
            
            return status_text
            
        elif data_type == "priority":
            # Para prioridad, buscar el texto y cualquier indicador visual
            priority_text = cell.text.strip()
            priority_class = cell.get_attribute("class") or ""
            
            # Verificar elementos de indicador visual de prioridad
            icon_elements = cell.find_elements(By.XPATH, ".//span[contains(@class, 'sapUiIcon')] | .//span[contains(@class, 'sapMGaugeSegment')]")
            
            if icon_elements:
                # Determinar prioridad por color/clase del icono
                for icon in icon_elements:
                    icon_class = icon.get_attribute("class") or ""
                    if "negative" in icon_class or "red" in icon_class:
                        return "Very High" if not priority_text else priority_text
                    elif "critical" in icon_class or "yellow" in icon_class or "orange" in icon_class:
                        return "High" if not priority_text else priority_text
                    elif "neutral" in icon_class or "blue" in icon_class:
                        return "Medium" if not priority_text else priority_text
                    elif "positive" in icon_class or "green" in icon_class:
                        return "Low" if not priority_text else priority_text
            
            return priority_text
            
        elif data_type == "date":
            # Para fechas, asegurar formato consistente
            date_text = cell.text.strip()
            
            # Si no hay texto de fecha, buscar atributos alternativos
            if not date_text:
                # Intentar extraer fecha de atributos como title, aria-label, o value
                date_text = cell.get_attribute("title") or cell.get_attribute("aria-label") or cell.get_attribute("value") or ""
            
            return date_text
            
        else:
            # Para texto general, extraer el contenido de texto
            text = cell.text.strip()
            
            # Si no hay texto visible, intentar obtener de otros atributos
            if not text:
                text = cell.get_attribute("title") or cell.get_attribute("value") or ""
                
            return text
    except Exception as e:
        logger.debug(f"Error al extraer valor de celda ({data_type}): {e}")
        return ""