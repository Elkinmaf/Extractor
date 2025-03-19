import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.font import Font
import threading
import logging
from datetime import datetime

# Importar PIL solo si está disponible
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

logger = logging.getLogger(__name__)



def adjust_combobox_dropdown_width(combobox):
    """
    Ajusta el ancho del dropdown del combobox al elemento más largo
    
    Esta función analiza todos los elementos en el combobox y ajusta
    el ancho del dropdown para mostrar el elemento más largo.
    
    Args:
        combobox: El widget ttk.Combobox a ajustar
    """
    """ values = combobox["values"]
    if not values:
        return
    
    # Calcular el ancho máximo basado en el elemento más largo
    max_width = max([len(str(item)) for item in values])
    
    # Añadir margen para mejor visualización
    width = max_width + 5
    
    # Limitar el ancho entre un mínimo y un máximo razonable
    width = min(60, max(25, width))
    """
    
    # Ajustar el ancho del combobox
    combobox.configure(width=37)
    
    # En tkinter, también podemos modificar la opción de estilo del combobox para
    # controlar el dropdown. Esto requiere acceso a la ventana principal.
    try:
        # Intentar obtener el estilo y modificarlo para que el dropdown sea más ancho
        style = ttk.Style()
        style.configure('TCombobox', postoffset=(0, 0, width*7, 0))
    except Exception as e:
        # Si hay algún error, simplemente lo ignoramos y usamos el ajuste básico
        logger.debug(f"No se pudo ajustar el estilo del dropdown: {e}")



class MainWindow:
    """Clase que maneja la interfaz de usuario principal para SAP Issues Extractor"""
    
    def __init__(self, root, controller):
        """
        Inicializa la ventana principal
        
        Args:
            root (tk.Tk): Ventana raíz de Tkinter
            controller (IssuesExtractor): Instancia del controlador principal
        """
        self.root = root
        self.controller = controller
        self.compact_mode = True  # Por defecto, usar modo compacto para pantallas pequeñas
        self.current_theme = "sap"  # Por defecto, usar tema SAP

        # Crear atributos para componentes principales
        self.header_frame = None
        self.left_panel = None
        self.right_panel = None
        self.footer_frame = None
        self.log_frame = None
        self.log_text = None
        self.client_combo = None
        self.project_combo = None
        
        # Variables para widgets y controles
        self.status_label = None
        self.progress_bar = None
        self.collapsed_sections = {"log": False}
        
        # Bindear variables del controlador
        self.controller.status_var = tk.StringVar(value="Listo para iniciar")
        self.controller.excel_filename_var = tk.StringVar(value="Archivo: No seleccionado")
        self.controller.client_var = tk.StringVar(value="")
        self.controller.project_var = tk.StringVar(value="")
    
    def setup_ui(self):
        """Configura toda la interfaz de usuario con un diseño adaptativo"""
        self._configure_root()
        self._setup_styles()
        self._create_main_layout()
        self._create_header()
        self._create_left_panel()
        self._create_right_panel()
        self._create_footer()
        self._create_context_menu()
        self._apply_sap_theme()
        
        # Actualizar variables del controlador
        self.controller.root = self.root
        self.controller.log_text = self.log_text
        self.controller.client_combo = self.client_combo
        self.controller.project_combo = self.project_combo
        
        # Conectar señales
        self._connect_signals()
        
        # Comprobar altura de pantalla para ajustar automáticamente
        self.root.update_idletasks()
        screen_height = self.root.winfo_screenheight()
        if screen_height < 600:  # Pantalla pequeña
            self.toggle_compact_mode(True)
            
    def _configure_root(self):
        """Configura la ventana principal"""
        # Título y tamaño
        self.root.title("SAP Issues Extractor")
        self.root.geometry("900x580")
        self.root.minsize(800, 500)
        
        # Ícono de la aplicación si está disponible
        icon_path = os.path.join("assets", "icon.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)
            
        # Configurar comportamiento al cerrar
        self.root.protocol("WM_DELETE_WINDOW", self.controller.exit_app)
        
        # Hacer que la ventana sea redimensionable
        self.root.resizable(True, True)
        
        # Configurar grid weights para hacer la ventana adaptativa
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=0)  # Header - tamaño fijo
        self.root.grid_rowconfigure(1, weight=1)  # Contenido - expandible
        self.root.grid_rowconfigure(2, weight=0)  # Footer - tamaño fijo
    
    def _setup_styles(self):
        """Configura los estilos para ttk widgets"""
        self.style = ttk.Style()
        
        # Definir fuentes - SAP usa Segoe UI
        self.default_font = Font(family="Segoe UI", size=9)
        self.header_font = Font(family="Segoe UI", size=12, weight="bold")
        self.small_font = Font(family="Segoe UI", size=8)
        self.button_font = Font(family="Segoe UI", size=9)
        
        # Colores SAP
        self.sap_blue = "#1F4E78"         # Azul SAP principal
        self.sap_light_blue = "#427CAC"   # Azul SAP claro
        self.sap_dark_blue = "#154063"    # Azul SAP oscuro
        self.sap_bg = "#F5F5F5"           # Fondo gris claro
        self.sap_section_bg = "#E6E6E6"   # Fondo de secciones
        self.sap_fg = "#333333"           # Texto oscuro
        self.sap_border = "#CCCCCC"       # Borde gris
        
        # Configurar estilo para frame con borde
        self.style.configure("Card.TFrame", borderwidth=1, relief="solid", background="#FFFFFF")
        
        # Botones principales - estilo SAP Fiori
        self.style.configure("Primary.TButton", 
                           font=self.button_font, 
                           background=self.sap_blue,
                           foreground="white")
        padding=(5,4)
                           
        self.style.map("Primary.TButton", 
            background=[('active', self.sap_light_blue), ('pressed', self.sap_dark_blue)],
            foreground=[('active', 'white'), ('pressed', 'white')])
            
        # Botones secundarios
        self.style.configure("Secondary.TButton", font=self.button_font)
        
        # Etiquetas de secciones
        self.style.configure("Section.TLabel", 
                           font=self.default_font, 
                           background=self.sap_section_bg, 
                           foreground=self.sap_fg,
                           padding=5)
        
        # Separadores
        self.style.configure("Horizontal.TSeparator", background=self.sap_border)
        
        # Progreso
        self.style.configure("TProgressbar", 
                          thickness=6, 
                          background=self.sap_blue)
        
        # Combobox
        self.style.configure("TCombobox", 
                          padding=2, 
                          font=self.default_font)
        
        # Scrollbars más delgados
        self.style.configure("TScrollbar", 
                          gripcount=0, 
                          background=self.sap_border,
                          troughcolor="#EEEEEE", 
                          arrowsize=12, 
                          arrowcolor="#666666",
                          width=10)
                          
    def _apply_sap_theme(self):
        """Aplica el tema de SAP a la interfaz"""
        # Colores del tema SAP
        bg_color = "#FFFFFF"
        fg_color = "#333333"
        section_bg = "#E6E6E6"
        card_border = "#CCCCCC"
        highlight_color = "#1F4E78"
        
        # Aplicar tema a los widgets principales
        self.style.configure("TFrame", background=bg_color)
        self.style.configure("Card.TFrame", background=bg_color, borderwidth=1, relief="solid")
        self.style.configure("TLabel", background=bg_color, foreground=fg_color)
        self.style.configure("Section.TLabel", background=section_bg, foreground=fg_color)
        self.style.configure("TButton", background=bg_color)
        self.style.configure("Primary.TButton", background=highlight_color, foreground="white")
        
        # Modificar colores del log
        self.log_text.configure(bg="#FCFCFC", fg=fg_color, insertbackground=fg_color)
        
        # Actualizar colores de tags de log
        self.log_text.tag_configure("INFO", foreground="#000000")
        self.log_text.tag_configure("DEBUG", foreground="#666666")
        self.log_text.tag_configure("WARNING", foreground="#FF8800")
        self.log_text.tag_configure("ERROR", foreground="#FF0000")





    def _create_main_layout(self):
            """Crea el layout principal de la aplicación con paneles separados"""
            # Frame principal para todo el contenido
            self.main_frame = ttk.Frame(self.root)
            self.main_frame.grid(row=0, column=0, sticky="nsew")
            self.root.grid_rowconfigure(0, weight=1)
            self.root.grid_columnconfigure(0, weight=1)
            
            # Configurar el layout del frame principal
            self.main_frame.grid_rowconfigure(0, weight=0)  # Header (altura fija)
            self.main_frame.grid_rowconfigure(1, weight=1)  # Contenido (expandible)
            self.main_frame.grid_rowconfigure(2, weight=0)  # Footer (altura fija)
            self.main_frame.grid_columnconfigure(0, weight=1)
            
            # Panel de cabecera
            self.header_frame = ttk.Frame(self.main_frame, style="Card.TFrame", padding=5)
            self.header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
            
            # Marco contenedor para paneles laterales (soporta redimensionamiento)
            self.content_frame = ttk.Frame(self.main_frame)
            self.content_frame.grid(row=1, column=0, sticky="nsew", padx=5)
            self.content_frame.grid_columnconfigure(0, weight=2)  # Panel izquierdo
            self.content_frame.grid_columnconfigure(1, weight=3)  # Panel derecho
            self.content_frame.grid_rowconfigure(0, weight=1)
            
            # Panel izquierdo (configuración y controles)
            self.left_panel = ttk.Frame(self.content_frame, style="Card.TFrame")
            self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 2), pady=0)
            
            # Panel derecho (log y resultados)
            self.right_panel = ttk.Frame(self.content_frame, style="Card.TFrame")
            self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(2, 0), pady=0)
            
            # Panel de pie de página
            self.footer_frame = ttk.Frame(self.main_frame, padding=5)
            self.footer_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
    
    def _create_header(self):
        """Crea la sección de cabecera con logo y título"""
        # Configuración de columnas para el header
        self.header_frame.grid_columnconfigure(0, weight=0)  # Logo (fijo)
        self.header_frame.grid_columnconfigure(1, weight=1)  # Título (expandible)
        self.header_frame.grid_columnconfigure(2, weight=0)  # Botones (fijo)
        
        # Logo si PIL está disponible
        if PIL_AVAILABLE:
            logo_path = os.path.join("assets", "logo.png")
            if os.path.exists(logo_path):
                try:
                    # Usar Image.LANCZOS si está disponible, sino usar Image.ANTIALIAS
                    resample_method = getattr(Image, 'LANCZOS', Image.ANTIALIAS)
                    
                    logo_img = Image.open(logo_path)
                    logo_img = logo_img.resize((32, 32), resample_method)
                    logo_tk = ImageTk.PhotoImage(logo_img)
                    
                    # Guardar referencia a la imagen para evitar que la recolecte el GC
                    if not hasattr(self.controller, 'image_cache'):
                        self.controller.image_cache = {}
                    self.controller.image_cache["logo"] = logo_tk
                    
                    logo_label = ttk.Label(self.header_frame, image=logo_tk)
                    logo_label.grid(row=0, column=0, padx=(0, 10))
                except Exception as e:
                    logger.debug(f"Error al cargar logo: {e}")
        
        # Título y subtítulo
        title_frame = ttk.Frame(self.header_frame)
        title_frame.grid(row=0, column=1, sticky="w")
        
        title_label = ttk.Label(title_frame, text="SAP Issues Extractor", font=self.header_font)
        title_label.grid(row=0, column=0, sticky="w")
        
        subtitle_label = ttk.Label(title_frame, text="Extracción automática de issues desde SAP Fiori")
        subtitle_label.grid(row=1, column=0, sticky="w")
        
        # Botones de cabecera
        buttons_frame = ttk.Frame(self.header_frame)
        buttons_frame.grid(row=0, column=2, sticky="e")
        
        # Botón de modo compacto
        self.compact_button = ttk.Button(buttons_frame, text="📏", width=3,
                                        command=lambda: self.toggle_compact_mode())
        self.compact_button.grid(row=0, column=0, padx=(0, 5))
        
        # Botón de tema
        self.theme_button = ttk.Button(buttons_frame, text="🎨", width=3,
                                       command=self.toggle_theme)
        self.theme_button.grid(row=0, column=1, padx=(0, 5))
        
        # Botón de ayuda
        help_button = ttk.Button(buttons_frame, text="❓", width=3,
                                command=self.show_help)
        help_button.grid(row=0, column=2)
        
        
        
        
        
        
    def _create_left_panel(self):
            """Crea el panel izquierdo con configuración y controles"""
            # Configurar el panel izquierdo para organización vertical
            self.left_panel.grid_columnconfigure(0, weight=1)
            
            # Sección de archivo Excel
            excel_section_frame = self._create_collapsible_section(
                self.left_panel, "Archivo Excel", 0, can_collapse=False)
            
            # Indicador de archivo Excel seleccionado
            excel_file_frame = ttk.Frame(excel_section_frame)
            excel_file_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
            excel_file_frame.grid_columnconfigure(0, weight=1)
            
            excel_file_label = ttk.Label(excel_file_frame, 
                                        textvariable=self.controller.excel_filename_var,
                                        wraplength=300, justify="left")
            excel_file_label.grid(row=1, column=0, sticky="w", columnspan=2)
            
            # Botón para seleccionar archivo Excel
            excel_file_button = tk.Button(excel_file_frame, text="Seleccionar",
                                          bg= "#1F4E78", fg="white",
                                          command=self.controller.choose_excel_file)
            excel_file_button.grid(row=0, column=1, padx=(5, 0))
            
            # Separador
            ttk.Separator(self.left_panel, orient="horizontal").grid(
                row=1, column=0, sticky="ew", pady=5)
            
            # Sección de Cliente y Proyecto
            client_section_frame = self._create_collapsible_section(
                self.left_panel, "Cliente y Proyecto", 2, can_collapse=False)
            
            # Frame para cliente
            client_frame = ttk.Frame(client_section_frame)
            client_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
            client_frame.grid_columnconfigure(1, weight=1)

            # Etiqueta y entrada para Cliente
            ttk.Label(client_frame, text="Cliente:").grid(row=0, column=0, sticky="w", padx=(0, 5))

            # Marco para contener el combo y el botón de añadir
            client_combo_frame = ttk.Frame(client_frame)
            client_combo_frame.grid(row=0, column=1, sticky="ew")
            client_combo_frame.grid_columnconfigure(0, weight=1)

            # Combo editable para selección de cliente
            self.client_combo = ttk.Combobox(client_combo_frame, 
                                        textvariable=self.controller.client_var,
                                        state="readonly", width=25)
            self.client_combo.grid(row=0, column=0, sticky="ew", pady=2)

            # Botón para añadir nuevo cliente
            add_client_btn = ttk.Button(client_combo_frame, text="+", width=2,
                                    command=self.controller.add_new_client)
            add_client_btn.grid(row=0, column=1, padx=(5, 0), pady=2)

            # Obtener y configurar lista de clientes
            clients = self.controller.db_manager.get_clients()
            self.client_combo['values'] = clients

            # Ajuste automático ancho
            adjust_combobox_dropdown_width(self.client_combo)
            
            # Seleccionar el primer cliente si hay alguno
            if clients:
                self.client_combo.current(0)
                self.controller.select_client(clients[0])
            
            
            # Frame para proyecto

            project_frame = ttk.Frame(client_section_frame)
            project_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
            project_frame.grid_columnconfigure(1, weight=1)

            # Etiqueta y entrada para Proyecto
            ttk.Label(project_frame, text="Proyecto:").grid(row=0, column=0, sticky="w", padx=(0, 5))

            # Marco para contener el combo y el botón de añadir
            project_combo_frame = ttk.Frame(project_frame)
            project_combo_frame.grid(row=0, column=1, sticky="ew")
            project_combo_frame.grid_columnconfigure(0, weight=1)

            # Combo editable para selección de proyecto
            self.project_combo = ttk.Combobox(project_combo_frame, 
                                        textvariable=self.controller.project_var,
                                        state="readonly", width=25)
            self.project_combo.grid(row=0, column=0, sticky="ew", pady=2)

            # Botón para añadir nuevo proyecto
            add_project_btn = ttk.Button(project_combo_frame, text="+", width=2,
                                    command=self.controller.add_new_project)
            add_project_btn.grid(row=0, column=1, padx=(5, 0), pady=2)
            
            # Separador
            ttk.Separator(self.left_panel, orient="horizontal").grid(
                row=3, column=0, sticky="ew", pady=5)
            
            # Sección de Acciones
            actions_section_frame = self._create_collapsible_section(
                self.left_panel, "Acciones", 4, can_collapse=False)
            
            # Frame para botones principales
            buttons_frame = ttk.Frame(actions_section_frame)
            buttons_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
            buttons_frame.grid_columnconfigure(0, weight=1)
            buttons_frame.grid_columnconfigure(1, weight=1)
            
            # Botón para iniciar navegador
            start_browser_btn = tk.Button(buttons_frame, text="Iniciar Navegador", 
                                        bg ="#1F4E78", fg="White", 
                                        font=("Segoe UI", 9, "bold"),
                                        width=18, height=2,
                                        command=self.controller.start_browser)
            start_browser_btn.grid(row=0, column=0, sticky="ew", padx=(0, 5), pady=8)
            
            # Botón para iniciar extracción
            extract_btn = tk.Button(buttons_frame, text="Iniciar Extracción", 
                                    bg ="#1F4E78", fg="White", 
                                    font=("Segoe UI", 9, "bold"),
                                    width=18, height=2,
                                command=self.controller.start_extraction)
            extract_btn.grid(row=0, column=1, sticky="ew", padx=(5, 0), pady=8)
            
            # Botón para abrir Excel
            open_excel_btn = ttk.Button(buttons_frame, text="Abrir Excel", width=15,
                                    command=lambda: self.controller.excel_manager.open_excel_file())
            open_excel_btn.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 5))
            
            # Botón para salir
            exit_btn = ttk.Button(buttons_frame, text="Salir", width=15,
                                command=self.controller.exit_app)
            exit_btn.grid(row=2, column=0, columnspan=2, sticky="ew")
            
            # Añadir espacio para empujar elementos hacia arriba
            spacer = ttk.Frame(self.left_panel)
            spacer.grid(row=5, column=0, sticky="ew", pady=10)
            self.left_panel.grid_rowconfigure(5, weight=1)
        
        
        
        
        
        
        
        
        
        
    def _create_right_panel(self):
            """Crea el panel derecho con el registro de actividad y resultados"""
            # Configurar panel para organización vertical
            self.right_panel.grid_rowconfigure(1, weight=1)  # Log expandible
            self.right_panel.grid_columnconfigure(0, weight=1)
            
            # Sección de Estado
            status_section_frame = self._create_collapsible_section(
                self.right_panel, "Estado", 0, can_collapse=False)
            
            # Etiqueta de estado
            status_frame = ttk.Frame(status_section_frame)
            status_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
            status_frame.grid_columnconfigure(0, weight=1)
            
            self.status_label = ttk.Label(status_frame, textvariable=self.controller.status_var,
                                        wraplength=400, justify="left")
            self.status_label.grid(row=0, column=0, sticky="w")
            
            # Barra de progreso
            self.progress_bar = ttk.Progressbar(status_frame, mode="indeterminate", length=100)
            self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(5, 0))
            
            # Sección de log con barra de desplazamiento
            log_section_frame = self._create_collapsible_section(
                self.right_panel, "Registro de Actividad", 1, 
                can_collapse=True, collapsed_key="log")
            
            # Frame para el log con scrollbar
            log_container = ttk.Frame(log_section_frame)
            log_container.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
            log_container.grid_rowconfigure(0, weight=1)
            log_container.grid_columnconfigure(0, weight=1)
            
            # Asegurarse de que la sección de log pueda expandirse
            log_section_frame.grid_rowconfigure(0, weight=1)
            log_section_frame.grid_columnconfigure(0, weight=1)
            
            # Text widget para mostrar log con scrollbar
            self.log_text = tk.Text(log_container, wrap="word", height=10, 
                                font=("Consolas", 9), bg="#F8F8F8", relief="flat")
            self.log_text.grid(row=0, column=0, sticky="nsew")
            
            # Scrollbar vertical
            log_scrollbar = ttk.Scrollbar(log_container, orient="vertical", 
                                        command=self.log_text.yview)
            log_scrollbar.grid(row=0, column=1, sticky="ns")
            self.log_text.config(yscrollcommand=log_scrollbar.set)
            
            # Configurar tags para colores de log
            self.log_text.tag_configure("INFO", foreground="#000000")
            self.log_text.tag_configure("DEBUG", foreground="#666666")
            self.log_text.tag_configure("WARNING", foreground="#FF8800")
            self.log_text.tag_configure("ERROR", foreground="#FF0000")
            self.log_text.tag_configure("CRITICAL", foreground="#FF0000", background="#FFCCCC")
    
    def _create_footer(self):
        """Crea la sección de pie de página con información de estado"""
        # Configurar el footer
        self.footer_frame.grid_columnconfigure(0, weight=1)
        
        # Información de estado y versión
        footer_label = ttk.Label(self.footer_frame, 
                              text="SAP Issues Extractor v1.0.0 - © 2025",
                              font=self.small_font)
        footer_label.grid(row=0, column=0, sticky="w")
        
        # Botón de limpieza de log en el lado derecho
        clear_log_btn = ttk.Button(self.footer_frame, text="Limpiar Log", width=12,
                                command=self._clear_log)
        clear_log_btn.grid(row=0, column=1, sticky="e")
        
    def _create_collapsible_section(self, parent, title, row, can_collapse=True, collapsed_key=None):
        """
        Crea una sección plegable/desplegable
        
        Args:
            parent: Widget padre
            title: Título de la sección
            row: Fila para colocar la sección
            can_collapse: Si la sección puede plegarse/desplegarse
            collapsed_key: Clave para almacenar estado de colapso
            
        Returns:
            Frame: El frame del contenido de la sección
        """
        # Frame para la cabecera de la sección
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=row, column=0, sticky="ew", padx=2, pady=(5, 0))
        header_frame.grid_columnconfigure(0, weight=1)
        
        # Estilo de cabecera
        section_label = ttk.Label(header_frame, text=title, style="Section.TLabel")
        section_label.grid(row=0, column=0, sticky="ew")
        
        # Botón de colapso si es plegable
        if can_collapse and collapsed_key:
            collapse_text = "▼" if not self.collapsed_sections.get(collapsed_key, False) else "►"
            collapse_btn = ttk.Button(header_frame, text=collapse_text, width=2,
                                    command=lambda: self._toggle_section(collapsed_key))
            collapse_btn.grid(row=0, column=1, sticky="e")
            
            # Guardar referencia al botón para actualizarlo después
            setattr(self, f"{collapsed_key}_collapse_btn", collapse_btn)
        
        # Frame para el contenido
        content_frame = ttk.Frame(parent)
        
        # Si la sección está colapsada, no mostrar el contenido
        if not can_collapse or not self.collapsed_sections.get(collapsed_key, False):
            content_frame.grid(row=row+1, column=0, sticky="nsew", padx=2, pady=(0, 5))
            
        # Guardar referencia al frame para mostrarlo/ocultarlo después
        if collapsed_key:
            setattr(self, f"{collapsed_key}_section_frame", content_frame)
            
        return content_frame
        
    def _toggle_section(self, section_key):
        """
        Alterna el estado plegado/desplegado de una sección
        
        Args:
            section_key: Clave de la sección a alternar
        """
        # Invertir estado
        self.collapsed_sections[section_key] = not self.collapsed_sections.get(section_key, False)
        collapsed = self.collapsed_sections[section_key]
        
        # Obtener referencias a los widgets
        section_frame = getattr(self, f"{section_key}_section_frame", None)
        collapse_btn = getattr(self, f"{section_key}_collapse_btn", None)
        
        if section_frame and collapse_btn:
            if collapsed:
                # Ocultar sección
                section_frame.grid_remove()
                collapse_btn.configure(text="►")
            else:
                # Mostrar sección
                section_frame.grid()
                collapse_btn.configure(text="▼")
                
                
                
                
                
                
                
                
    def _create_context_menu(self):
            """Crea el menú contextual para el log"""
            self.context_menu = tk.Menu(self.root, tearoff=0)
            self.context_menu.add_command(label="Copiar", command=self._copy_log)
            self.context_menu.add_command(label="Guardar Log", command=self._save_log)
            self.context_menu.add_separator()
            self.context_menu.add_command(label="Limpiar", command=self._clear_log)
            
            # Bindear el botón derecho al log
            self.log_text.bind("<Button-3>", self._show_context_menu)
        
    def _show_context_menu(self, event):
        """Muestra el menú contextual en la posición del ratón"""
        self.context_menu.post(event.x_root, event.y_root)
        
    def _copy_log(self):
        """Copia el contenido seleccionado del log al portapapeles"""
        try:
            # Si hay texto seleccionado, copiar solo eso
            selected_text = self.log_text.get("sel.first", "sel.last")
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
        except tk.TclError:
            # Si no hay selección, copiar todo
            all_text = self.log_text.get("1.0", "end-1c")
            self.root.clipboard_clear()
            self.root.clipboard_append(all_text)
            
    def _save_log(self):
        """Guarda el contenido del log a un archivo"""
        try:
            # Obtener nombre de archivo para guardar
            file_path = filedialog.asksaveasfilename(
                defaultextension=".log",
                filetypes=[("Archivos de log", "*.log"), ("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")],
                title="Guardar archivo de log"
            )
            
            if file_path:
                # Obtener todo el texto y guardar
                log_content = self.log_text.get("1.0", "end-1c")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(log_content)
                messagebox.showinfo("Guardar Log", f"Log guardado correctamente en:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar log: {e}")
            
    def _clear_log(self):
        """Limpia el contenido del log"""
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
    
    def _connect_signals(self):
        """Conecta señales y eventos de los widgets"""
        # Conectar cambio de cliente
        self.client_combo.bind("<<ComboboxSelected>>", 
                            lambda e: self.controller.select_client(self.client_combo.get()))
        
        # Conectar cambio de proyecto
        self.project_combo.bind("<<ComboboxSelected>>", 
                             lambda e: self.controller.select_project(self.project_combo.get()))
        
        # Verificar periódicamente el estado de procesamiento
        self._check_processing_state()
        
        # Detectar tamaño de ventana
        self.root.bind("<Configure>", self._on_window_resize)
        
    def _check_processing_state(self):
        """
        Actualiza la interfaz basada en el estado de procesamiento,
        como la barra de progreso y botones
        """
        if hasattr(self.controller, 'processing') and self.controller.processing:
            # Si está procesando, mostrar y activar la barra de progreso
            self.progress_bar.grid()
            self.progress_bar.start(10)
        else:
            # Si no está procesando, detener y ocultar la barra
            self.progress_bar.stop()
            self.progress_bar.grid_remove()
            
        # Programar la siguiente verificación
        self.root.after(100, self._check_processing_state)
        
    def _on_window_resize(self, event):
        """Maneja el evento de redimensionamiento de la ventana"""
        # Solo procesar eventos de la ventana principal, no de sub-widgets
        if event.widget == self.root:
            # Si la altura es menor a 600px, cambiar a modo compacto
            if event.height < 600 and not self.compact_mode:
                self.toggle_compact_mode(True)
            # Si la altura es mayor a 700px, cambiar a modo normal
            elif event.height > 700 and self.compact_mode:
                self.toggle_compact_mode(False)
                
    def toggle_compact_mode(self, force_state=None):
        """
        Alterna entre modo compacto y normal para adaptarse a pantallas pequeñas
        
        Args:
            force_state: Si se proporciona, fuerza el modo específico (True=compacto, False=normal)
        """
        # Determinar nuevo estado
        if force_state is not None:
            self.compact_mode = force_state
        else:
            self.compact_mode = not self.compact_mode
            
        if self.compact_mode:
            # Modo compacto: ocultar elementos no esenciales y reducir espacios
            self.compact_button.configure(text="📐")  # Cambiar icono a expandir
            
            # Ajustar fuentes y padding
            self.default_font.configure(size=8)
            self.header_font.configure(size=10)
            self.small_font.configure(size=7)
            self.button_font.configure(size=8)
            
            # Colapsar secciones no esenciales
            if not self.collapsed_sections.get("log", False):
                self._toggle_section("log")
                
            # Reducir altura del log
            self.log_text.configure(height=6)
            
            # Ajustar paddings
            for widget in [self.header_frame, self.left_panel, self.right_panel, self.footer_frame]:
                if hasattr(widget, 'configure'):
                    widget.configure(padding=2)
        else:
            # Modo normal: mostrar todos los elementos y restaurar espacios
            self.compact_button.configure(text="📏")  # Cambiar icono a compactar
            
            # Restaurar fuentes y padding
            self.default_font.configure(size=9)
            self.header_font.configure(size=12)
            self.small_font.configure(size=8)
            self.button_font.configure(size=9)
            
            # Expandir secciones colapsadas
            if self.collapsed_sections.get("log", False):
                self._toggle_section("log")
                
            # Restaurar altura del log
            self.log_text.configure(height=10)
            
            # Restaurar paddings
            self.header_frame.configure(padding=5)
            self.footer_frame.configure(padding=5)
        
        # Actualizar estilos
        self._setup_styles()
        
    def toggle_theme(self):
        """Alterna entre temas disponibles"""
        themes = ["sap", "light", "dark"]
        current_index = themes.index(self.current_theme) if self.current_theme in themes else 0
        next_index = (current_index + 1) % len(themes)
        self.current_theme = themes[next_index]
        
        if self.current_theme == "sap":
            self._apply_sap_theme()
            self.theme_button.configure(text="🔵")  # Icono para tema SAP
        elif self.current_theme == "light":
            self._apply_light_theme()
            self.theme_button.configure(text="☀️")  # Icono para tema claro
        else:
            self._apply_dark_theme()
            self.theme_button.configure(text="🌙")  # Icono para tema oscuro
    
    def _apply_light_theme(self):
        """Aplica el tema claro a la interfaz"""
        # Colores del tema claro
        bg_color = "#FFFFFF"
        fg_color = "#000000"
        section_bg = "#F0F0F0"
        card_border = "#DDDDDD"
        highlight_color = "#3498DB"  # Azul más genérico
        
        # Aplicar tema a los widgets principales
        self.style.configure("TFrame", background=bg_color)
        self.style.configure("Card.TFrame", background=bg_color, borderwidth=1, relief="solid")
        self.style.configure("TLabel", background=bg_color, foreground=fg_color)
        self.style.configure("Section.TLabel", background=section_bg, foreground=fg_color)
        self.style.configure("TButton", background=bg_color)
        self.style.configure("Primary.TButton", background=highlight_color, foreground="white")
        
        # Modificar colores del log
        self.log_text.configure(bg="#FCFCFC", fg=fg_color, insertbackground=fg_color)
        
        # Actualizar colores de tags de log
        self.log_text.tag_configure("INFO", foreground="#000000")
        self.log_text.tag_configure("DEBUG", foreground="#666666")
        self.log_text.tag_configure("WARNING", foreground="#FF8800")
        self.log_text.tag_configure("ERROR", foreground="#FF0000")
        
    def _apply_dark_theme(self):
        """Aplica el tema oscuro a la interfaz"""
        # Colores del tema oscuro
        bg_color = "#222222"
        fg_color = "#EEEEEE"
        section_bg = "#333333"
        card_border = "#444444"
        highlight_color = "#3A7CB8"
        
        # Aplicar tema a los widgets principales
        self.style.configure("TFrame", background=bg_color)
        self.style.configure("Card.TFrame", background=bg_color, borderwidth=1, relief="solid")
        self.style.configure("TLabel", background=bg_color, foreground=fg_color)
        self.style.configure("Section.TLabel", background=section_bg, foreground=fg_color)
        self.style.configure("TButton", background=bg_color)
        self.style.configure("Primary.TButton", background=highlight_color, foreground="white")
        
        # Modificar colores del log
        self.log_text.configure(bg="#333333", fg=fg_color, insertbackground=fg_color)
        
        # Actualizar colores de tags de log
        self.log_text.tag_configure("INFO", foreground="#CCCCCC")
        self.log_text.tag_configure("DEBUG", foreground="#999999")
        self.log_text.tag_configure("WARNING", foreground="#FFBB33")
        self.log_text.tag_configure("ERROR", foreground="#FF6666")
        
    def show_help(self):
        """Muestra ventana de ayuda con instrucciones básicas"""
        help_text = """
SAP Issues Extractor - Ayuda Rápida

1. Seleccione un archivo Excel para guardar los datos
2. Elija un cliente y proyecto de la lista desplegable
3. Haga clic en "Iniciar Navegador" para abrir Chrome
4. Una vez cargado SAP, haga clic en "Iniciar Extracción"
5. Siga las indicaciones que aparezcan durante el proceso
6. Al finalizar, los datos se guardarán en el archivo Excel

Para ver los datos extraídos, haga clic en "Abrir Excel".

Para adaptar la interfaz a pantallas pequeñas:
- Use el botón 📏 para cambiar al modo compacto
- Colapse secciones con el botón ▼

Para más información, consulte la documentación completa.
        """
        
        messagebox.showinfo("Ayuda - SAP Issues Extractor", help_text.strip())