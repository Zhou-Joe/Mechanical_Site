"""
URL configuration for Acceleration Reader application
"""

from django.urls import path
from . import views

app_name = 'acceleration_reader'

urlpatterns = [
    path('', views.home, name='home'),
    path('upload/', views.upload_file, name='upload_file'),
    path('plot-data/', views.get_plot_data, name='get_plot_data'),
    path('astm-fit/', views.get_astm_fit, name='get_astm_fit'),
    path('gb-fit/', views.get_gb_fit, name='get_gb_fit'),
    path('zone-analysis/', views.get_zone_analysis, name='get_zone_analysis'),
    path('reversal-analysis/', views.get_reversal_analysis, name='get_reversal_analysis'),
    path('edit-data/', views.edit_data, name='edit_data'),
    path('remove-dataset/', views.remove_dataset, name='remove_dataset'),
    path('export/', views.export_dataset, name='export_dataset'),
    path('report/', views.generate_report, name='generate_report'),
    path('clear-data/', views.clear_data, name='clear_data'),
]
