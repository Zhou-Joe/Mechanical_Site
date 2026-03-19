from django.contrib import admin
from .models import Attraction, Equipment, OilInspectionReport, OilParameter, UploadedFile

@admin.register(Attraction)
class AttractionAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at', 'updated_at']
    search_fields = ['name', 'description']
    list_filter = ['created_at']
    ordering = ['name']

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'attraction', 'location', 'equipment_type', 'created_at']
    search_fields = ['name', 'location', 'equipment_type', 'attraction__name']
    list_filter = ['attraction', 'equipment_type', 'created_at']
    ordering = ['attraction', 'name']

@admin.register(OilInspectionReport)
class OilInspectionReportAdmin(admin.ModelAdmin):
    list_display = ['equipment', 'report_date', 'sample_date', 'report_number', 'is_processed', 'created_at']
    search_fields = ['equipment__name', 'equipment__attraction__name', 'report_number']
    list_filter = ['equipment__attraction', 'report_date', 'sample_date', 'is_processed']
    ordering = ['-report_date']
    date_hierarchy = 'report_date'
    
    fieldsets = (
        ('基本信息', {
            'fields': ('equipment', 'report_date', 'sample_date', 'report_number')
        }),
        ('文件内容', {
            'fields': ('pdf_file', 'md_content', 'processed_data', 'is_processed')
        }),
    )

@admin.register(OilParameter)
class OilParameterAdmin(admin.ModelAdmin):
    list_display = ['report', 'parameter_name', 'parameter_value', 'unit', 'is_normal', 'created_at']
    search_fields = ['report__equipment__name', 'report__equipment__attraction__name', 'parameter_name']
    list_filter = ['parameter_name', 'is_normal', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('report', 'report__equipment', 'report__equipment__attraction')

@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'file_type', 'file_size', 'upload_time', 'processed', 'processing_status']
    search_fields = ['original_filename', 'file_type']
    list_filter = ['file_type', 'processed', 'processing_status', 'upload_time']
    ordering = ['-upload_time']
    readonly_fields = ['file_size', 'upload_time']
    
    fieldsets = (
        ('文件信息', {
            'fields': ('file', 'original_filename', 'file_type', 'file_size')
        }),
        ('处理状态', {
            'fields': ('processed', 'processing_status', 'error_message')
        }),
    )
