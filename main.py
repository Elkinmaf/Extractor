#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script principal para SAP Issues Extractor
---
Este es el punto de entrada principal para la aplicación de extracción de issues de SAP.
Coordina la inicialización de componentes y maneja la lógica de ejecución en diferentes
modos (GUI o consola).
"""

  
import io

import os
os.system("chcp 65001")
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
import logging
import traceback
from datetime import datetime
from tools.vba_extractor import VBAExtractor


from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging

# Configurar logging básico inicial
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(
    log_dir, f"extraccion_issues_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Verificar que estamos ejecutando desde el directorio principal del proyecto
def ensure_project_root():
    """Asegura que el script se ejecute desde el directorio raíz del proyecto"""
    current_dir = os.path.basename(os.getcwd())
    if current_dir == 'sap_issues_extractor':
        # Ya estamos en el directorio raíz
        return True
    elif 'sap_issues_extractor' in os.listdir('.'):
        # Cambiar al directorio raíz
        os.chdir('sap_issues_extractor')
        return True
    else:
        print("Error: Este script debe ejecutarse desde el directorio raíz del proyecto 'sap_issues_extractor'")
        return False

def check_required_packages():
    """
    Verifica que estén instalados los paquetes requeridos
    
    Returns:
        list: Lista de paquetes faltantes
    """
    required_packages = {
        "selenium": "Para automatización web",
        "pandas": "Para procesamiento de datos",
        "openpyxl": "Para manejo de archivos Excel"
    }
    
    missing = []
    for package, description in required_packages.items():
        try:
            __import__(package)
        except ImportError:
            missing.append(f"{package} ({description})")
    
    return missing

def create_shortcut(target_path, shortcut_path=None, icon_path=None):
    """
    Crea un acceso directo para la aplicación en Windows
    
    Args:
        target_path (str): Ruta al ejecutable
        shortcut_path (str, optional): Ruta donde crear el acceso directo
        icon_path (str, optional): Ruta al ícono
        
    Returns:
        str or None: Ruta al acceso directo creado, o None si falló
    """
    try:
        if not shortcut_path:
            desktop_path = os.path.join(os.environ['USERPROFILE'], 'Desktop')
            shortcut_path = os.path.join(desktop_path, "SAP Issues Extractor.lnk")
            
        if os.path.exists(shortcut_path):
            return shortcut_path
        
        # Solo en Windows
        if sys.platform != 'win32':
            logger.warning("La creación de accesos directos solo está soportada en Windows")
            return None
            
        import winshell
        from win32com.client import Dispatch
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = target_path
        shortcut.WorkingDirectory = os.path.dirname(target_path)
        if icon_path:
            shortcut.IconLocation = icon_path
        shortcut.save()
        
        return shortcut_path
    except Exception as e:
        logger.error(f"Error al crear acceso directo: {e}")
        return None

def main():
    """
    Función principal que ejecuta la aplicación
    
    Controla el flujo principal del programa, maneja excepciones globales,
    y decide entre modo GUI o consola.
    """
    # Asegurar que estamos en el directorio raíz del proyecto
    if not ensure_project_root():
        sys.exit(1)
    
    logger.info("=== Iniciando SAP Issues Extractor ===")
    
    # Verificar paquetes requeridos
    missing_packages = check_required_packages()
    if missing_packages:
        print("Faltan las siguientes bibliotecas necesarias:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nPor favor, instálalas usando:")
        print(f"pip install {' '.join([p.split()[0] for p in missing_packages])}")
        input("\nPresiona ENTER para salir...")
        sys.exit(1)
    
    # Notificar sobre Pillow, pero no detener la ejecución
    try:
        __import__("PIL")
    except ImportError:
        print("Nota: La biblioteca Pillow no está disponible. Algunas características visuales estarán limitadas.")
        print("Si deseas instalarla, ejecuta: pip install Pillow")
    
    # Importar la clase principal
    try:
        from extractor.issues_extractor import IssuesExtractor, run_console_mode
    except ImportError as e:
        logger.critical(f"Error al importar módulos: {e}")
        print(f"Error crítico: {e}")
        print("Asegúrate de estar ejecutando el script desde el directorio raíz del proyecto.")
        input("\nPresiona ENTER para salir...")
        sys.exit(1)
    
    try:
        # Determinar modo de ejecución
        if len(sys.argv) > 1 and sys.argv[1] == "--console":
            # Modo consola
            logger.info("Ejecutando en modo consola")
            run_console_mode()
        else:
            # Modo interfaz gráfica (predeterminado)
            logger.info("Ejecutando en modo GUI")
            extractor = IssuesExtractor()
            extractor.main_gui()
            
        logger.info("=== Proceso de extracción finalizado ===")
        
    except Exception as e:
        # Capturar y registrar cualquier error no manejado
        logger.critical(f"Error crítico en la ejecución: {e}")
        logger.critical(traceback.format_exc())
        
        print(f"\n¡ERROR! Se ha producido un error crítico: {e}")
        print(f"Por favor, revisa el archivo de log para más detalles: {log_file}")
        
        # En modo consola, mantener la ventana abierta para ver el error
        if len(sys.argv) > 1 and sys.argv[1] == "--console":
            input("\nPresiona ENTER para cerrar...")

if __name__ == "__main__":
    main()
