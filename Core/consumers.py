import json
import time
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from .rag import preguntar
from .models import Consulta, Metricas, Logs
from .utils import enviar_alerta_background

class ChatConsumer(AsyncWebsocketConsumer):
    """
    Maneja las conexiones WebSocket para el chat en tiempo real.
    Orquesta la recepción de mensajes, invocación al RAG y 
    persistencia de métricas.
    """

    async def connect(self):
        await self.accept()

    async def receive(self, text_data):
        """
        Procesa el mensaje entrante, ejecuta la consulta RAG y gestiona alertas.
        """
        data = json.loads(text_data)
        pregunta = data.get("message")

        if not pregunta:
            await self.send(text_data=json.dumps({"message": "⚠️ Pregunta vacía"}))
            return

        start_time = time.monotonic()
        
        try:
            # Ejecutar RAG en hilo aparte para no bloquear el loop de eventos (ASGI)
            respuesta, precision = await sync_to_async(preguntar)(pregunta)
            
            end_time = time.monotonic()
            tiempo_respuesta_ms = (end_time - start_time) * 1000
            
            # Detección de Falsos Negativos (Incidente de Recuperación)
            frases_negativas = ["no tengo información", "no encuentro", "lo siento", "no sé", "disculpa"]
            es_respuesta_negativa = any(frase in respuesta.lower() for frase in frases_negativas)
            
            if precision > 0.60 and es_respuesta_negativa:
                print(f"ALERTA RAG: Contexto relevante (score {precision:.2f}) ignorado por el modelo.")
                enviar_alerta_background(pregunta, respuesta, precision)

            await self.guardar_consulta_y_metrica(
                pregunta, 
                respuesta, 
                tiempo_respuesta_ms,
                precision
            )

        except Exception as e:
            print(f"Excepción crítica en RAG: {e}")
            respuesta = "Lo siento, tuve un problema interno al procesar tu solicitud."
            
            await self.guardar_log_error(pregunta, str(e))
            
            await self.send(text_data=json.dumps({"message": respuesta}))
            return

        # Respuesta final al cliente
        await self.send(text_data=json.dumps({
            "user": pregunta,
            "message": respuesta
        }))

    @database_sync_to_async
    def guardar_consulta_y_metrica(self, pregunta_txt, respuesta_txt, tiempo_ms, precision_val):
        """Persiste la interacción y sus métricas de rendimiento en la base de datos relacional."""
        try:
            nueva_consulta = Consulta.objects.create(
                texto_pregunta=pregunta_txt,
                texto_respuesta=respuesta_txt
            )
            
            Metricas.objects.create(
                consulta=nueva_consulta,
                tiempo_respuesta_ms=tiempo_ms,
                precision=precision_val
            )
            print(f"Métrica registrada: {tiempo_ms:.0f}ms | Precisión: {precision_val:.2f}")

        except Exception as e:
            print(f"Fallo en persistencia de métricas: {e}")

    @database_sync_to_async
    def guardar_log_error(self, pregunta_txt, error_txt):
        """Registra excepciones críticas del flujo RAG en la tabla de Logs."""
        try:
            Logs.objects.create(
                accion='ERROR_RAG',
                detalles=f"Input: {pregunta_txt} | Exception: {error_txt}"
            )
        except Exception as e:
            print(f"Fallo crítico al guardar log de error: {e}")