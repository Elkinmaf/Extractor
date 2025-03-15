"""
Módulo config - Configuración global para SAP Issues Extractor

Este módulo contiene la configuración global de la aplicación, incluyendo
constantes, rutas de archivo, colores para la interfaz, etc.
"""

from config.settings import (
    SAP_COLORS, 
    TIMEOUTS, 
    EXTRACTION_CONFIG, 
    BROWSER_CONFIG,
    SELECTORS,
    load_json_config
)

# Facilitar la importación directa
__all__ = [
    'SAP_COLORS', 
    'TIMEOUTS', 
    'EXTRACTION_CONFIG', 
    'BROWSER_CONFIG',
    'SELECTORS',
    'load_json_config'
]
