Asistente Virtual "A la Hora" - Prototipo RAG

Este proyecto es un prototipo de asistente virtual inteligente para la relojería "Bendita la Hora". Utiliza **Django**, **WebSockets** y técnicas de **RAG (Retrieval-Augmented Generation)** para responder consultas sobre inventario, precios y servicios en tiempo real.

Stack Tecnológico

* **Backend:** Django 5 + Django Channels
* **Servidor:** Daphne
* **IA / RAG:** LangChain, ChromaDB, Sentence-Transformers
* **LLM:** DeepSeek API
* **Base de Datos:** SQLite + ChromaDB 

---

**Instalación y Configuración**
Sigue estos pasos para levantar el proyecto en tu entorno local.

**Instalar dependencias**

* pip install -r requirements.txt

**Crear archivo .env**

* DEEPSEEK_API_KEY="xxxxxxxxxxxxxxxxx"
* SMPT_KEY="xxxxxxxxxxxxx"

**Aplicar migraciones**

* python manage.py migrate

**Crear un Superusuario**

* python manage.py createsuperuser

**Ejecutar el Servidor**

* daphne App.asgi:application



