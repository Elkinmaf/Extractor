"""
Módulo ui - Interfaz de usuario para SAP Issues Extractor

Este módulo contiene las clases para la interfaz gráfica de usuario,
incluyendo la ventana principal y diálogos adicionales.
"""

from ui.main_window import MainWindow
from ui.dialogs import AboutDialog, SettingsDialog

# Facilitar la importación directa
__all__ = ['MainWindow', 'AboutDialog', 'SettingsDialog', 'custom_dialogs']