from django.contrib import admin
from .models import FerrographyReport, FerrographyParticle, FerrographyDiagnosis


@admin.register(FerrographyReport)
class FerrographyReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'equipment', 'report_date', 'sample_date', 'is_processed', 'created_at']
    list_filter = ['is_processed', 'report_date']
    search_fields = ['equipment__name', 'report_number']
    date_hierarchy = 'report_date'


@admin.register(FerrographyParticle)
class FerrographyParticleAdmin(admin.ModelAdmin):
    list_display = ['report', 'particle_type', 'concentration']
    list_filter = ['particle_type']


@admin.register(FerrographyDiagnosis)
class FerrographyDiagnosisAdmin(admin.ModelAdmin):
    list_display = ['report', 'wear_status']
