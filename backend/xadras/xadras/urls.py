"""
Configuração de URL para o projeto xadras.

A lista `urlpatterns` encaminha URLs para vistas. Para mais informações, consulte:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Exemplos:
Vistas de função
    1. Adicionar uma importação:  from my_app import views
    2. Adicionar um URL a urlpatterns:  path('', views.home, name='home')
Vistas baseadas em classes
    1. Adicionar uma importação:  from other_app.views import Home
    2. Adicionar um URL a urlpatterns:  path('', Home.as_view(), name='home')
Incluir outro URLconf
    1. Importar a função include(): from django.urls import include, path
    2. Adicionar um URL a urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('djoser.urls')),
    path('api/', include('djoser.urls.authtoken')),
    path('api/accounts/', include('accounts.urls')),
    path('api/game/', include('game.urls')),
    path('api/matchmaking/', include('matchmaking.urls')),
    path('api/', include('tournaments.urls')),  # Endpoints de torneio
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
