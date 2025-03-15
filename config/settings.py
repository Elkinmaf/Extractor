#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
settings.py - Configuraciones globales para SAP Issues Extractor
---
Este módulo contiene constantes, ajustes de configuración y variables 
globales que son utilizadas por múltiples componentes del sistema.
"""

import os
import json
import logging

# =========================================================================
# DIRECTORIOS Y RUTAS
# =========================================================================

# Directorio base del proyecto (para rutas relativas)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Directorios principales
CONFIG_DIR = os.path.join(BASE_DIR, "config")
DATA_DIR = os.path.join(BASE_DIR, "data")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# Crear directorios necesarios
for directory in [CONFIG_DIR, DATA_DIR, LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Archivos importantes
DB_PATH = os.path.join(DATA_DIR, "sap_extraction.db")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
API_CONFIG_FILE = os.path.join(CONFIG_DIR, "api_config.json")

# =========================================================================
# ESTILOS Y APARIENCIA
# =========================================================================

# Colores estilo SAP para la interfaz gráfica
SAP_COLORS = {
    "primary": "#1870C5",    # Azul SAP
    "secondary": "#354A5F",  # Azul oscuro SAP
    "success": "#107E3E",    # Verde SAP
    "warning": "#E9730C",    # Naranja SAP
    "danger": "#BB0000",     # Rojo SAP
    "light": "#F5F6F7",      # Gris claro SAP
    "dark": "#32363A",       # Gris oscuro SAP
    "white": "#FFFFFF",
    "gray": "#D3D7D9",
    "text": "#000000"        # Texto negro para máximo contraste
}

# =========================================================================
# TIEMPOS DE ESPERA
# =========================================================================

# Tiempos de espera para operaciones (en segundos)
TIMEOUTS = {
    "browser": 60,           # Tiempo máximo global para operaciones del navegador
    "page_load": 60,         # Tiempo máximo para cargar una página completa
    "element_visibility": 30, # Tiempo máximo para que un elemento sea visible
    "ajax_completion": 20,   # Tiempo máximo para completar peticiones AJAX
    "typing_delay": 0.3,     # Tiempo entre caracteres al escribir en campos
    "dropdown_delay": 2,     # Tiempo de espera para que aparezcan opciones desplegables
    "animation_delay": 1.5,  # Tiempo para completar animaciones UI
    "extraction_retry": 5    # Tiempo entre reintentos de extracción
}

# Tiempos de espera para operaciones (en segundos)
BROWSER_TIMEOUT = 60           # Tiempo máximo global para operaciones del navegador
MAX_RETRY_ATTEMPTS = 3         # Número máximo de intentos para operaciones críticas

# =========================================================================
# CONFIGURACIÓN DE EXTRACCIÓN
# =========================================================================

# Parámetros para el proceso de extracción
EXTRACTION_CONFIG = {
    "max_attempts": 3,       # Número máximo de intentos de extracción
    "scroll_max_attempts": 100, # Intentos máximos de scroll para cargar todos los elementos
    "no_change_threshold": 10, # Número de intentos sin cambios antes de terminar el scroll
    "default_issues_count": 100, # Cantidad predeterminada de issues a extraer si no se puede determinar
    "extraction_batch_size": 10, # Tamaño de lote para reportar progreso durante la extracción
    "page_limit": 20,        # Límite de páginas a procesar por seguridad
}

# =========================================================================
# CONFIGURACIÓN DEL NAVEGADOR
# =========================================================================

# Perfil y opciones del navegador Chrome
CHROME_PROFILE_DIR = os.path.join(os.environ.get('USERPROFILE', os.path.expanduser('~')), 
                              'AppData', 'Local', 'Google', 'Chrome', 'SAP_Automation')

BROWSER_CONFIG = {
    "profile_dir": CHROME_PROFILE_DIR,
    "use_headless": False,   # Usar modo headless (sin interfaz gráfica)
    "allow_gpu": False,      # Permitir aceleración GPU
    "disable_extensions": True, # Deshabilitar extensiones para mejorar rendimiento
    "disable_infobars": True, # Deshabilitar barras de información de Chrome
}

# =========================================================================
# SELECTORES PARA ELEMENTOS WEB
# =========================================================================

# Selectores para encontrar elementos web en SAP
SELECTORS = {
    "customer_field": [
        "//input[@placeholder='Enter Customer ID or Name']",
        "//input[contains(@placeholder, 'Customer')]",
        "//input[@id='customer']",
        "//input[contains(@aria-label, 'Customer')]",
        "//div[contains(text(), 'Customer')]/following-sibling::div//input",
    ],
    "project_field": [
        "//input[contains(@placeholder, 'Project')]", 
        "//input[@id='project']", 
        "//input[contains(@aria-label, 'Project')]",
        "//input[contains(@id, 'project')]",
    ],
    "search_button": [
        "//button[contains(@aria-label, 'Search')]",
        "//button[@title='Search']",
        "//span[contains(text(), 'Search')]/parent::button",
    ],
    "issues_tab": [
        "//div[contains(text(), 'Issues')] | //span[contains(text(), 'Issues')]",
        "//li[@role='tab']//div[contains(text(), 'Issues')]",
        "//a[contains(text(), 'Issues')]",
    ],
    "table_rows": [
        "//table[contains(@class, 'sapMListTbl')]/tbody/tr[not(contains(@class, 'sapMListTblHeader'))]",
        "//div[contains(@class, 'sapMList')]//li[contains(@class, 'sapMLIB')]",
        "//div[@role='row'][not(contains(@class, 'sapMListHeaderSubTitleItems'))]",
    ]
}

# =========================================================================
# FUNCIONES AUXILIARES
# =========================================================================

def load_json_config(file_path, default=None):
    """
    Carga configuración desde un archivo JSON
    
    Args:
        file_path (str): Ruta al archivo JSON
        default (dict, optional): Configuración predeterminada si el archivo no existe
        
    Returns:
        dict: Configuración cargada o valor predeterminado
    """
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"Error al cargar configuración desde {file_path}: {e}")
    
    return default if default is not None else {}

def save_json_config(file_path, config_data):
    """
    Guarda configuración en un archivo JSON
    
    Args:
        file_path (str): Ruta al archivo JSON
        config_data (dict): Datos de configuración a guardar
        
    Returns:
        bool: True si la operación fue exitosa, False en caso contrario
    """
    try:
        # Asegurar que el directorio existe
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)
        return True
    except Exception as e:
        logging.error(f"Error al guardar configuración en {file_path}: {e}")
        return False
