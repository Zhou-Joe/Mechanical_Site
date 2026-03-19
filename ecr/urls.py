from django.urls import path
from . import views

app_name = 'ecr'

urlpatterns = [
    path('', views.ecr_list, name='ecr_list'),
    path('create/', views.ecr_create, name='ecr_create'),
    path('<int:pk>/', views.ecr_detail, name='ecr_detail'),
    path('<int:pk>/edit/', views.ecr_edit, name='ecr_edit'),
    path('<int:pk>/export/', views.ecr_export, name='ecr_export'),
    path('import/', views.ecr_import, name='ecr_import'),
]
