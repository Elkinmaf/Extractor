# Estructura Modular para SAP Issues Extractor
sap_issues_extractor/
│
├── main.py                       # Punto de entrada principal
├── config/                       # Directorio para archivos de configuración
│   ├── __init__.py
│   └── settings.py               # Configuración global (colores, directorios, etc.)
│
├── utils/                        # Utilidades comunes
│   ├── __init__.py
│   └── logger_config.py          # Configuración del logger
│
├── data/                         # Manejo de datos
│   ├── __init__.py
│   ├── database_manager.py       # Gestión de la base de datos SQLite
│   └── excel_manager.py          # Gestión de archivos Excel
│
├── browser/                      # Automatización del navegador
│   ├── __init__.py
│   ├── sap_browser.py            # Implementación del navegador para SAP
│   └── element_finder.py         # Funciones auxiliares para encontrar elementos web
        element_finder_sap.py     # (Adicional) Funciones específicas para SAP UI5
        
│
├── ui/                           # Interfaz de usuario
│   ├── __init__.py
│   ├── main_window.py            # Ventana principal de la interfaz
│   └── dialogs.py                # Diálogos y ventanas adicionales
│
└── extractor/                    # Lógica de extracción
    ├── __init__.py
    └── issues_extractor.py       # Coordinación del proceso de extracción
