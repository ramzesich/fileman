from django.conf import settings
from django.contrib.auth.models import User
from django.db import models


class Document(models.Model):
    filename = models.CharField(max_length=255, unique=True)
    upload_time = models.DateTimeField(auto_now_add=True)
    replicate = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return "%s" % self.filename
    
    class Meta:
        ordering = ['filename']


class ActionLogRecord(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    username = models.CharField(max_length=30)
    description = models.CharField(max_length=255)

    def __str__(self):
        return "%s [at %s]: %s" % (self.username, self.timestamp.strftime(settings.DATETIME_FMT), self.description)
    
    class Meta:
        ordering = ['username', 'timestamp']
