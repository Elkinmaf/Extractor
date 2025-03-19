#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
custom_dialogs.py - Diálogos personalizados para SAP Issues Extractor
---
Este módulo proporciona diálogos y mensajes personalizados con mejor
alineación de texto y formato para la aplicación SAP Issues Extractor.
"""

import tkinter as tk
from tkinter import ttk
import os
import logging

logger = logging.getLogger(__name__)

class FormattedDialog(tk.Toplevel):
    """
    Diálogo personalizado con mejor formato de texto y alineación.
    
    Esta clase implementa un diálogo modal con soporte para:
    - Texto con formato y alineación correcta
    - Íconos personalizados
    - Botones personalizables
    """
    
    def __init__(self, parent, title, message, icon_type="info", width=450, height=250):
        """
        Inicializa un diálogo personalizado con formato mejorado
        
        Args:
            parent: Ventana padre
            title (str): Título del diálogo
            message (str): Mensaje a mostrar (puede contener listas con prefijo numérico)
            icon_type (str): Tipo de ícono ('info', 'warning', 'error', 'question')
            width (int): Ancho de la ventana
            height (int): Alto de la ventana
        """
        super().__init__(parent)
        
        # Configuración básica del diálogo
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)
        self.transient(parent)  # Mantener diálogo sobre la ventana principal
        self.grab_set()         # Hacer modal (bloquea interacción con ventana principal)
        
        # Configurar estilos
        bg_color = "#F5F5F5"  # Fondo gris muy claro
        self.configure(background=bg_color)
        
        # Bordes y decoración de la ventana
        if os.name == 'nt':  # Windows
            self.overrideredirect(False)  # Mantener decoración estándar de Windows
        else:
            self.overrideredirect(False)  # Usar decoración estándar en otros sistemas
            
        self.style = ttk.Style(self)
        self.style.configure("Dialog.TFrame", background=bg_color)
        self.style.configure("Dialog.TLabel", background=bg_color, font=("Segoe UI", 10))
        self.style.configure("DialogTitle.TLabel", background=bg_color, font=("Segoe UI", 11, "bold"))
        
        # Configurar grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(1, weight=1)
        
        # Frame principal
        main_frame = ttk.Frame(self, style="Dialog.TFrame", padding=10)
        main_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")
        main_frame.grid_columnconfigure(1, weight=1)
        
        # Crear y configurar icono
        self.icon_canvas = self._create_icon(main_frame, icon_type)
        if self.icon_canvas:
            self.icon_canvas.grid(row=0, column=0, padx=(5, 15), pady=10, sticky="n")
        
        # Procesar el mensaje para identificar listas y formatear alineación
        self.formatted_message = self._format_message(message)
        
        # Frame para contener el mensaje (permite mejor control del texto)
        text_frame = ttk.Frame(main_frame, style="Dialog.TFrame")
        text_frame.grid(row=0, column=1, sticky="nsew")
        text_frame.grid_columnconfigure(0, weight=1)
        text_frame.grid_rowconfigure(0, weight=1)  # Permitir que el texto se expanda verticalmente
        
        # Widget de texto para mostrar el mensaje con alineación correcta
        self.text_widget = tk.Text(text_frame, wrap="word", width=40, height=10,
                              font=("Segoe UI", 10), borderwidth=0, highlightthickness=0,
                              background="#F5F5F5", padx=5, pady=5, relief="flat")
        self.text_widget.grid(row=0, column=0, sticky="nsew")
        
        # Insertar texto formateado
        self.text_widget.insert("1.0", self.formatted_message)
        self.text_widget.configure(state="disabled")  # Impedir edición
        
        # Asegurar que se vea todo el contenido
        self.text_widget.see("end")
        
        # Botón OK con estilo SAP
        button_frame = ttk.Frame(self, style="Dialog.TFrame")
        button_frame.grid(row=1, column=0, columnspan=2, sticky="se", padx=15, pady=15)
        
        # Usar un botón con estilo SAP (azul)
        ok_button = tk.Button(
            button_frame, 
            text="OK", 
            width=10, 
            bg="#1F4E78",  # Azul SAP
            fg="white",    # Texto blanco
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            command=self.destroy
        )
        ok_button.grid(row=0, column=0, padx=5)
        
        # Efectos al pasar el mouse
        def on_enter(e):
            ok_button['background'] = "#3A7CA8"  # Azul más claro al pasar el mouse
            
        def on_leave(e):
            ok_button['background'] = "#1F4E78"  # Volver al azul original
            
        ok_button.bind("<Enter>", on_enter)
        ok_button.bind("<Leave>", on_leave)
        
        # Centrar ventana en la pantalla
        self._center_window()
        
        # Configurar comportamiento al cerrar
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        
        # Dar foco al botón OK
        ok_button.focus_set()
        
    def _create_icon(self, parent, icon_type):
        """
        Crea un ícono personalizado para el diálogo utilizando un canvas
        
        Args:
            parent: Widget padre donde se creará el ícono
            icon_type (str): Tipo de ícono ('info', 'warning', 'error', 'question')
            
        Returns:
            Canvas: Canvas con el ícono dibujado
        """
        try:
            # Mapeo de emojis según el tipo de diálogo
            emoji_map = {
                "info": "i",
                "warning": "!",
                "error": "×",
                "question": "?"
            }
            
            # Crear un canvas para dibujar el ícono
            icon_size = 32
            canvas = tk.Canvas(parent, width=icon_size, height=icon_size, 
                             bg="#F5F5F5", bd=0, highlightthickness=0)
            
            # Color de fondo según el tipo
            color_map = {
                "info": "#3498DB",     # Azul
                "warning": "#F39C12",  # Naranja
                "error": "#E74C3C",    # Rojo
                "question": "#2ECC71"  # Verde
            }
            
            # Dibujar un círculo con el color adecuado
            color = color_map.get(icon_type, "#3498DB")
            canvas.create_oval(2, 2, icon_size-2, icon_size-2, 
                             fill=color, outline=color)
            
            # Agregar el texto del ícono
            canvas.create_text(icon_size/2, icon_size/2, 
                             text=emoji_map.get(icon_type, "i"),
                             fill="white", font=("Segoe UI", 16, "bold"))
            
            return canvas
                
        except Exception as e:
            logger.debug(f"Error al crear ícono para diálogo: {e}")
            return None

    def _format_message(self, message):
        """
        Formatea el mensaje para mejorar la alineación del texto,
        especialmente para listas numeradas
        
        Args:
            message (str): Mensaje original
            
        Returns:
            str: Mensaje formateado con indentaciones correctas
        """
        lines = message.split('\n')
        formatted_lines = []
        in_list = False
        list_indent = 0
        current_list_item = 0
        
        for line in lines:
            # Línea vacía
            if not line.strip():
                formatted_lines.append("")
                continue
                
            # Detectar el inicio de una lista numerada (1. Texto)
            if line.strip() and line.strip()[0].isdigit() and '. ' in line:
                number_part = line.strip().split('.')[0]
                if number_part.isdigit():
                    item_number = int(number_part)
                    
                    # Verificar si es un nuevo elemento o una continuación
                    if in_list and item_number == current_list_item + 1:
                        # Continuación de la lista
                        current_list_item = item_number
                    else:
                        # Nueva lista o salto en numeración
                        in_list = True
                        current_list_item = item_number
                    
                    # Encontrar la posición del punto para alinear elementos siguientes
                    list_indent = line.find('. ') + 2
                    formatted_lines.append(line)
            elif in_list and line.strip() and not (line.strip()[0].isdigit() and '. ' in line.strip()):
                # Continuar un elemento de lista - aplicar indentación
                # Solo aplicar indentación si no comienza con un número seguido de punto
                formatted_lines.append(' ' * list_indent + line.strip())
            else:
                # Línea normal o nuevo elemento de lista no consecutivo
                if line.strip() and line.strip()[0].isdigit() and '. ' in line.strip():
                    # Es un elemento de lista, pero no consecutivo
                    in_list = True
                    number_part = line.strip().split('.')[0]
                    if number_part.isdigit():
                        current_list_item = int(number_part)
                    list_indent = line.find('. ') + 2
                else:
                    # No es un elemento de lista
                    in_list = False
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    def _center_window(self):
        """Centra el diálogo en la pantalla"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        
        # Obtener dimensiones de la pantalla
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Calcular posición
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        # Posicionar ventana
        self.geometry(f"{width}x{height}+{x}+{y}")

def show_formatted_message(parent, title, message, icon_type="info", width=450, height=250):
    """
    Muestra un mensaje formateado en un diálogo personalizado
    
    Args:
        parent: Ventana padre
        title (str): Título del diálogo
        message (str): Mensaje a mostrar
        icon_type (str): Tipo de ícono ('info', 'warning', 'error', 'question')
        width (int): Ancho de la ventana
        height (int): Alto de la ventana
        
    Returns:
        FormattedDialog: Instancia del diálogo creado
    """
    dialog = FormattedDialog(parent, title, message, icon_type, width, height)
    
    # Esperar a que se cierre el diálogo
    parent.wait_window(dialog)
    
    return dialog

# Funciones de utilidad para mensajes comunes

def show_info(parent, title, message):
    """Muestra un mensaje informativo formateado"""
    return show_formatted_message(parent, title, message, "info")

def show_warning(parent, title, message):
    """Muestra un mensaje de advertencia formateado"""
    return show_formatted_message(parent, title, message, "warning")

def show_error(parent, title, message):
    """Muestra un mensaje de error formateado"""
    return show_formatted_message(parent, title, message, "error", height=200)

def show_question(parent, title, message):
    """Muestra un mensaje de pregunta formateado"""
    return show_formatted_message(parent, title, message, "question")

def show_extraction_instructions(parent, client_info, project_info):
    """
    Muestra instrucciones formateadas para la extracción
    
    Args:
        parent: Ventana padre
        client_info (str): Información del cliente
        project_info (str): Información del proyecto
        
    Returns:
        FormattedDialog: Instancia del diálogo creado
    """
    # Asegurarnos de que el mensaje incluya todos los puntos y esté bien formateado
    # Usar un mensaje más compacto para garantizar que todo sea visible
    message = f"""La aplicación ha navegado automáticamente a la página de SAP con:

Cliente: {client_info}
Proyecto: {project_info}

Por favor:
1. Verifica que has iniciado sesión correctamente
2. Comprueba que puedes ver las recomendaciones para el cliente
3. Cuando quieras comenzar, haz clic en 'Iniciar Extracción'"""
    
    # Crear un diálogo más alto para asegurar que todo el contenido sea visible
    dialog = FormattedDialog(parent, "Instrucciones de Extracción", message, "info", width=450, height=340)
    
    # Asegurarse de que el widget de texto tenga suficiente altura
    dialog.text_widget.configure(height=12)
    
    # Esperar a que se cierre el diálogo
    parent.wait_window(dialog)
    
    return dialog