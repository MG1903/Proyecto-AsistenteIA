from django.db import models
from django.contrib.auth.models import User
import threading
import time

# --- Modelos para la Gestión de Conocimiento (Admin) ---

class Documento(models.Model):
    """
    Representa un documento fuente subido por el Administrador.
    Corresponde a la tabla 'documento' del diagrama.
    """
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    nombre_archivo = models.CharField(max_length=255)
    archivo = models.FileField(upload_to='documentos/')
    fecha_subida = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=50, default='Pendiente')

    def __str__(self):
        return self.nombre_archivo
    

class DocumentosChunk(models.Model):
    """
    Representa un fragmento (chunk) de un documento, listo para ser vectorizado.
    Corresponde a la tabla 'documentoschunk' del diagrama.
    """
    documento_origen = models.ForeignKey(Documento, on_delete=models.CASCADE)
    contenido_del_texto = models.TextField()
    def __str__(self):
        return f"Chunk de {self.documento_origen.nombre_archivo[:20]}..."

# --- Modelos para Métricas y Trazabilidad ---

class Consulta(models.Model):
    """
    Registra cada interacción (pregunta y respuesta) con el asistente.
    Corresponde a la tabla 'consulta' del diagrama.
    """
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    texto_pregunta = models.TextField()
    texto_respuesta = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pregunta: {self.texto_pregunta[:30]}..."

class Metricas(models.Model):
    """
    Almacena las métricas de rendimiento de cada consulta.
    Corresponde a la tabla 'metricas' del diagrama.
    """
    # Vinculamos la métrica a la consulta específica
    consulta = models.OneToOneField(Consulta, on_delete=models.CASCADE)
    precision = models.FloatField(null=True, blank=True)
    tiempo_respuesta_ms = models.FloatField()
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Métricas de Consulta {self.consulta.id} ({self.tiempo_respuesta_ms} ms)"

class Logs(models.Model):
    """
    Registro de eventos importantes del sistema (ej: errores, subidas).
    """
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    documento = models.ForeignKey(Documento, on_delete=models.SET_NULL, null=True, blank=True)
    accion = models.CharField(max_length=255)
    detalles = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.timestamp}] {self.accion}"
    