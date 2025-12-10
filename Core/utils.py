from django.core.mail import send_mail
from django.conf import settings
from dotenv import load_dotenv
import os
import threading

load_dotenv()
Correo= os.environ.get("CORREO")

def enviar_alerta_admin_sync(pregunta, respuesta, precision):
    asunto = f"ALERTA RAG: Posible fallo de respuesta (Confianza: {precision:.2f})"
    mensaje = f"""
    El asistente no pudo responder correctamente, pero el sistema detectó información relevante en la base de datos.
    
    ------------------------------------------------
    Pregunta del Usuario:
    {pregunta}
    
    Respuesta del Modelo:
    {respuesta}
    
    Precisión Vectorial (Similitud):
    {precision:.2f} (Alta coincidencia encontrada)
    ------------------------------------------------
    
    Se recomienda revisar los chunks o el prompt del sistema.
    """
    
    try:
        send_mail(
            subject=asunto,
            message=mensaje,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[Correo],
            fail_silently=False,
        )
        print("Correo de alerta enviado al administrador.")
    except Exception as e:
        print(f"Error enviando correo: {e}")

def enviar_alerta_background(pregunta, respuesta, precision):
    thread = threading.Thread(
        target=enviar_alerta_admin_sync, 
        args=(pregunta, respuesta, precision)
    )
    thread.start()