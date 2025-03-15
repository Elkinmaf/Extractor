#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
dialogs.py - Diálogos adicionales para la interfaz gráfica
---
Este módulo contiene clases para los diálogos secundarios de la aplicación,
como el diálogo "Acerca de" y el diálogo de configuración.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import webbrowser

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Importaciones de otros módulos del proyecto
from config.settings import SAP_COLORS, load_json_config, save_json_config, CONFIG_FILE

# Configurar logger
import logging
logger = logging.getLogger(__name__)

class BaseDialog:
    """Clase base para diálogos modales"""
    
    def __init__(self, parent, title="Diálogo", width=400, height=300, resizable=(False, False)):
        """
        Inicializa un diálogo base
        
        Args:
            parent: Ventana padre
            title (str): Título del diálogo
            width (int): Ancho de la ventana
            height (int): Alto de la ventana
            resizable (tuple): Si la ventana es redimensionable (horizontal, vertical)
        """
        self.parent = parent
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry(f"{width}x{height}")
        self.dialog.resizable(resizable[0], resizable[1])
        self.dialog.transient(parent)  # Hacer la ventana modal
        self.dialog.grab_set()         # Capturar todos los eventos
        
        # Centrar el diálogo
        self.center_dialog()
        
        # Manejar cierre
        self.dialog.protocol("WM_DELETE_WINDOW", self.close)
        
    def center_dialog(self):
        """Centra el diálogo en la pantalla"""
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        
    def show(self):
        """Muestra el diálogo y espera a que se cierre"""
        self.dialog.wait_window()
        
    def close(self):
        """Cierra el diálogo"""
        self.dialog.destroy()

class AboutDialog(BaseDialog):
    """Diálogo Acerca de la aplicación"""
    
    def __init__(self, parent):
        """Inicializa el diálogo Acerca de"""
        super().__init__(parent, "Acerca de SAP Issues Extractor", 500, 400)
        
        # Crear contenido del diálogo
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Logo SAP (si está disponible)
        self.logo = None
        if PIL_AVAILABLE:
            try:
                logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "sap_logo.png")
                if os.path.exists(logo_path):
                    logo_image = Image.open(logo_path)
                    logo_image = logo_image.resize((100, 100), Image.LANCZOS)
                    self.logo = ImageTk.PhotoImage(logo_image)
                    
                    logo_label = tk.Label(main_frame, image=self.logo)
                    logo_label.pack(pady=10)
            except Exception as e:
                logger.debug(f"No se pudo cargar el logo: {e}")
        
        # Título
        title_label = ttk.Label(
            main_frame, 
            text="SAP Issues Extractor",
            font=("Arial", 16, "bold"),
            foreground=SAP_COLORS["primary"]
        )
        title_label.pack(pady=5)
        
        # Versión
        version_label = ttk.Label(
            main_frame, 
            text="Versión 2.0",
            font=("Arial", 12)
        )
        version_label.pack(pady=5)
        
        # Fecha
        current_year = datetime.now().year
        date_label = ttk.Label(
            main_frame, 
            text=f"© {current_year}",
            font=("Arial", 10)
        )
        date_label.pack(pady=5)
        
        # Descripción
        description = """
        Una herramienta para extraer automáticamente información de issues
        desde la interfaz SAP. Optimiza el proceso de seguimiento y gestión
        de recomendaciones SAP EPM.
        """
        desc_label = ttk.Label(
            main_frame, 
            text=description,
            font=("Arial", 10),
            justify="center",
            wraplength=400
        )
        desc_label.pack(pady=10)
        
        # Botones
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=20)
        
        # Botón para abrir página web (si existiera)
        web_btn = ttk.Button(
            btn_frame,
            text="Página web",
            command=self.open_website
        )
        web_btn.pack(side=tk.LEFT, padx=10)
        
        # Botón para cerrar
        close_btn = ttk.Button(
            btn_frame,
            text="Cerrar",
            command=self.close
        )
        close_btn.pack(side=tk.RIGHT, padx=10)
        
    def open_website(self):
        """Abre la página web de la aplicación"""
        try:
            webbrowser.open("https://www.sap.com")
        except Exception as e:
            logger.error(f"Error al abrir página web: {e}")
            messagebox.showerror("Error", "No se pudo abrir la página web")

class SettingsDialog(BaseDialog):
    """Diálogo de configuración de la aplicación"""
    
    def __init__(self, parent, extractor_instance):
        """
        Inicializa el diálogo de configuración
        
        Args:
            parent: Ventana padre
            extractor_instance: Instancia de la clase IssuesExtractor
        """
        super().__init__(parent, "Configuración", 550, 450, resizable=(True, True))
        self.extractor = extractor_instance
        
        # Cargar configuración actual
        self.config = load_json_config(CONFIG_FILE, {})
        
        # Crear variables Tkinter para los controles
        self.create_variables()
        
        # Crear contenido del diálogo
        self.create_interface()
        
    def create_variables(self):
        """Crea las variables Tkinter para los controles"""
        # Valores predeterminados
        browser_defaults = self.config.get('browser', {})
        extraction_defaults = self.config.get('extraction', {})
        
        # Variables del navegador
        self.var_browser_profile_dir = tk.StringVar(value=browser_defaults.get('profile_dir', ''))
        self.var_browser_headless = tk.BooleanVar(value=browser_defaults.get('headless', False))
        
        # Variables de extracción
        self.var_extraction_attempts = tk.IntVar(value=extraction_defaults.get('max_attempts', 3))
        self.var_extraction_scroll = tk.IntVar(value=extraction_defaults.get('scroll_max_attempts', 100))
        self.var_extraction_timeout = tk.DoubleVar(value=extraction_defaults.get('timeout', 30.0))
        
    def create_interface(self):
        """Crea la interfaz del diálogo"""
        # Contenedor principal con notebook para pestañas
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Pestaña 1: Configuración del navegador
        browser_tab = ttk.Frame(notebook, padding=10)
        notebook.add(browser_tab, text="Navegador")
        self.create_browser_tab(browser_tab)
        
        # Pestaña 2: Configuración de extracción
        extraction_tab = ttk.Frame(notebook, padding=10)
        notebook.add(extraction_tab, text="Extracción")
        self.create_extraction_tab(extraction_tab)
        
        # Pestaña 3: Apariencia
        appearance_tab = ttk.Frame(notebook, padding=10)
        notebook.add(appearance_tab, text="Apariencia")
        self.create_appearance_tab(appearance_tab)
        
        # Botones de acción
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        # Botón para guardar
        save_btn = ttk.Button(
            btn_frame,
            text="Guardar configuración",
            command=self.save_config
        )
        save_btn.pack(side=tk.RIGHT, padx=5)
        
        # Botón para restaurar valores predeterminados
        defaults_btn = ttk.Button(
            btn_frame,
            text="Restaurar predeterminados",
            command=self.restore_defaults
        )
        defaults_btn.pack(side=tk.LEFT, padx=5)
        
    def create_browser_tab(self, parent):
        """Crea el contenido de la pestaña de navegador"""
        # Título
        title_label = ttk.Label(
            parent,
            text="Configuración del Navegador",
            font=("Arial", 12, "bold")
        )
        title_label.pack(anchor=tk.W, pady=10)
        
        # Frame para controles
        controls_frame = ttk.Frame(parent)
        controls_frame.pack(fill=tk.BOTH, expand=True)
        
        # Directorio de perfil
        profile_label = ttk.Label(
            controls_frame,
            text="Directorio de perfil de Chrome:"
        )
        profile_label.grid(row=0, column=0, sticky=tk.W, pady=5)
        
        profile_entry = ttk.Entry(
            controls_frame,
            textvariable=self.var_browser_profile_dir,
            width=40
        )
        profile_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        
        profile_btn = ttk.Button(
            controls_frame,
            text="Explorar",
            command=self.select_profile_dir
        )
        profile_btn.grid(row=0, column=2, pady=5, padx=5)
        
        # Checkbox de modo headless
        headless_check = ttk.Checkbutton(
            controls_frame,
            text="Usar modo headless (sin interfaz gráfica)",
            variable=self.var_browser_headless
        )
        headless_check.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # Espaciador para empujar todos los controles hacia arriba
        controls_frame.columnconfigure(1, weight=1)
        spacer = ttk.Frame(controls_frame)
        spacer.grid(row=10, column=0, pady=10)
        controls_frame.rowconfigure(10, weight=1)
        
    def create_extraction_tab(self, parent):
        """Crea el contenido de la pestaña de extracción"""
        # Título
        title_label = ttk.Label(
            parent,
            text="Configuración de Extracción",
            font=("Arial", 12, "bold")
        )
        title_label.pack(anchor=tk.W, pady=10)
        
        # Frame para controles
        controls_frame = ttk.Frame(parent)
        controls_frame.pack(fill=tk.BOTH, expand=True)
        
        # Intentos máximos
        attempts_label = ttk.Label(
            controls_frame,
            text="Intentos máximos de extracción:"
        )
        attempts_label.grid(row=0, column=0, sticky=tk.W, pady=5)
        
        attempts_spin = ttk.Spinbox(
            controls_frame,
            from_=1,
            to=10,
            textvariable=self.var_extraction_attempts,
            width=5
        )
        attempts_spin.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Intentos de scroll
        scroll_label = ttk.Label(
            controls_frame,
            text="Intentos máximos de scroll:"
        )
        scroll_label.grid(row=1, column=0, sticky=tk.W, pady=5)
        
        scroll_spin = ttk.Spinbox(
            controls_frame,
            from_=10,
            to=200,
            textvariable=self.var_extraction_scroll,
            width=5
        )
        scroll_spin.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Timeout
        timeout_label = ttk.Label(
            controls_frame,
            text="Tiempo máximo de espera (segundos):"
        )
        timeout_label.grid(row=2, column=0, sticky=tk.W, pady=5)
        
        timeout_spin = ttk.Spinbox(
            controls_frame,
            from_=1,
            to=120,
            textvariable=self.var_extraction_timeout,
            width=5
        )
        timeout_spin.grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Espaciador para empujar todos los controles hacia arriba
        controls_frame.columnconfigure(2, weight=1)
        spacer = ttk.Frame(controls_frame)
        spacer.grid(row=10, column=0, pady=10)
        controls_frame.rowconfigure(10, weight=1)
        
    def create_appearance_tab(self, parent):
        """Crea el contenido de la pestaña de apariencia"""
        # Título
        title_label = ttk.Label(
            parent,
            text="Configuración de Apariencia",
            font=("Arial", 12, "bold")
        )
        title_label.pack(anchor=tk.W, pady=10)
        
        # Mostrar colores SAP disponibles
        color_frame = ttk.LabelFrame(parent, text="Colores SAP")
        color_frame.pack(fill=tk.X, pady=10, padx=5)
        
        row = 0
        col = 0
        for color_name, color_value in SAP_COLORS.items():
            # Crear un frame con el color
            color_box = tk.Frame(
                color_frame,
                background=color_value,
                width=30,
                height=30,
                borderwidth=1,
                relief=tk.RAISED
            )
            color_box.grid(row=row, column=col, padx=5, pady=5)
            
            # Etiqueta con el nombre
            color_label = ttk.Label(
                color_frame,
                text=color_name,
                font=("Arial", 8)
            )
            color_label.grid(row=row+1, column=col, padx=5)
            
            # Avanzar a la siguiente columna o fila
            col += 1
            if col > 4:  # 5 colores por fila
                col = 0
                row += 2
                
        # Nota informativa
        note_label = ttk.Label(
            parent,
            text="Nota: Estas configuraciones se aplicarán en el próximo inicio de la aplicación.",
            font=("Arial", 9, "italic"),
            foreground="#666666"
        )
        note_label.pack(anchor=tk.W, pady=20)
        
    def select_profile_dir(self):
        """Abre un diálogo para seleccionar el directorio de perfil"""
        from tkinter import filedialog
        
        current_dir = self.var_browser_profile_dir.get()
        if not current_dir or not os.path.exists(current_dir):
            current_dir = os.path.join(os.environ.get('USERPROFILE', os.path.expanduser('~')), 
                                     'AppData', 'Local', 'Google', 'Chrome')
        
        directory = filedialog.askdirectory(
            initialdir=current_dir,
            title="Seleccionar directorio de perfil de Chrome"
        )
        
        if directory:
            self.var_browser_profile_dir.set(directory)
            
    def save_config(self):
        """Guarda la configuración actual"""
        try:
            # Recopilar los valores de las variables
            config = {
                'browser': {
                    'profile_dir': self.var_browser_profile_dir.get(),
                    'headless': self.var_browser_headless.get()
                },
                'extraction': {
                    'max_attempts': self.var_extraction_attempts.get(),
                    'scroll_max_attempts': self.var_extraction_scroll.get(),
                    'timeout': self.var_extraction_timeout.get()
                }
            }
            
            # Guardar en el archivo de configuración
            if save_json_config(CONFIG_FILE, config):
                messagebox.showinfo("Configuración guardada", "La configuración se ha guardado correctamente.")
                self.close()
            else:
                messagebox.showerror("Error", "No se pudo guardar la configuración.")
                
        except Exception as e:
            logger.error(f"Error al guardar configuración: {e}")
            messagebox.showerror("Error", f"No se pudo guardar la configuración: {e}")
            
    def restore_defaults(self):
        """Restaura los valores predeterminados"""
        if messagebox.askyesno("Restaurar predeterminados", 
                            "¿Está seguro de restaurar todos los valores a sus predeterminados?"):
            # Browser defaults
            self.var_browser_profile_dir.set(os.path.join(
                os.environ.get('USERPROFILE', os.path.expanduser('~')), 
                'AppData', 'Local', 'Google', 'Chrome', 'SAP_Automation'
            ))
            self.var_browser_headless.set(False)
            
            # Extraction defaults
            self.var_extraction_attempts.set(3)
            self.var_extraction_scroll.set(100)
            self.var_extraction_timeout.set(30.0)
            
            messagebox.showinfo("Valores restaurados", 
                              "Se han restaurado los valores predeterminados. Haga clic en Guardar para aplicarlos.")
