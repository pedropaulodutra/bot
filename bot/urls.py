from django.urls import path
from bot import views
from .views import create_superuser_temp_view


urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('setup/criar-super-usuario-agora-92i374y5h/', create_superuser_temp_view, name='create_superuser_temp'),
]
