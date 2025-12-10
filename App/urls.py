"""
URL configuration for App project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from Core import views
from django.conf import settings
from django.conf.urls.static import static
from Core.views import chat_view, panel_dashboard, panel_documentos, panel_documentos_upload, panel_metricas, panel_consultas, panel_logs, CustomLoginView, ver_contenido_documento, ver_chunks, logout_view


urlpatterns = [
    path('admin/', admin.site.urls),
    path("ask/", chat_view, name="chat"),
    path("", views.chat_page, name="chat_page"),

    # Panel
    path("panel/", panel_dashboard, name="panel_dashboard"),
    path("panel/documentos/", panel_documentos, name="panel_documentos"),
    path("panel/documentos/upload/", panel_documentos_upload, name="panel_documentos_upload"),
    path('api/doc/<int:doc_id>/content/', ver_contenido_documento, name='api_ver_contenido'),
    path('api/doc/<int:doc_id>/chunks/', ver_chunks, name='api_ver_chunks'),
    path("panel/metricas/", panel_metricas, name="panel_metricas"),
    path("panel/consultas/", panel_consultas, name="panel_consultas"),
    path("panel/logs/", panel_logs, name="panel_logs"),

    # Login
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
