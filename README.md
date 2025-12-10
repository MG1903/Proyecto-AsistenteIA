# Asistente Virtual "A la Hora" - Prototipo RAG

## 1. Manual de Instalación

### 1.1. Introducción
Este proyecto es un **prototipo de Asistente Virtual Inteligente** desarrollado para la relojería "Bendita la Hora". Su propósito es automatizar la respuesta a consultas frecuentes (inventario, precios) mediante la integración de un Modelo de Lenguaje Grande (LLM) con una base de conocimiento propietaria.

La solución emplea la arquitectura **RAG (Retrieval-Augmented Generation)**, asegurando que las respuestas sean precisas y estén contextualizadas con los datos de la empresa, evitando las "alucinaciones" comunes de los LLMs puros.

### 1.2. Requisitos del Sistema
Para la ejecución en entorno de desarrollo local:

| Categoría | Requisito Mínimo | Justificación |
| :--- | :--- | :--- |
| **Sistema Operativo** | Windows 10 / macOS / Linux | Soporte nativo de Python y dependencias. |
| **CPU** | 2.0 GHz Dual-Core | Necesario para ejecutar los procesos de vectorización (`sentence-transformers`). |
| **RAM** | 4 GB | Mínimo para el entorno Python, Django y la carga de embeddings. |
| **Software** | Python 3.12 | Lenguaje base del proyecto. |
| **Gestor Paquetes** | pip | Necesario para instalar las dependencias de `requirements.txt`. |
| **Servicios Externos**| Clave DeepSeek API | Requerida para la generación de respuestas por el LLM. |

### 1.3. Stack Tecnológico

| Componente | Herramienta | Función Principal |
| :--- | :--- | :--- |
| **Backend / Framework**| Django 5.x | Estructura MVT, gestión de modelos y panel administrativo. |
| **Servidor ASGI** | Daphne | Servidor asíncrono optimizado para gestionar WebSockets (Django Channels). |
| **Base Vectorial** | ChromaDB | Almacenamiento y búsqueda de los embeddings de la Base de Conocimiento. |
| **Embeddings** | Sentence-Transformers | Generación de vectores semánticos (modelo `all-MiniLM-L6-v2`). |
| **Orquestador** | LangChain | Cadena de procesamiento RAG. |
| **LLM** | DeepSeek API | Modelo de lenguaje para generar las respuestas finales. |
| **BD Estructurada**| SQLite | Persistencia de Logs, Consultas, Métricas y Documentos. |

---

## 2. Proceso de Instalación y Configuración

Siga los pasos a continuación para inicializar el prototipo en su ambiente local.

### 2.1. Proceso de Instalación (Paso a Paso)

1.  **Clonar el Repositorio**
    Abra la terminal en el directorio deseado y clone el proyecto:
    ```bash
    git clone https://github.com/MG1903/Proyecto-AsistenteIA.git
    cd Proyecto-AsistenteIA
    ```

2.  **Crear Entorno Virtual (Recomendado) (Opcional)**
    Aísle las dependencias para evitar conflictos:
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Linux/macOS
    # .\venv\Scripts\activate   # En Windows Powershell
    ```

3.  **Instalar Dependencias**
    Instale todas las bibliotecas de Python requeridas (LangChain, ChromaDB, Django, etc.):
    ```bash
    pip install -r requirements.txt
    ```

4.  **Aplicar Migraciones**
    Prepare la base de datos relacional para los modelos de Logs, Consultas y Documentos:
    ```bash
    python manage.py migrate
    ```

### 2.2. Configuración de Parámetros (Claves de API)

Para conectar el sistema al LLM y habilitar las alertas SMTP, cree un archivo llamado **`.env`** en la raíz del proyecto.

> **Importante:** Las credenciales deben ser solicitadas personalmente al equipo de desarrollo.

| Clave | Propósito | Ejemplo (Formato) |
| :--- | :--- | :--- |
| `DEEPSEEK_API_KEY` | Autenticación del servicio LLM. | `sk-xxxxxxxxxxxxxxxxxxxxxxxx` |
| `CORREO` | Correo del administrador (Para SMTP). | `tu_correo@gmail.com` |
| `SMTP_KEY`| Contraseña de Aplicación de Correo (SMTP). | `abcde fghij klmno pqrst` |

### 2.3. Configuración y Carga Inicial

1.  **Crear un Superusuario**
    Necesario para acceder al Panel de Administración y cargar documentos:
    ```bash
    python manage.py createsuperuser
    ```

2.  **Carga del Conocimiento Base (RAG)**
    Acceda al Panel de Administración (`/login/`) y use la sección **Documentos** para subir el archivo `.csv` con el inventario o la base de conocimiento de la relojería. Este paso genera los embeddings y activa el motor RAG.

### 2.4. Ejecución del Servidor

El proyecto utiliza un servidor ASGI optimizado para rendimiento asíncrono y WebSockets.

```bash
daphne App.asgi:application



