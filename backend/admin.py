from django.contrib import admin
from backend.models import *


class DocumentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'upload_time', 'replicate', 'description')
    list_display_links = ('filename',)
    list_filter = ('replicate',)


class ActionLogRecordAdmin(admin.ModelAdmin):
    list_display = ('username', 'timestamp', 'description')
    list_display_links = ('description',)
    list_filter = ('username',)


admin.site.register(Document, DocumentAdmin)
admin.site.register(ActionLogRecord, ActionLogRecordAdmin)
