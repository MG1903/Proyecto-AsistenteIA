from django.contrib import admin, messages
from .models import Documento, DocumentosChunk, Consulta, Metricas, Logs
from .rag import agregar_datos
import os
import csv

BATCH_SIZE = 500

class DocumentosChunkInline(admin.TabularInline):
    """Permite visualizar los fragmentos vectorizados dentro del detalle del documento."""
    model = DocumentosChunk
    extra = 0
    readonly_fields = ('contenido_del_texto',)

@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    """
    Administración de documentos. 
    Integra el pipeline de ingestión RAG: Parsing -> Vectorización (ChromaDB) -> Persistencia SQL.
    """
    list_display = ('nombre_archivo', 'estado', 'fecha_subida', 'usuario')
    list_filter = ('estado', 'fecha_subida')
    search_fields = ('nombre_archivo',)
    inlines = [DocumentosChunkInline]

    def save_model(self, request, obj, form, change):
        """
        Sobrescribe el guardado para disparar el procesamiento síncrono del archivo.
        Maneja el flujo completo desde la subida física hasta la indexación vectorial.
        """
        # Establecer estado inicial y guardar físicamente
        obj.estado = 'Procesando'
        super().save_model(request, obj, form, change)

        try:
            ruta_archivo = obj.archivo.path
            _, extension = os.path.splitext(ruta_archivo)
            textos_procesados = []

            # Delegar parsing según formato
            if extension.lower() == '.csv':
                textos_procesados = self._parse_csv(ruta_archivo)
            elif extension.lower() == '.txt':
                textos_procesados = self._parse_txt(ruta_archivo)
            else:
                raise ValueError(f"Extensión '{extension}' no soportada. Use .csv o .txt")

            if not textos_procesados:
                raise ValueError("El archivo no contiene registros válidos para procesar.")

            # Iniciar vectorización por lotes
            total_items = self._process_batches(obj, textos_procesados)

            # Finalización exitosa
            obj.estado = 'Procesado'
            obj.save()
            
            Logs.objects.create(
                usuario=request.user, documento=obj, accion='PROCESADO_OK',
                detalles=f"Ingestión exitosa de {total_items} registros."
            )
            messages.success(request, f"Procesamiento completado. {total_items} vectores generados.")

        except Exception as e:
            # Rollback lógico en caso de fallo
            print(f"Error en pipeline RAG: {e}")
            obj.estado = 'Error'
            obj.save()
            
            Logs.objects.create(
                usuario=request.user, documento=obj, accion='ERROR_ADMIN',
                detalles=str(e)
            )
            messages.error(request, f"Fallo en el procesamiento: {str(e)}")

    def _parse_csv(self, filepath):
        """
        Maneja la lectura robusta de CSV, detectando encoding (utf-8-sig/latin-1)
        y delimitadores (;/,) dinámicamente.
        """
        textos = []
        encoding = 'utf-8-sig'
        
        # Detección heurística de encoding para soporte Excel/Windows
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                f.read(1024)
        except UnicodeDecodeError:
            encoding = 'latin-1'

        with open(filepath, mode='r', encoding=encoding) as f:
            # Detección de delimitador basada en la primera línea
            first_line = f.readline()
            f.seek(0)
            delim = ';' if ';' in first_line else ','
            
            lector = csv.reader(f, delimiter=delim)
            next(lector, None)  # Omitir header

            for row in lector:
                # Validación estricta de estructura (mínimo 5 columnas esperadas)
                if len(row) >= 5:
                    try:
                        # Mapping: 1=Código, 2=Descripción, 3=Precio, 4=Stock
                        frase = (
                            f"Producto: {row[2].strip()} (Código: {row[1].strip()}). "
                            f"Precio: ${row[3].strip()}. "
                            f"Stock disponible: {row[4].strip()} unidades."
                        )
                        textos.append(frase)
                    except IndexError:
                        continue 
        return textos

    def _parse_txt(self, filepath):
        """Lee archivos de texto plano separando contenido por párrafos dobles."""
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read().split('\n\n')

    def _process_batches(self, doc_obj, textos):
        """
        Divide la carga de trabajo en lotes para optimizar memoria y llamadas a la API.
        Realiza inserción en ChromaDB y bulk_create en SQLite.
        """
        total = len(textos)
        chunks_sql = []

        print(f"Iniciando procesamiento por lotes para {total} registros...")

        for i in range(0, total, BATCH_SIZE):
            lote = textos[i:i + BATCH_SIZE]
            
            # 1. Persistencia Vectorial (ChromaDB)
            agregar_datos(lote)
            
            # 2. Preparación Persistencia Relacional (SQLite)
            for texto in lote:
                chunks_sql.append(
                    DocumentosChunk(documento_origen=doc_obj, contenido_del_texto=texto)
                )
            
            print(f"Lote procesado: {i} a {min(i + BATCH_SIZE, total)}")

        # Escritura masiva en BD para reducir overhead de transacciones
        DocumentosChunk.objects.bulk_create(chunks_sql)
        
        return total

# --- Configuración Estándar para otros Modelos ---

@admin.register(Consulta)
class ConsultaAdmin(admin.ModelAdmin):
    list_display = ('texto_pregunta', 'fecha', 'usuario')
    list_filter = ('fecha',)
    search_fields = ('texto_pregunta', 'texto_respuesta')
    readonly_fields = ('usuario', 'texto_pregunta', 'texto_respuesta', 'fecha')

@admin.register(Metricas)
class MetricasAdmin(admin.ModelAdmin):
    list_display = ('consulta', 'tiempo_respuesta_ms', 'fecha')
    list_filter = ('fecha',)
    readonly_fields = ('consulta', 'tiempo_respuesta_ms', 'fecha', 'precision')

@admin.register(Logs)
class LogsAdmin(admin.ModelAdmin):
    list_display = ('accion', 'timestamp', 'usuario', 'documento')
    list_filter = ('accion', 'timestamp')
    readonly_fields = ('accion', 'timestamp', 'usuario', 'documento', 'detalles')