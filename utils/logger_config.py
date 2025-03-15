#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
logger_config.py - Configuración del sistema de logging
---
Este módulo proporciona funciones para configurar el sistema de logging
con diferentes niveles y formatos, permitiendo registro en archivos y consola.
También incluye soporte para mostrar logs en widgets de interfaz gráfica.
"""

import os
import sys
import logging
import traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Importar configuraciones globales
from config.settings import LOGS_DIR

# Asegurar que el directorio de logs existe
os.makedirs(LOGS_DIR, exist_ok=True)

def setup_logger(name=None, level=logging.INFO, log_to_console=True, log_file=None):
    """
    Configura y devuelve un logger con los manejadores especificados
    
    Args:
        name (str, optional): Nombre del logger. Si es None, se usa el logger raíz.
        level (int, optional): Nivel de logging (DEBUG, INFO, etc.). Por defecto INFO.
        log_to_console (bool, optional): Si se debe mostrar logs en consola. Por defecto True.
        log_file (str, optional): Nombre específico para el archivo de log. Si es None, se genera automáticamente.
    
    Returns:
        logging.Logger: Logger configurado
    """
    # Obtener el logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Limpiar handlers existentes
    if logger.handlers:
        logger.handlers.clear()
    
    # Formato detallado para los logs
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(module)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Formato más simple para la consola
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    
    # Configurar archivo de log rotativo
    if not log_file:
        log_file = f"extraccion_issues_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    log_path = os.path.join(LOGS_DIR, log_file)
    
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(level)
    logger.addHandler(file_handler)
    
    # Opcionalmente, agregar manejador de consola
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(level)
        logger.addHandler(console_handler)
    
    return logger

def log_exceptions(logger, level=logging.ERROR):
    """
    Decorador para registrar excepciones en funciones
    
    Args:
        logger (logging.Logger): Logger a utilizar
        level (int, optional): Nivel de logging para las excepciones. Por defecto ERROR.
    
    Returns:
        function: Decorador configurado
    
    Example:
        @log_exceptions(logger)
        def mi_funcion():
            # Si ocurre una excepción, será registrada automáticamente
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.log(level, f"Excepción en {func.__name__}: {e}")
                logger.log(level, f"Traza: {traceback.format_exc()}")
                raise
        return wrapper
    return decorator

class GUILogHandler(logging.Handler):
    """
    Handler personalizado para enviar logs a un widget Text de Tkinter
    """
    def __init__(self, text_widget):
        """
        Inicializa el handler con un widget Text de Tkinter
        
        Args:
            text_widget: Widget Text de Tkinter para mostrar logs
        """
        super().__init__()
        self.text_widget = text_widget
        self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    def emit(self, record):
        """
        Emite un registro de log al widget Text
        
        Args:
            record: Registro de log a emitir
        """
        msg = self.format(record)
        
        def append():
            self.text_widget.configure(state='normal')
            
            # Agregar marca de tiempo y nivel con color
            time_str = msg.split(' - ')[0] + ' - '
            level_str = record.levelname + ' - '
            msg_content = msg.split(' - ', 2)[2] if len(msg.split(' - ')) > 2 else ""
            
            self.text_widget.insert('end', time_str, "INFO")
            self.text_widget.insert('end', level_str, record.levelname)
            self.text_widget.insert('end', msg_content + '\n', record.levelname)
            
            self.text_widget.configure(state='disabled')
            self.text_widget.see('end')  # Asegurar que se muestre la última línea
            
            # Limitar tamaño del log
            self._limit_log_length()
            
        # Llamar a append desde el hilo principal
        self.text_widget.after(0, append)
    
    def _limit_log_length(self, max_lines=1000):
        """
        Limita el número de líneas en el widget Text
        
        Args:
            max_lines (int): Número máximo de líneas a mantener
        """
        if float(self.text_widget.index('end-1c').split('.')[0]) > max_lines:
            self.text_widget.configure(state='normal')
            self.text_widget.delete('1.0', f'{max_lines//2}.0')
            self.text_widget.configure(state='disabled')

def setup_gui_logger(logger, text_widget):
    """
    Configura un logger para enviar mensajes a un widget Text de Tkinter
    
    Args:
        logger (logging.Logger): Logger a configurar
        text_widget: Widget Text para mostrar logs
    """
    # Crear handler para el widget Text
    gui_handler = GUILogHandler(text_widget)
    gui_handler.setLevel(logging.INFO)
    
    # Añadir el handler al logger
    logger.addHandler(gui_handler)
    
    # Preparar tags de colores en el widget Text
    text_widget.tag_configure("INFO", foreground="black")
    text_widget.tag_configure("DEBUG", foreground="#555555")
    text_widget.tag_configure("WARNING", foreground="#CC6600")
    text_widget.tag_configure("ERROR", foreground="#990000")
    text_widget.tag_configure("CRITICAL", foreground="#FF0000", background="#FFCCCC")
    
    # Desactivar la edición del widget
    text_widget.configure(state='disabled')

def setup_selenium_logger(level=logging.WARNING):
    """
    Configura el logger específico para Selenium
    
    Reduce el ruido de logs de selenium configurando un nivel más restrictivo.
    
    Args:
        level (int, optional): Nivel de logging. Por defecto WARNING.
    """
    # Configurar loggers específicos de Selenium/Webdriver
    for logger_name in ['selenium', 'urllib3', 'webdriver']:
        logging.getLogger(logger_name).setLevel(level)

# Crear logger global para la aplicación
logger = setup_logger('sap_extractor')
