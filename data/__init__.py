"""
Módulo data - Gestión de datos para SAP Issues Extractor

Este módulo contiene clases para la gestión de datos, incluyendo
el acceso a la base de datos SQLite y la manipulación de archivos Excel.
"""

from data.database_manager import DatabaseManager
from data.excel_manager import ExcelManager

# Facilitar la importación directa
__all__ = ['DatabaseManager', 'ExcelManager']