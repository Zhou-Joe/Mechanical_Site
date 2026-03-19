from django.contrib import admin
from .models import ECRRecord


@admin.register(ECRRecord)
class ECRRecordAdmin(admin.ModelAdmin):
    list_display = ['form_number', 'title', 'requestor', 'progress', 'request_date', 'completion_date']
    list_filter = ['progress', 'engineering_change_type', 'request_date']
    search_fields = ['form_number', 'title', 'requestor', 'doc_number', 'attraction_or_location']
    date_hierarchy = 'request_date'
