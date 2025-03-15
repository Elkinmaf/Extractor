#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
element_finder.py - Utilidades para encontrar elementos web en SAP UI5/Fiori
---
Este módulo proporciona funciones especializadas para localizar elementos
en la interfaz SAP que pueden ser difíciles de encontrar con los
métodos estándar de Selenium, incluyendo estrategias para tablas,
controles de paginación y elementos dinámicos.
"""

import time
import logging
from typing import List, Union, Any, Optional, Dict, Callable
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

# Importar configuraciones
from config.settings import TIMEOUTS, SELECTORS

# Configurar logger
logger = logging.getLogger(__name__)

def find_element(
    driver: WebDriver, 
    selectors: Union[str, List[str]], 
    by: By = By.XPATH,
    timeout: float = TIMEOUTS["element_visibility"],
    parent: WebElement = None,
    wait_for_visibility: bool = True,
    multiple_attempts: bool = True
) -> Optional[WebElement]:
    """
    Encuentra un elemento web de manera robusta con múltiples selectores y reintentos
    
    Args:
        driver (WebDriver): Instancia del controlador de Selenium
        selectors (str|List[str]): Un selector o lista de selectores para buscar el elemento
        by (By, optional): Método de localización (XPATH, CSS_SELECTOR, etc.). Por defecto XPATH.
        timeout (float, optional): Tiempo máximo de espera en segundos.
        parent (WebElement, optional): Elemento padre para buscar dentro de él. Por defecto None (buscar en todo el DOM).
        wait_for_visibility (bool, optional): Si se debe esperar a que el elemento sea visible. Por defecto True.
        multiple_attempts (bool, optional): Si se deben realizar múltiples intentos. Por defecto True.
        
    Returns:
        WebElement or None: El elemento encontrado, o None si no se encontró
    """
    # Convertir un solo selector a lista
    if isinstance(selectors, str):
        selectors = [selectors]
    
    # Definir el contexto de búsqueda (driver o elemento padre)
    context = parent if parent else driver
    
    # Intentar cada selector
    for selector in selectors:
        try:
            if wait_for_visibility:
                # Esperar a que el elemento sea visible
                wait = WebDriverWait(driver, timeout)
                element = wait.until(
                    EC.visibility_of_element_located((by, selector))
                )
                return element
            else:
                # Buscar sin esperar visibilidad
                element = context.find_element(by, selector)
                return element
        except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
            logger.debug(f"No se encontró elemento con selector {selector}: {e}")
            continue
    
    # Si llegamos aquí, ningún selector funcionó
    # Intentar un enfoque más agresivo con JavaScript si está habilitado
    if multiple_attempts and by == By.XPATH:
        for selector in selectors:
            try:
                logger.debug(f"Intentando encontrar elemento con JavaScript: {selector}")
                element = driver.execute_script(
                    f"""
                    var element = document.evaluate(
                        "{selector}",
                        document,
                        null,
                        XPathResult.FIRST_ORDERED_NODE_TYPE,
                        null
                    ).singleNodeValue;
                    return element;
                    """
                )
                if element:
                    return element
            except Exception as e:
                logger.debug(f"Error al buscar con JavaScript: {e}")
                continue
    
    logger.warning(f"No se pudo encontrar ningún elemento con los selectores proporcionados")
    return None

def find_elements(
    driver: WebDriver, 
    selectors: Union[str, List[str]], 
    by: By = By.XPATH,
    timeout: float = TIMEOUTS["element_visibility"],
    parent: WebElement = None,
    filter_visibility: bool = False
) -> List[WebElement]:
    """
    Encuentra múltiples elementos web con varios selectores
    
    Args:
        driver (WebDriver): Instancia del controlador de Selenium
        selectors (str|List[str]): Un selector o lista de selectores para buscar elementos
        by (By, optional): Método de localización (XPATH, CSS_SELECTOR, etc.). Por defecto XPATH.
        timeout (float, optional): Tiempo máximo de espera en segundos.
        parent (WebElement, optional): Elemento padre para buscar dentro de él. Por defecto None.
        filter_visibility (bool, optional): Filtrar solo elementos visibles. Por defecto False.
        
    Returns:
        List[WebElement]: Lista de elementos encontrados (puede estar vacía)
    """
    # Convertir un solo selector a lista
    if isinstance(selectors, str):
        selectors = [selectors]
    
    # Definir el contexto de búsqueda (driver o elemento padre)
    context = parent if parent else driver
    
    all_elements = []
    
    # Intentar cada selector
    for selector in selectors:
        try:
            if timeout > 0:
                # Esperar a que al menos un elemento esté presente
                wait = WebDriverWait(driver, timeout)
                wait.until(
                    EC.presence_of_element_located((by, selector))
                )
            
            # Obtener todos los elementos con ese selector
            elements = context.find_elements(by, selector)
            
            # Filtrar por visibilidad si es necesario
            if filter_visibility:
                elements = [e for e in elements if e.is_displayed()]
                
            all_elements.extend(elements)
            
            # Si encontramos elementos, no necesitamos seguir con más selectores
            if elements:
                logger.debug(f"Encontrados {len(elements)} elementos con selector {selector}")
                break
                
        except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
            logger.debug(f"No se encontraron elementos con selector {selector}: {e}")
            continue
    
    logger.debug(f"Total de elementos encontrados: {len(all_elements)}")
    return all_elements

def find_table_rows(driver: WebDriver, highlight: bool = False) -> List[WebElement]:
    """
    Encuentra todas las filas de una tabla SAP UI5 utilizando múltiples estrategias.
    
    Args:
        driver (WebDriver): WebDriver de Selenium
        highlight (bool): Si es True, resalta la primera fila encontrada
        
    Returns:
        list: Lista de elementos WebElement que representan filas de la tabla
    """
    all_rows = []
    
    # Usar los selectores predefinidos desde settings
    selectors = SELECTORS.get("table_rows", [
        # Selectores de SAP estándar
        "//table[contains(@class, 'sapMListTbl')]/tbody/tr[not(contains(@class, 'sapMListTblHeader'))]",
        "//div[contains(@class, 'sapMList')]//li[contains(@class, 'sapMLIB')]",
        "//table[contains(@class, 'sapMList')]/tbody/tr",
        "//div[@role='row'][not(contains(@class, 'sapMListHeaderSubTitleItems')) and not(contains(@class, 'sapMListTblHeader'))]",
        "//div[contains(@class, 'sapMListItems')]/div[contains(@class, 'sapMListItem')]",
        "//div[contains(@class, 'sapMListItems')]//div[contains(@class, 'sapMObjectIdentifier')]/..",
        "//div[contains(@class, 'sapMListItem')]",
        
        # Selectores de Fiori
        "//div[contains(@class, 'sapMList')]//li[@tabindex]",
        "//div[contains(@class, 'sapUiTable')]//tr[contains(@class, 'sapUiTableRow')]",
        "//div[contains(@class, 'sapUiTableRowHdr')]/..",
        "//table[contains(@class, 'sapMTable')]//tr[not(contains(@class, 'sapMListTblHeaderRow'))]",
        
        # Selectores específicos de SDWork Center
        "//div[contains(@class, 'sdworkItems')]//div[contains(@class, 'sapMLIB')]",
        "//div[contains(@class, 'issueList')]//div[contains(@class, 'sapMLIB')]",
        "//div[contains(@id, 'issue')]//div[contains(@class, 'sapMLIB')]",
        
        # Selectores genéricos más específicos
        "//div[contains(@class, 'sapMLIB-CTX')]",
        "//div[contains(@class, 'sapMObjectListItem')]",
        "//div[contains(@class, 'sapMListModeMultiSelect')]//div[contains(@class, 'sapMLIB')]"
    ])

    for selector in selectors:
        try:
            rows = driver.find_elements(By.XPATH, selector)
            if len(rows) > 0:
                logger.info(f"Se encontraron {len(rows)} filas con selector: {selector}")
                
                # Filtrar filas válidas
                valid_rows = []
                for row in rows:
                    try:
                        has_content = False
                        text_elements = row.find_elements(By.XPATH, ".//span | .//div | .//a")
                        for element in text_elements:
                            if element.text and element.text.strip():
                                has_content = True
                                break
                                
                        if has_content:
                            # Verificar que no sea un encabezado
                            class_attr = row.get_attribute("class") or ""
                            is_header = "header" in class_attr.lower()
                            if not is_header:
                                valid_rows.append(row)
                    except:
                        valid_rows.append(row)  # Si hay error, incluir por si acaso
                
                if len(valid_rows) > 0:
                    all_rows = valid_rows
                    
                    if len(valid_rows) >= 75:  # Si encontramos muchas filas, probablemente es el selector correcto
                        break
        except Exception as e:
            logger.debug(f"Error con selector {selector}: {e}")
    
    # Si los selectores estándar fallan, usar enfoque alternativo
    if len(all_rows) == 0:
        logger.warning("Usando enfoque alternativo para encontrar filas")
        try:
            any_rows = driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'sapM')] | //tr | //li[contains(@class, 'sapM')]"
            )
            
            for element in any_rows:
                try:
                    # Verificar si parece una fila de datos
                    if element.text and len(element.text.strip()) > 10:
                        children = element.find_elements(By.XPATH, ".//*")
                        if len(children) >= 3:
                            parent_elements = element.find_elements(
                                By.XPATH, 
                                "./ancestor::div[contains(@class, 'sapMList') or contains(@class, 'sapMTable')]"
                            )
                            if len(parent_elements) > 0:
                                all_rows.append(element)
                except:
                    continue
                    
            logger.info(f"Enfoque alternativo encontró {len(all_rows)} posibles filas")
        except Exception as e:
            logger.error(f"Error en enfoque alternativo: {e}")
    
    # Resaltar filas si se solicita
    if highlight and len(all_rows) > 0:
        try:
            driver.execute_script(
                "arguments[0].scrollIntoView(true); arguments[0].style.border = '2px solid red';",
                all_rows[0]
            )
        except:
            pass
    
    # Eliminar duplicados manteniendo el orden
    unique_rows = []
    seen_ids = set()
    
    for row in all_rows:
        try:
            row_id = row.id
            if row_id not in seen_ids:
                seen_ids.add(row_id)
                unique_rows.append(row)
        except:
            # Si no podemos obtener un ID, usar aproximación con texto y clase
            try:
                row_text = row.text[:50] if row.text else ""
                row_class = row.get_attribute("class") or ""
                row_signature = f"{row_text}|{row_class}"
                
                if row_signature not in seen_ids:
                    seen_ids.add(row_signature)
                    unique_rows.append(row)
            except:
                unique_rows.append(row)
    
    logger.info(f"Total de filas únicas encontradas: {len(unique_rows)}")
    return unique_rows

def detect_table_headers(driver: WebDriver) -> Dict[str, int]:
    """
    Detecta y mapea los encabezados de la tabla para mejor extracción
    
    Args:
        driver (WebDriver): WebDriver de Selenium
        
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
            header_rows = driver.find_elements(By.XPATH, selector)
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
        
        logger.warning("No se pudieron detectar encabezados de tabla")
        return {}
        
    except Exception as e:
        logger.error(f"Error al detectar encabezados: {e}")
        return {}

def get_row_cells(row: WebElement) -> List[WebElement]:
    """
    Método mejorado para obtener todas las celdas de una fila
    
    Args:
        row (WebElement): WebElement de Selenium que representa una fila
        
    Returns:
        list: Lista de WebElements que representan celdas
    """
    cells = []
    
    try:
        # Intentar diferentes métodos para obtener celdas en orden de prioridad
        cell_extractors = [
            # 1. Buscar elementos td directamente (tabla HTML estándar)
            lambda r: r.find_elements(By.XPATH, ".//td"),
            
            # 2. Buscar celdas específicas de SAP UI5
            lambda r: r.find_elements(By.XPATH, ".//div[@role='gridcell']"),
            
            # 3. Buscar elementos con clases que indiquen que son celdas
            lambda r: r.find_elements(By.XPATH, ".//*[contains(@class, 'cell') or contains(@class, 'Cell')]"),
            
            # 4. Buscar divs hijos directos como posible celda
            lambda r: r.find_elements(By.XPATH, "./div[not(contains(@class, 'sapUiNoContentPadding'))]"),
            
            # 5. Buscar spans con información relevante
            lambda r: r.find_elements(By.XPATH, ".//span[contains(@id, 'col')]")
        ]
        
        # Intentar cada método hasta encontrar celdas
        for extractor in cell_extractors:
            try:
                extracted_cells = extractor(row)
                if extracted_cells and len(extracted_cells) > 2:  # Necesitamos al menos 3 celdas para ser válidas
                    # Verificar que las celdas tengan texto
                    if all(cell.text.strip() for cell in extracted_cells[:3]):
                        return extracted_cells
            except:
                continue
                
        # Intentar método más específico basado en las capturas de pantalla
        try:
            # Localizar por columnas basadas en la estructura de las imágenes
            columns = ["Title", "Type", "Priority", "Status", "Deadline", "Due Date", "Created By", "Created On"]
            column_cells = []
            
            for i, column in enumerate(columns):
                # Intentar localizar celda específica por su posición o atributos
                xpath_patterns = [
                    f".//div[contains(@aria-label, '{column}')]",
                    f".//div[contains(@aria-colindex, '{i+1}')]",
                    f".//div[contains(@data-column-index, '{i}')]",
                    f".//div[contains(@class, 'col{i+1}')]"
                ]
                
                for xpath in xpath_patterns:
                    cell_candidates = row.find_elements(By.XPATH, xpath)
                    if cell_candidates:
                        column_cells.append(cell_candidates[0])
                        break
            
            if len(column_cells) >= 3:
                return column_cells
        except:
            pass
        
        # Estrategia de respaldo: buscar todos los elementos con texto en la fila
        if not cells:
            # Buscar todos los elementos con texto visible
            text_elements = row.find_elements(By.XPATH, ".//*[normalize-space(text())]")
            
            # Filtrar los que parezcan ser encabezados o elementos de UI
            filtered_elements = []
            for el in text_elements:
                # Excluir elementos que son parte de la UI, no datos
                classes = el.get_attribute("class") or ""
                if not any(ui_class in classes.lower() for ui_class in ["icon", "button", "checkbox", "arrow", "header"]):
                    filtered_elements.append(el)
            
            # Devolver si tenemos suficientes elementos
            if len(filtered_elements) >= 4:
                return filtered_elements
                
    except Exception as e:
        logger.debug(f"Error al extraer celdas: {e}")
    
    return cells

def wait_for_element(
    driver: WebDriver, 
    selector: str, 
    by: By = By.XPATH,
    timeout: float = TIMEOUTS["element_visibility"],
    condition: str = "visible",
    poll_frequency: float = 0.5
) -> bool:
    """
    Espera a que un elemento cumpla cierta condición
    
    Args:
        driver (WebDriver): Instancia del controlador de Selenium
        selector (str): Selector para localizar el elemento
        by (By, optional): Método de localización. Por defecto XPATH.
        timeout (float, optional): Tiempo máximo de espera en segundos. Por defecto 30.
        condition (str, optional): Condición a cumplir ('present', 'visible', 'clickable', 'invisible').
        poll_frequency (float, optional): Frecuencia de sondeo en segundos. Por defecto 0.5.
        
    Returns:
        bool: True si el elemento cumple la condición dentro del tiempo de espera, False en caso contrario
    """
    try:
        wait = WebDriverWait(driver, timeout, poll_frequency=poll_frequency)
        
        # Diccionario de condiciones
        conditions = {
            "present": EC.presence_of_element_located((by, selector)),
            "visible": EC.visibility_of_element_located((by, selector)),
            "clickable": EC.element_to_be_clickable((by, selector)),
            "invisible": EC.invisibility_of_element_located((by, selector))
        }
        
        # Verificar que la condición es válida
        if condition not in conditions:
            logger.warning(f"Condición '{condition}' no reconocida, usando 'visible'")
            condition = "visible"
        
        # Esperar la condición
        wait.until(conditions[condition])
        logger.debug(f"Elemento {selector} cumple condición '{condition}'")
        return True
        
    except TimeoutException:
        logger.warning(f"Tiempo de espera excedido para elemento {selector} con condición '{condition}'")
        return False
    except Exception as e:
        logger.error(f"Error al esperar elemento {selector}: {e}")
        return False

def find_ui5_elements(driver: WebDriver, control_type: str, properties: Dict = None) -> List[WebElement]:
    """
    Encuentra elementos UI5 específicos usando JavaScript
    
    Args:
        driver (WebDriver): WebDriver de Selenium
        control_type (str): Tipo de control UI5 (ej. "sap.m.Input")
        properties (dict, optional): Diccionario de propiedades para filtrar controles
        
    Returns:
        list: Lista de WebElements que coinciden con los criterios
    """
    script = """
    function findUI5Controls(controlType, properties) {
        if (!window.sap || !window.sap.ui) return [];
        
        var controls = sap.ui.getCore().byFieldGroupId().filter(function(control) {
            return control.getMetadata().getName() === controlType;
        });
        
        if (properties) {
            controls = controls.filter(function(control) {
                for (var prop in properties) {
                    if (control.getProperty(prop) !== properties[prop]) {
                        return false;
                    }
                }
                return true;
            });
        }
        
        return controls.map(function(control) {
            return control.getId();
        });
    }
    return findUI5Controls(arguments[0], arguments[1]);
    """
    
    try:
        control_ids = driver.execute_script(script, control_type, properties)
        elements = []
        
        for control_id in control_ids:
            try:
                element = driver.find_element(By.ID, control_id)
                elements.append(element)
            except:
                pass
                
        return elements
    except:
        return []

def check_for_pagination(driver: WebDriver) -> Optional[List[WebElement]]:
    """
    Verifica si la tabla tiene paginación y devuelve los controles
    
    Args:
        driver (WebDriver): WebDriver de Selenium
        
    Returns:
        list: Lista de WebElements que representan controles de paginación, o None si no hay
    """
    try:
        # Selectores para controles de paginación
        pagination_selectors = SELECTORS.get("pagination_controls", [
            "//div[contains(@class, 'sapMPaginator')]",
            "//div[contains(@class, 'sapUiTablePaginator')]",
            "//div[contains(@class, 'pagination')]",
            "//button[contains(@class, 'navButton') or contains(@aria-label, 'Next') or contains(@aria-label, 'Siguiente')]",
            "//span[contains(@class, 'sapMPaginatorButton')]",
            "//button[contains(text(), 'Next') or contains(text(), 'Siguiente')]",
            "//a[contains(@class, 'sapMBtn') and contains(@aria-label, 'Next')]"
        ])
        
        for selector in pagination_selectors:
            elements = driver.find_elements(By.XPATH, selector)
            if elements:
                logger.info(f"Se encontraron controles de paginación: {len(elements)} elementos con selector {selector}")
                return elements
        
        # Buscar elementos "Show More" o "Load More"
        load_more_selectors = SELECTORS.get("load_more_controls", [
            "//button[contains(text(), 'More') or contains(text(), 'más') or contains(text(), 'Show')]",
            "//a[contains(text(), 'More') or contains(text(), 'Load')]",
            "//div[contains(@class, 'sapMListShowMoreButton')]",
            "//span[contains(text(), 'Show') and contains(text(), 'More')]/..",
            "//span[contains(@class, 'sapUiTableColShowMoreButton')]"
        ])
        
        for selector in load_more_selectors:
            elements = driver.find_elements(By.XPATH, selector)
            if elements:
                logger.info(f"Se encontraron botones 'Show More': {len(elements)} elementos con selector {selector}")
                return elements
        
        logger.info("No se encontraron controles de paginación en la tabla")
        return None
        
    except Exception as e:
        logger.error(f"Error al verificar paginación: {e}")
        return None

def click_element_safely(
    driver: WebDriver, 
    element: WebElement,
    use_js: bool = True, 
    retry_attempts: int = 3
) -> bool:
    """
    Intenta hacer clic en un elemento con varios métodos y reintentos
    
    Args:
        driver (WebDriver): WebDriver de Selenium
        element (WebElement): WebElement en el que hacer clic
        use_js (bool): Si es True, intenta usar JavaScript para hacer clic
        retry_attempts (int): Número de reintentos
        
    Returns:
        bool: True si el clic fue exitoso, False en caso contrario
    """
    for attempt in range(retry_attempts):
        try:
            # Asegurar que el elemento es visible
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.5)
            
            if use_js:
                # Método 1: JavaScript click (más confiable en SAP UI5)
                driver.execute_script("arguments[0].click();", element)
                logger.debug(f"Clic realizado con JavaScript en intento {attempt+1}")
                return True
            else:
                # Método 2: Clic normal de Selenium
                element.click()
                logger.debug(f"Clic normal realizado en intento {attempt+1}")
                return True
        except Exception as e:
            if attempt == retry_attempts - 1:
                logger.warning(f"No se pudo hacer clic después de {retry_attempts} intentos: {e}")
            else:
                logger.debug(f"Error en intento {attempt+1}: {e}, reintentando...")
                time.sleep(1)  # Pequeña pausa antes de reintentar
    
    return False

def click_pagination_next(
    driver: WebDriver, 
    pagination_elements: List[WebElement]
) -> bool:
    """
    Hace clic en el botón de siguiente página
    
    Args:
        driver (WebDriver): WebDriver de Selenium
        pagination_elements (List[WebElement]): Lista de elementos de paginación
        
    Returns:
        bool: True si se pudo hacer clic, False en caso contrario
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
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
            time.sleep(0.5)
            
            # Usar la función de clic seguro
            return click_element_safely(driver, next_button)
        
        # Si no se encontró botón específico, intentar con el último elemento
        if pagination_elements and len(pagination_elements) > 0:
            last_element = pagination_elements[-1]
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", last_element)
            time.sleep(0.5)
            return click_element_safely(driver, last_element)
        
        logger.warning("No se pudo identificar o hacer clic en el botón 'Next'")
        return False
        
    except Exception as e:
        logger.error(f"Error al hacer clic en paginación: {e}")
        return False

def detect_table_type(driver: WebDriver) -> str:
    """
    Detecta el tipo de tabla UI5 presente en la página actual.
    
    Los tipos de tabla incluyen: standard_ui5, responsive_table, grid_table y unknown.
    Cada tipo de tabla requiere una estrategia de scroll diferente.
    
    Args:
        driver (WebDriver): WebDriver de Selenium
        
    Returns:
        str: Tipo de tabla detectado ("standard_ui5", "responsive_table", "grid_table" o "unknown")
    """
    try:
        # Buscar patrones característicos de diferentes tipos de tablas
        standard_ui5 = len(driver.find_elements(By.XPATH, "//table[contains(@class, 'sapMListTbl')]"))
        responsive_table = len(driver.find_elements(By.XPATH, "//div[contains(@class, 'sapMListItems')]"))
        grid_table = len(driver.find_elements(By.XPATH, "//div[contains(@class, 'sapUiTable')]"))
        
        # Determinar el tipo de tabla más probable basado en la presencia de elementos
        if standard_ui5 > 0:
            return "standard_ui5"
        elif responsive_table > 0:
            return "responsive_table"
        elif grid_table > 0:
            return "grid_table"
        else:
            return "unknown"
    except Exception as e:
        logger.debug(f"Error al detectar tipo de tabla: {e}")
        return "unknown"  # Si hay error, usar tipo genérico

def optimize_browser_performance(driver: WebDriver) -> bool:
    """
    Ejecuta scripts para mejorar el rendimiento del navegador durante operaciones intensivas
    
    Args:
        driver (WebDriver): WebDriver de Selenium
        
    Returns:
        bool: True si la optimización fue exitosa, False en caso contrario
    """
    try:
        # Script para liberar memoria y reducir carga visual
        performance_script = """
        // Desactivar animaciones y transiciones para mejor rendimiento
        try {
            let styleSheet = document.createElement('style');
            styleSheet.textContent = '* { animation-duration: 0.001s !important; transition-duration: 0.001s !important; }';
            document.head.appendChild(styleSheet);
        } catch(e) {}
        
        // Liberar memoria si está disponible el recolector de basura
        if (window.gc) {
            window.gc();
        }
        
        // Optimizar para scroll (desactivar eventos innecesarios)
        try {
            const observer = window.IntersectionObserver;
            if (observer) {
                // Desconectar observadores de intersección temporalmente
                const observers = performance.getEntriesByType('resource')
                    .filter(entry => entry.initiatorType === 'observer');
                
                for (const obs of observers) {
                    try { obs.disconnect(); } catch(e) {}
                }
            }
        } catch(e) {}
        """
        
        driver.execute_script(performance_script)
        logger.debug("Script de optimización de rendimiento ejecutado")
        return True
    except Exception as e:
        logger.debug(f"Error al optimizar rendimiento del navegador: {e}")
        return False

def get_text_safe(element: WebElement) -> str:
    """
    Obtiene el texto de un elemento de manera segura
    
    Args:
        element (WebElement): Elemento del que obtener el texto
        
    Returns:
        str: Texto del elemento o cadena vacía si hay error
    """
    try:
        return element.text.strip()
    except Exception:
        try:
            # Intentar con JavaScript como alternativa
            driver = element.parent
            return driver.execute_script("return arguments[0].textContent.trim();", element)
        except Exception:
            return ""

def is_element_present(
    driver: WebDriver, 
    selector: str, 
    by: By = By.XPATH,
    timeout: float = 5
) -> bool:
    """
    Verifica si un elemento está presente en la página
    
    Args:
        driver (WebDriver): Instancia del controlador de Selenium
        selector (str): Selector para localizar el elemento
        by (By, optional): Método de localización. Por defecto XPATH.
        timeout (float, optional): Tiempo máximo de espera en segundos. Por defecto 5.
        
    Returns:
        bool: True si el elemento está presente, False en caso contrario
    """
    try:
        wait = WebDriverWait(driver, timeout)
        wait.until(EC.presence_of_element_located((by, selector)))
        return True
    except:
        return False

def is_element_visible(
    driver: WebDriver, 
    selector: str, 
    by: By = By.XPATH,
    timeout: float = 5
) -> bool:
    """
    Verifica si un elemento está visible en la página
    
    Args:
        driver (WebDriver): Instancia del controlador de Selenium
        selector (str): Selector para localizar el elemento
        by (By, optional): Método de localización. Por defecto XPATH.
        timeout (float, optional): Tiempo máximo de espera en segundos. Por defecto 5.
        
    Returns:
        bool: True si el elemento está visible, False en caso contrario
    """
    try:
        wait = WebDriverWait(driver, timeout)
        wait.until(EC.visibility_of_element_located((by, selector)))
        return True
    except:
        return False

def scroll_to_element(
    driver: WebDriver, 
    element: WebElement,
    block_position: str = "center"
) -> bool:
    """
    Desplaza la vista hasta un elemento específico
    
    Args:
        driver (WebDriver): WebDriver de Selenium
        element (WebElement): Elemento al que desplazarse
        block_position (str): Posición de desplazamiento ("start", "center", "end", "nearest")
        
    Returns:
        bool: True si el desplazamiento fue exitoso, False en caso contrario
    """
    try:
        driver.execute_script(
            f"arguments[0].scrollIntoView({{block: '{block_position}', behavior: 'smooth'}});", 
            element
        )
        time.sleep(0.5)  # Pequeña pausa para permitir que termine el desplazamiento
        return True
    except Exception as e:
        logger.debug(f"Error al desplazarse al elemento: {e}")
        return False

def highlight_element(
    driver: WebDriver,
    element: WebElement,
    duration: float = 1.0,
    color: str = "red",
    border_width: int = 2
) -> None:
    """
    Resalta visualmente un elemento en la página
    
    Args:
        driver (WebDriver): WebDriver de Selenium
        element (WebElement): Elemento a resaltar
        duration (float): Duración del resaltado en segundos
        color (str): Color del borde
        border_width (int): Ancho del borde en píxeles
    """
    try:
        # Guardar el estilo original
        original_style = driver.execute_script(
            "return arguments[0].getAttribute('style');", element
        )
        
        # Aplicar el resaltado
        driver.execute_script(
            f"arguments[0].setAttribute('style', arguments[1] + '; border: {border_width}px solid {color} !important; background-color: rgba(255,0,0,0.1) !important;');",
            element,
            original_style or ""
        )
        
        # Esperar la duración del resaltado
        time.sleep(duration)
        
        # Restaurar el estilo original
        driver.execute_script(
            "arguments[0].setAttribute('style', arguments[1]);",
            element,
            original_style or ""
        )
    except Exception as e:
        logger.debug(f"Error al resaltar elemento: {e}")

def perform_data_extraction(
    driver: WebDriver,
    extractor_function: Callable,
    rows: List[WebElement],
    batch_size: int = 10
) -> List[Dict]:
    """
    Ejecuta la extracción de datos de manera optimizada por lotes
    
    Args:
        driver (WebDriver): WebDriver de Selenium
        extractor_function (Callable): Función que extrae datos de una fila
        rows (List[WebElement]): Lista de filas de la tabla
        batch_size (int): Tamaño del lote para procesamiento
        
    Returns:
        List[Dict]: Lista de diccionarios con los datos extraídos
    """
    result = []
    total_rows = len(rows)
    
    # Optimizar el navegador antes de comenzar la extracción
    optimize_browser_performance(driver)
    
    logger.info(f"Iniciando extracción de datos para {total_rows} filas")
    
    # Procesar en lotes para mejor rendimiento y feedback
    for batch_start in range(0, total_rows, batch_size):
        batch_end = min(batch_start + batch_size, total_rows)
        current_batch = rows[batch_start:batch_end]
        
        logger.info(f"Procesando lote {batch_start//batch_size + 1} ({batch_start+1}-{batch_end} de {total_rows})")
        
        batch_results = []
        for row in current_batch:
            try:
                # Asegurar que la fila es visible para extracción
                scroll_to_element(driver, row)
                
                # Extraer datos utilizando la función proporcionada
                row_data = extractor_function(row)
                if row_data:
                    batch_results.append(row_data)
            except StaleElementReferenceException:
                logger.warning("Elemento obsoleto detectado, saltando fila")
                continue
            except Exception as e:
                logger.error(f"Error al extraer datos de fila: {e}")
                continue
        
        # Agregar los resultados del lote actual
        result.extend(batch_results)
        logger.info(f"Lote completado: {len(batch_results)} filas procesadas correctamente")
        
        # Pequeña pausa entre lotes para reducir la carga
        if batch_end < total_rows:
            time.sleep(0.5)
    
    logger.info(f"Extracción completa: {len(result)} filas procesadas de un total de {total_rows}")
    return result