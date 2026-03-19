from django.urls import path
from . import views

app_name = 'oil_records'

urlpatterns = [
    path('', views.me_home, name='me_home'),
    path('oil-inspection/', views.dashboard, name='dashboard'),
    path('upload/', views.upload_report, name='upload_report'),
    path('upload-simple/', views.upload_report_simple, name='upload_report_simple'),
    path('batch-upload/', views.batch_upload, name='batch_upload'),
    path('batch-upload-async/', views.batch_upload_async, name='batch_upload_async'),
    path('batch-upload-stream/', views.batch_upload_stream, name='batch_upload_stream'),
    path('upload-preview/', views.upload_preview, name='upload_preview'),
    path('ocr-preview-display/', views.ocr_preview_display, name='ocr_preview_display'),
    path('confirm-upload/', views.confirm_upload, name='confirm_upload'),
    path('api/equipment/', views.get_equipment_api, name='get_equipment_api'),
    path('api/trends/', views.get_trends_api, name='get_trends_api'),
    path('api/all-trends/', views.get_all_trends_api, name='get_all_trends_api'),
    path('api/table-data/', views.get_table_data_api, name='get_table_data_api'),
    path('export/', views.export_data, name='export_data'),
    path('download-md/<int:report_id>/', views.download_md_file, name='download_md_file'),
    # Downtime Report URLs
    path('downtime-report/', views.downtime_report, name='downtime_report'),
    path('api/downtime-report/generate/', views.generate_downtime_report_view, name='generate_downtime_report'),
]
