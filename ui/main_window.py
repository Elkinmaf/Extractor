#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
main_window.py - Implementación de la ventana principal de la interfaz gráfica
---
Este módulo contiene la clase MainWindow que implementa la interfaz gráfica
principal del extractor de issues de SAP, incluyendo todos los controles
y manejadores de eventos necesarios.
"""

import os
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

# Intentar importar PIL para funciones gráficas mejoradas
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Importaciones de otros módulos del proyecto
from config.settings import SAP_COLORS
from utils.logger_config import setup_logger, setup_gui_logger
from ui.dialogs import AboutDialog, SettingsDialog

# Configurar logger
logger = setup_logger(__name__)

class MainWindow:
    """
    Clase principal para la interfaz gráfica de usuario del extractor de SAP.
    
    Esta clase maneja la creación y configuración de la ventana principal,
    así como la interacción con el resto de componentes del sistema.
    """
    
    def __init__(self, root, extractor_instance):
        """
        Inicializa la ventana principal
        
        Args:
            root (tk.Tk): Ventana raíz de Tkinter
            extractor_instance: Instancia de la clase IssuesExtractor
        """
        self.root = root
        self.extractor = extractor_instance
        self.image_cache = {}  # Para almacenar referencias a imágenes
        
        # Configuraciones de la ventana principal
        self.root.title("SAP Issues Extractor")
        self.root.geometry("950x700")
        self.root.minsize(800, 600)
        self.root.configure(bg=SAP_COLORS["light"])
        
        # Variables Tkinter
        self.status_var = tk.StringVar(value="Listo para iniciar")
        self.excel_filename_var = tk.StringVar(value="No seleccionado")
        
        # Asignar las variables al extractor para que pueda actualizarlas
        self.extractor.status_var = self.status_var
        self.extractor.excel_filename_var = self.excel_filename_var
        
        # Crear interfaz
        self.setup_ui()
        
        # Vincular eventos de cierre
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Configurar teclas de acceso rápido
        self.setup_shortcuts()
        
    def setup_ui(self):
        """Configura todos los elementos de la interfaz de usuario"""
        # Ajustar el tema según el sistema operativo
        self._adjust_theme_for_platform()
        
        # Crear componentes en métodos separados
        self._create_menu()
        self._create_main_frame()
        self._create_header_panel()
        self._create_content_frame()
        self._create_status_bar()
        
        # Configurar tab order
        self._setup_tab_order()
        
        # Centrar ventana
        self._center_window()
        
    def _adjust_theme_for_platform(self):
        """Ajusta el tema según el sistema operativo para mejor integración"""
        try:
            import platform
            system = platform.system()
            
            # Configurar tema dependiendo del sistema operativo
            if system == "Windows":
                # Usar colores nativos de Windows para algunos elementos
                self.root.configure(bg="#F0F0F0")
            elif system == "Darwin":  # macOS
                # Ajustes específicos para macOS
                self.root.configure(bg="#ECECEC")
            elif system == "Linux":
                # Ajustes específicos para Linux
                pass
                
            logger.debug(f"Tema ajustado para plataforma: {system}")
        except Exception as e:
            logger.warning(f"No se pudo ajustar el tema para la plataforma: {e}")
            
    def _create_menu(self):
        """Crea la barra de menú de la aplicación"""
        menu_bar = tk.Menu(self.root)
        
        # Menú Archivo
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Seleccionar/Crear Excel", command=self.extractor.choose_excel_file)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.on_closing)
        menu_bar.add_cascade(label="Archivo", menu=file_menu)
        
        # Menú Navegador
        browser_menu = tk.Menu(menu_bar, tearoff=0)
        browser_menu.add_command(label="Iniciar Navegador", command=self.extractor.start_browser)
        browser_menu.add_command(label="Extraer Issues", command=self.extractor.start_extraction)
        menu_bar.add_cascade(label="Navegador", menu=browser_menu)
        
        # Menú Herramientas
        tools_menu = tk.Menu(menu_bar, tearoff=0)
        tools_menu.add_command(label="Configuración", command=self.show_settings)
        menu_bar.add_cascade(label="Herramientas", menu=tools_menu)
        
        # Menú Ayuda
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="Acerca de", command=self.show_about)
        menu_bar.add_cascade(label="Ayuda", menu=help_menu)
        
        # Establecer el menú
        self.root.config(menu=menu_bar)
        
    def _create_main_frame(self):
        """Crea el marco principal de la aplicación"""
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
    def _create_header_panel(self):
        """Crea el panel de cabecera con logo y título"""
        try:
            # Frame de cabecera
            self.header_frame = ttk.Frame(self.main_frame)
            self.header_frame.pack(fill=tk.X, pady=(0, 15))
            
            # Intentar cargar logo si PIL está disponible
            logo_photo = None
            if PIL_AVAILABLE:
                try:
                    # Intentar cargar un logo de SAP o un ícono apropiado
                    logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "sap_logo.png")
                    if os.path.exists(logo_path):
                        logo_image = Image.open(logo_path)
                        logo_photo = ImageTk.PhotoImage(logo_image)
                        
                        # Añadir logo a la cabecera
                        logo_label = tk.Label(self.header_frame, image=logo_photo, bg=SAP_COLORS["light"])
                        logo_label.image = logo_photo  # Mantener referencia
                        logo_label.pack(side=tk.LEFT, padx=(0, 10))
                except Exception as e:
                    logger.debug(f"No se pudo cargar el logo: {e}")
            
            # Título con fondo de alto contraste
            title_background = "#0A3D6E"  # Azul oscuro
            title_foreground = "#FFFFFF"  # Texto blanco
            
            title_label = tk.Label(
                self.header_frame, 
                text="Extractor de Recomendaciones SAP",
                font=("Arial", 18, "bold"),
                foreground=title_foreground,
                background=title_background,
                padx=12,
                pady=8
            )
            title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        except Exception as e:
            logger.error(f"Error al crear panel de cabecera: {e}")
            
    def _create_content_frame(self):
        """Crea el marco principal de contenido dividido en paneles"""
        content_frame = ttk.Frame(self.main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Panel izquierdo para configuración
        self.left_panel = ttk.Frame(content_frame, padding=10, width=500)
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10), expand=True)
        
        # Crear secciones del panel izquierdo
        self._create_client_panel()
        self._create_project_panel()
        self._create_browser_panel()
        self._create_excel_panel()
        self._create_action_panel()
        
        # Panel derecho para logs
        right_panel = ttk.Frame(content_frame, padding=10, width=400)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Log frame
        self._create_log_panel(right_panel)
        
    def _create_client_panel(self):
        """Crea el panel de selección de cliente"""
        try:
            client_frame = tk.LabelFrame(
                self.left_panel, 
                text="Cliente", 
                bg=SAP_COLORS["light"],
                fg="#000000",
                font=("Arial", 11, "bold"),
                padx=10, pady=10
            )
            client_frame.pack(fill=tk.X, pady=(0, 10))
            
            # Grid para organizar los elementos
            client_frame.columnconfigure(1, weight=1)  # La segunda columna se expandirá
            
            # Etiqueta ERP
            tk.Label(
                client_frame, 
                text="ERP Number:",
                bg=SAP_COLORS["light"],
                fg="#000000",
                font=("Arial", 9)
            ).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
            
            # Entry ERP
            self.extractor.client_var = tk.StringVar(value="1025541")
            client_entry = tk.Entry(
                client_frame, 
                textvariable=self.extractor.client_var,
                width=15,
                font=("Arial", 10),
                bg="white",
                fg="black",
                highlightbackground=SAP_COLORS["primary"],
                highlightcolor=SAP_COLORS["primary"]
            )
            client_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
            
            # Etiqueta de clientes guardados
            tk.Label(
                client_frame, 
                text="Clientes guardados:",
                bg=SAP_COLORS["light"],
                fg="#000000",
                font=("Arial", 9)
            ).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
            
            # Lista desplegable de clientes guardados
            client_list = self.extractor.db_manager.get_clients()
            self.extractor.client_combo = ttk.Combobox(client_frame, values=client_list, width=30)
            self.extractor.client_combo.config(state='readonly')
            self.extractor.client_combo.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky=tk.W+tk.E)
            self.extractor.client_combo.bind("<<ComboboxSelected>>", lambda e: self.extractor.select_client(self.extractor.client_combo.get()))
        
        except Exception as e:
            logger.error(f"Error al crear panel de cliente: {e}")
            
    def _create_project_panel(self):
        """Crea el panel de selección de proyecto"""
        try:
            project_frame = tk.LabelFrame(
                self.left_panel, 
                text="Proyecto", 
                bg=SAP_COLORS["light"],
                fg="#000000",
                font=("Arial", 11, "bold"),
                padx=10, pady=10
            )
            project_frame.pack(fill=tk.X, pady=(0, 10))
            
            # Grid para organizar los elementos
            project_frame.columnconfigure(1, weight=1)  # La segunda columna se expandirá
            
            # Etiqueta ID
            tk.Label(
                project_frame, 
                text="ID Proyecto:",
                bg=SAP_COLORS["light"],
                fg="#000000",
                font=("Arial", 10)
            ).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
            
            # Entry Proyecto
            self.extractor.project_var = tk.StringVar(value="20096444")
            project_entry = tk.Entry(
                project_frame, 
                textvariable=self.extractor.project_var,
                width=15,
                font=("Arial", 10),
                bg="white",
                fg="black",
                highlightbackground=SAP_COLORS["primary"],
                highlightcolor=SAP_COLORS["primary"]
            )
            project_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
            
            # Etiqueta de proyectos
            tk.Label(
                project_frame, 
                text="Proyectos:",
                bg=SAP_COLORS["light"],
                fg="#000000",
                font=("Arial", 10)
            ).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
            
            # Lista desplegable de proyectos guardados
            project_list = self.extractor.db_manager.get_projects("1025541")
            self.extractor.project_combo = ttk.Combobox(project_frame, values=project_list, width=30)
            self.extractor.project_combo.config(state='readonly')
            self.extractor.project_combo.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky=tk.W+tk.E)
            self.extractor.project_combo.bind("<<ComboboxSelected>>", lambda e: self.extractor.select_project(self.extractor.project_combo.get()))
        
        except Exception as e:
            logger.error(f"Error al crear panel de proyecto: {e}")
            
    def _create_browser_panel(self):
        """Crea el panel de control del navegador"""
        try:
            browser_frame = tk.LabelFrame(
                self.left_panel, 
                text="Navegador", 
                bg=SAP_COLORS["light"],
                fg="#000000",
                font=("Arial", 11, "bold"),
                padx=10, pady=10
            )
            browser_frame.pack(fill=tk.X, pady=(0, 10))
            
            # Etiqueta de navegador
            browser_label = tk.Label(
                browser_frame, 
                text="Iniciar un navegador con perfil dedicado:",
                bg=SAP_COLORS["light"],
                fg="#000000",
                font=("Arial", 10),
                anchor="w",
                justify="left"
            )
            browser_label.pack(fill=tk.X, pady=(0, 5))
            
            # Botón de navegador
            browser_button = tk.Button(
                browser_frame, 
                text="Iniciar Navegador",
                command=self.extractor.start_browser,
                bg=SAP_COLORS["primary"],
                fg="#FFFFFF",
                activebackground="#0A3D6E",
                activeforeground="#FFFFFF",
                font=("Arial", 10, "bold"),
                padx=10, pady=5
            )
            browser_button.pack(fill=tk.X, pady=5)
            
            # Guardar referencia al botón para acceso desde otras funciones
            self.browser_button = browser_button
            
        except Exception as e:
            logger.error(f"Error al crear panel de navegador: {e}")
            
    def _create_excel_panel(self):
        """Crea el panel de selección y gestión de Excel"""
        try:
            excel_frame = tk.LabelFrame(
                self.left_panel, 
                text="Archivo Excel", 
                bg=SAP_COLORS["light"],
                fg="#000000",
                font=("Arial", 11, "bold"),
                padx=10, pady=10
            )
            excel_frame.pack(fill=tk.X, pady=(0, 10))
            
            # Etiqueta de Excel
            excel_label = tk.Label(
                excel_frame, 
                text="Seleccione un archivo existente o cree uno nuevo:",
                bg=SAP_COLORS["light"],
                fg="#000000",
                font=("Arial", 10),
                anchor="w",
                justify="left"
            )
            excel_label.pack(fill=tk.X, pady=(0, 5))
            
            # Botón de Excel
            excel_button = tk.Button(
                excel_frame, 
                text="Seleccionar o Crear Excel",
                command=self.extractor.choose_excel_file,
                bg=SAP_COLORS["success"],
                fg="#FFFFFF",
                activebackground="#085E2E",
                activeforeground="#FFFFFF",
                font=("Arial", 10, "bold"),
                padx=10, pady=5
            )
            excel_button.pack(fill=tk.X, pady=5)
            
            # Guardar referencia al botón para acceso desde otras funciones
            self.excel_button = excel_button
            
            # Mostrar el nombre del archivo seleccionado
            excel_file_label = tk.Label(
                excel_frame, 
                textvariable=self.excel_filename_var,
                bg=SAP_COLORS["light"],
                fg="#0A3D6E",
                font=("Arial", 9, "bold"),
                wraplength=300,
                anchor="w",
                justify="left"
            )
            excel_file_label.pack(fill=tk.X, pady=5)
            
        except Exception as e:
            logger.error(f"Error al crear panel de Excel: {e}")
            
    def _create_action_panel(self):
        """Crea el panel de acciones principales"""
        try:
            action_frame = tk.LabelFrame(
                self.left_panel, 
                text="Acciones", 
                bg=SAP_COLORS["light"],
                fg="#000000",
                font=("Arial", 11, "bold"),
                padx=10, pady=10
            )
            action_frame.pack(fill=tk.X, pady=(0, 10))
            
            # Etiqueta de acción
            action_label = tk.Label(
                action_frame, 
                text="Extraer datos de issues desde SAP:",
                bg=SAP_COLORS["light"],
                fg="#000000",
                font=("Arial", 10),
                anchor="w",
                justify="left"
            )
            action_label.pack(fill=tk.X, pady=(0, 5))
            
            # Botón de extracción
            extract_button = tk.Button(
                action_frame, 
                text="Iniciar Extracción de Issues",
                command=self.extractor.start_extraction,
                bg=SAP_COLORS["warning"],
                fg="#FFFFFF",
                activebackground="#C25A00",
                activeforeground="#FFFFFF",
                font=("Arial", 10, "bold"),
                padx=10, pady=5
            )
            extract_button.pack(fill=tk.X, pady=5)
            
            # Guardar referencia al botón para acceso desde otras funciones
            self.extract_button = extract_button
            
            # Separador visual
            separator = tk.Frame(action_frame, height=2, bg=SAP_COLORS["gray"])
            separator.pack(fill=tk.X, pady=10)
            
            # Botón de salir
            exit_button = tk.Button(
                action_frame, 
                text="Salir de la Aplicación",
                command=self.extractor.exit_app,
                bg=SAP_COLORS["danger"],
                fg="#FFFFFF",
                activebackground="#990000",
                activeforeground="#FFFFFF",
                font=("Arial", 10, "bold"),
                padx=10, pady=5
            )
            exit_button.pack(fill=tk.X, pady=5)
            
            # Guardar referencia al botón para acceso desde otras funciones
            self.exit_button = exit_button
            
        except Exception as e:
            logger.error(f"Error al crear panel de acciones: {e}")
            
    def _create_log_panel(self, parent_frame):
        """Crea el panel de registro de actividad (logs)"""
        try:
            log_frame = tk.LabelFrame(
                parent_frame, 
                text="Registro de Actividad", 
                bg=SAP_COLORS["light"],
                fg="#000000",
                font=("Arial", 11, "bold"))
            log_frame.pack(fill=tk.BOTH, expand=True)
            
            # Text widget para logs
            self.extractor.log_text = tk.Text(
                log_frame, 
                height=20, 
                wrap=tk.WORD, 
                bg="white",
                fg="black",
                font=("Consolas", 9),
                padx=5,
                pady=5,
                borderwidth=2,
                relief=tk.SUNKEN
            )
            self.extractor.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # Colores para los logs
            self.extractor.log_text.tag_configure("INFO", foreground="black")
            self.extractor.log_text.tag_configure("WARNING", foreground="#CC6600")
            self.extractor.log_text.tag_configure("ERROR", foreground="#990000")
            self.extractor.log_text.tag_configure("DEBUG", foreground="#555555")
            
            # Scrollbar para el log
            scrollbar = ttk.Scrollbar(log_frame, command=self.extractor.log_text.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.extractor.log_text.config(yscrollcommand=scrollbar.set)
            
            # Configurar logger para GUI
            setup_gui_logger(logger, self.extractor.log_text)
            
        except Exception as e:
            logger.error(f"Error al crear panel de logs: {e}")
            
    def _create_status_bar(self):
        """Crea la barra de estado en la parte inferior de la ventana"""
        try:
            status_bar = tk.Label(
                self.root, 
                textvariable=self.status_var,
                fg="#000000",
                bg="#F0F0F0",
                relief=tk.SUNKEN, 
                anchor=tk.W, 
                padx=5,
                pady=2,
                font=("Arial", 10)
            )
            status_bar.pack(side=tk.BOTTOM, fill=tk.X)
            
        except Exception as e:
            logger.error(f"Error al crear barra de estado: {e}")
            
    def _setup_tab_order(self):
        """Configura el orden de tabulación entre controles"""
        try:
            # Obtener todos los widgets que admiten foco
            widgets = [
                # Campos de entrada
                self.extractor.client_var,
                self.extractor.client_combo,
                self.extractor.project_var,
                self.extractor.project_combo,
                
                # Botones
                self.browser_button,
                self.excel_button,
                self.extract_button,
                self.exit_button
            ]
            
            # Configurar el orden de tabulación
            for widget in widgets:
                if hasattr(widget, 'lift'):
                    widget.lift()  # Asegurar que el widget está en la jerarquía correcta
                
        except Exception as e:
            logger.warning(f"No se pudo configurar el orden de tabulación: {e}")
            
    def _center_window(self):
        """Centra la ventana de la aplicación en la pantalla"""
        try:
            # Actualizar la información de geometría
            self.root.update_idletasks()
            
            # Obtener dimensiones de la pantalla
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # Obtener dimensiones de la ventana
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()
            
            # Calcular posición para centrar
            x = int((screen_width - window_width) / 2)
            y = int((screen_height - window_height) / 2)
            
            # Establecer geometría
            self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
            
        except Exception as e:
            logger.warning(f"No se pudo centrar la ventana: {e}")
            
    def setup_shortcuts(self):
        """Configura atajos de teclado para las funciones principales"""
        try:
            # Definir atajos de teclado
            self.root.bind("<Control-q>", lambda e: self.on_closing())
            self.root.bind("<Control-b>", lambda e: self.extractor.start_browser())
            self.root.bind("<Control-e>", lambda e: self.extractor.choose_excel_file())
            self.root.bind("<F5>", lambda e: self.extractor.start_extraction())
            
        except Exception as e:
            logger.warning(f"No se pudieron configurar los atajos de teclado: {e}")
            
    def on_closing(self):
        """Maneja el evento de cierre de la ventana"""
        try:
            self.extractor.exit_app()
        except Exception as e:
            logger.error(f"Error al cerrar la aplicación: {e}")
            # En caso de error, cerrar forzadamente
            self.root.destroy()
            
    def show_about(self):
        """Muestra el diálogo Acerca de"""
        try:
            about_dialog = AboutDialog(self.root)
            about_dialog.show()
        except Exception as e:
            logger.error(f"Error al mostrar diálogo Acerca de: {e}")
            messagebox.showinfo("Acerca de", "SAP Issues Extractor\nVersión 2.0\n\nUna herramienta para extraer issues de SAP")
            
    def show_settings(self):
        """Muestra el diálogo de Configuración"""
        try:
            settings_dialog = SettingsDialog(self.root, self.extractor)
            settings_dialog.show()
        except Exception as e:
            logger.error(f"Error al mostrar diálogo de Configuración: {e}")
            messagebox.showinfo("Configuración", "No se pudo abrir la ventana de configuración")
