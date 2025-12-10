from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from .rag import preguntar, agregar_datos
from django.db.models import Avg, Count, Min, Max, F, Q
from django.utils import timezone
from .models import Documento, Consulta, Metricas, Logs, DocumentosChunk
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
import csv

# Create your views here.
def chat_view(request):
    pregunta = request.GET.get("q", "")
    if not pregunta:
        return JsonResponse({"error": "Falta la pregunta"}, status=400)

    respuesta = preguntar(pregunta)
    return JsonResponse({"respuesta": respuesta})

def chat_page(request):
    return render(request, "chat.html")

@login_required
def panel_dashboard(request):
    total_documentos = Documento.objects.count()
    ultimo = Documento.objects.order_by('-fecha_subida').first()

    total_consultas = Consulta.objects.count()
    hoy = timezone.localdate()
    consultas_hoy = Consulta.objects.filter(fecha__date=hoy).count()

    promedio_tiempo = Metricas.objects.aggregate(
        avg_ms=Avg('tiempo_respuesta_ms')
    )['avg_ms']

    documentos_pendientes = Documento.objects.filter(estado='Pendiente').count()
    documentos_cargados = Documento.objects.filter(estado='Cargado').count()

    total_errores = Logs.objects.filter(accion='ERROR_RAG').count()

    context = {
        "section": "dashboard",
        "total_documentos": total_documentos,
        "ultimo_documento_fecha": ultimo.fecha_subida if ultimo else None,
        "total_consultas": total_consultas,
        "consultas_hoy": consultas_hoy,
        "promedio_tiempo_ms": promedio_tiempo,
        "documentos_pendientes": documentos_pendientes,
        "documentos_cargados": documentos_cargados,
        "total_errores": total_errores,
        "disponibilidad_porcentaje": 100,
        "ultimas_consultas": Consulta.objects.order_by('-fecha')[:5],
    }
    return render(request, "dashboard.html", context)

@login_required
def panel_documentos(request):
    qs = Documento.objects.all().order_by('-fecha_subida')
    q = request.GET.get("q")
    if q:
        qs = qs.filter(nombre_archivo__icontains=q)

    ultimo = qs.first()

    context = {
        "section": "documentos",
        "documentos": qs,
        "total_documentos": qs.count(),
        "documentos_pendientes": qs.filter(estado='Pendiente').count(),
        "documentos_cargados": qs.filter(estado='Cargado').count(),
        "ultimo_documento_fecha": ultimo.fecha_subida if ultimo else None,
    }
    return render(request, "documentos_list.html", context)

@login_required
def panel_documentos_upload(request):
    """
    Recibe el archivo vía AJAX, SOLO procesa CSV y devuelve JSON.
    """
    if request.method == "POST" and request.FILES.get("archivo"):
        archivo = request.FILES["archivo"]
        nombre_archivo = archivo.name.lower()

        if not nombre_archivo.endswith('.csv'):
            return JsonResponse({
                "status": "error", 
                "message": "Formato de archivo no compatible" 
            })

        # 1. Crear registro "Procesando"
        doc = Documento.objects.create(
            usuario=request.user,
            nombre_archivo=archivo.name,
            archivo=archivo,
            estado="Procesando"
        )

        try:
            ruta_archivo = doc.archivo.path
            textos_para_chroma = []
        
            encoding = 'utf-8-sig'
            try:
                with open(ruta_archivo, 'r', encoding=encoding) as f:
                    f.read(1024)
            except UnicodeDecodeError:
                encoding = 'latin-1'

            with open(ruta_archivo, mode='r', encoding=encoding) as f:
                # Detectar delimitador (; o ,)
                linea_prueba = f.readline()
                f.seek(0)
                delim = ';' if ';' in linea_prueba else ','
                
                lector_csv = csv.reader(f, delimiter=delim)
                next(lector_csv, None) # Saltar encabezados

                for fila in lector_csv:
                    if len(fila) >= 5:
                        try:
                            # Ajusta índices según tus columnas
                            frase = (
                                f"Producto: {fila[2]} (Código: {fila[1]}). "
                                f"Precio: ${fila[3]}. "
                                f"Stock disponible: {fila[4]} unidades."
                            )
                            textos_para_chroma.append(frase)
                        except Exception:
                            continue

            if not textos_para_chroma:
                raise ValueError("El archivo CSV está vacío o no tiene filas válidas.")

            # --- PROCESAMIENTO POR LOTES ---
            cantidad_total = len(textos_para_chroma)
            tamanio_lote = 500
            chunks_para_bd = []

            for i in range(0, cantidad_total, tamanio_lote):
                lote = textos_para_chroma[i:i + tamanio_lote]
                agregar_datos(lote) # ChromaDB
                
                for texto in lote:
                    chunks_para_bd.append(
                        DocumentosChunk(documento_origen=doc, contenido_del_texto=texto)
                    )

            DocumentosChunk.objects.bulk_create(chunks_para_bd)

            doc.estado = "Cargado"
            doc.save()

            Logs.objects.create(
                usuario=request.user, documento=doc, 
                accion="SUBIDA_OK", detalles=f"Cargados {cantidad_total} items."
            )

            return JsonResponse({
                "status": "success", 
                "message": f"Documento procesado correctamente. {cantidad_total} items agregados."
            })

        except Exception as e:
            doc.estado = "Error"
            doc.save()
            Logs.objects.create(
                usuario=request.user, documento=doc, 
                accion="ERROR_SUBIDA", detalles=str(e)
            )
            return JsonResponse({"status": "error", "message": f"Error interno: {str(e)}"})

    return JsonResponse({"status": "error", "message": "No se envió archivo válido."})

@login_required
def ver_contenido_documento(request, doc_id):
    """Devuelve el contenido raw del archivo (primeros 5000 caracteres)"""
    doc = get_object_or_404(Documento, pk=doc_id)
    try:
        # Leemos el archivo físico
        with open(doc.archivo.path, 'r', encoding='utf-8', errors='replace') as f:
            contenido = f.read(5000)
            if len(contenido) == 5000:
                contenido += "\n\n... (Vista previa truncada para rendimiento)"
    except Exception as e:
        contenido = f"Error leyendo archivo: {str(e)}"
    
    return JsonResponse({'status': 'success', 'nombre': doc.nombre_archivo, 'contenido': contenido})

@login_required
def ver_chunks(request, doc_id):
    """Devuelve los chunks generados para este documento"""
    doc = get_object_or_404(Documento, pk=doc_id)
    # Obtenemos los textos de la BD
    chunks = list(DocumentosChunk.objects.filter(documento_origen=doc).values('id', 'contenido_del_texto'))
    
    return JsonResponse({'status': 'success', 'nombre': doc.nombre_archivo, 'chunks': chunks})

@login_required
def panel_metricas(request):
    metricas_qs = Metricas.objects.select_related("consulta").order_by("-fecha")

    total_metricas = metricas_qs.count()

    agg = metricas_qs.aggregate(
        avg_tiempo=Avg("tiempo_respuesta_ms"),
        min_tiempo=Min("tiempo_respuesta_ms"),
        max_tiempo=Max("tiempo_respuesta_ms"),
        avg_precision=Avg("precision"),
    )

    context = {
        "section": "metricas",
        "total_metricas": total_metricas,
        "avg_tiempo": agg["avg_tiempo"],
        "min_tiempo": agg["min_tiempo"],
        "max_tiempo": agg["max_tiempo"],
        "avg_precision": agg["avg_precision"],
        "metricas": metricas_qs[:50],
    }
    return render(request, "metricas.html", context)

@login_required
def panel_consultas(request):
    q = request.GET.get("q", "").strip()

    consultas_qs = Consulta.objects.all().order_by("-fecha")

    if q:
        consultas_qs = consultas_qs.filter(
            models.Q(texto_pregunta__icontains=q) |
            models.Q(texto_respuesta__icontains=q)
        )

    # Anotamos tiempo y precisión desde Metricas
    consultas_qs = consultas_qs.annotate(
        tiempo_respuesta_ms=F("metricas__tiempo_respuesta_ms"),
        precision_val=F("metricas__precision"),
    )

    hoy = timezone.localdate()
    consultas_hoy = Consulta.objects.filter(fecha__date=hoy).count()
    total_consultas = Consulta.objects.count()

    avg_tiempo = Metricas.objects.aggregate(
        avg_t=Avg("tiempo_respuesta_ms")
    )["avg_t"]

    context = {
        "section": "consultas",
        "consultas": consultas_qs[:100],
        "consultas_hoy": consultas_hoy,
        "total_consultas": total_consultas,
        "avg_tiempo": avg_tiempo,
        "busqueda": q,
    }
    return render(request, "consultas_list.html", context)

@login_required
def panel_logs(request):
    q = request.GET.get("q", "").strip()
    accion_filtro = request.GET.get("accion", "").strip()

    logs_qs = Logs.objects.select_related("usuario", "documento").order_by("-timestamp")

    if q:
        logs_qs = logs_qs.filter(
            Q(accion__icontains=q) |
            Q(detalles__icontains=q) |
            Q(documento__nombre_archivo__icontains=q)
        )

    if accion_filtro:
        logs_qs = logs_qs.filter(accion=accion_filtro)

    hoy = timezone.localdate()
    logs_hoy = Logs.objects.filter(timestamp__date=hoy).count()
    total_logs = Logs.objects.count()
    errores_rag = Logs.objects.filter(accion="ERROR_RAG").count()
    subidas_docs = Logs.objects.filter(accion="SUBIDA_DOCUMENTO").count()

    acciones_disponibles = (
        Logs.objects.values_list("accion", flat=True)
        .distinct()
        .order_by("accion")
    )

    context = {
        "section": "logs",
        "logs": logs_qs[:200],
        "total_logs": total_logs,
        "logs_hoy": logs_hoy,
        "errores_rag": errores_rag,
        "subidas_docs": subidas_docs,
        "acciones_disponibles": acciones_disponibles,
        "accion_filtro": accion_filtro,
        "busqueda": q,
    }
    return render(request, "logs_list.html", context)

class CustomLoginView(LoginView):
    template_name = 'login.html'
    redirect_authenticated_user = True

def logout_view(request):
    """Cierra sesión y redirige al login"""
    logout(request)
    return redirect('login')