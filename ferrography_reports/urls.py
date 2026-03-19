from django.urls import path
from . import views

app_name = 'ferrography_reports'

urlpatterns = [
    path('', views.ferrography_home, name='home'),
    path('upload/', views.upload_ferrography_report, name='upload'),
    path('batch-upload/', views.batch_upload, name='batch_upload'),
    path('batch-upload-async/', views.batch_upload_async, name='batch_upload_async'),
    path('batch-upload-stream/', views.batch_upload_stream, name='batch_upload_stream'),
    path('preview/', views.preview_display, name='preview_display'),
    path('confirm/', views.confirm_ferrography_upload, name='confirm'),
    path('list/', views.report_list, name='list'),
    path('detail/<int:report_id>/', views.report_detail, name='detail'),
    path('api/equipment/', views.get_equipment_api, name='get_equipment_api'),
]
