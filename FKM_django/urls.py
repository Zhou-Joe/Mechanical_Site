from django.urls import path
from . import views

app_name = 'fkm'

urlpatterns = [
    path('', views.index, name='index'),
    path('fatigue/', views.fatigue_calculator, name='fatigue'),
    path('static/', views.static_calculator, name='static'),
    path('api/materials/', views.load_material_data, name='load_materials'),
    path('api/fatigue/step1/', views.calculate_fatigue_step1, name='fatigue_step1'),
    path('api/fatigue/step2/', views.calculate_fatigue_step2, name='fatigue_step2'),
    path('api/fatigue/step3/', views.calculate_fatigue_step3, name='fatigue_step3'),
    path('api/fatigue/step3-weld/', views.calculate_fatigue_step3_weld, name='fatigue_step3_weld'),
    path('api/fatigue/step4/', views.calculate_fatigue_step4, name='fatigue_step4'),
    path('api/fatigue/step4-weld/', views.calculate_fatigue_step4_weld, name='fatigue_step4_weld'),
    path('api/fatigue/step5/', views.calculate_fatigue_step5, name='fatigue_step5'),
    path('api/fatigue/step6/', views.calculate_fatigue_step6, name='fatigue_step6'),
    path('api/fatigue/export/', views.export_fatigue_report, name='export_fatigue'),
    path('api/static/', views.calculate_static, name='static_calc'),
    path('api/static/step1/', views.calculate_static_step1, name='static_step1'),
    path('api/static/step3/', views.calculate_static_step3, name='static_step3'),
    path('api/static/step4/', views.calculate_static_step4, name='static_step4'),
    path('api/static/step4-weld/', views.calculate_static_step4_weld, name='static_step4_weld'),
    path('api/static/step5/', views.calculate_static_step5, name='static_step5'),
    path('api/static/step6/', views.calculate_static_step6, name='static_step6'),
    path('api/static/export/', views.export_static_report, name='export_static'),
]
