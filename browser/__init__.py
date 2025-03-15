"""
Módulo browser - Automatización del navegador para SAP Issues Extractor

Este módulo contiene clases para la automatización del navegador web,
especializadas en la interacción con la interfaz de SAP.
"""

from browser.element_finder import (
    find_element, find_elements, wait_for_element, click_element_safely,
    get_text_safe, is_element_present, is_element_visible, detect_table_type
)

from browser.element_finder_sap import (
    find_sap_input, find_sap_combobox, find_sap_button,
    interact_with_sap_dropdown, find_and_click_sap_tab, 
    wait_for_sap_busy_indicator_to_disappear, get_sap_table_data
)

# Exportar todo para ser accesible desde browser.*
__all__ = [
    'find_element', 'find_elements', 'wait_for_element', 'click_element_safely',
    'get_text_safe', 'is_element_present', 'is_element_visible', 'detect_table_type',
    'find_sap_input', 'find_sap_combobox', 'find_sap_button', 
    'interact_with_sap_dropdown', 'find_and_click_sap_tab',
    'wait_for_sap_busy_indicator_to_disappear', 'get_sap_table_data'
]