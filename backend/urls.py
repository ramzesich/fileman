from django.conf import settings
from django.conf.urls import patterns, url


urlpatterns = patterns('',
    url(r'^action/$', 'backend.views.dispatcher', name='file_dispatcher'),
    url(r'^list/$', 'backend.views.file_list', name='file_list'),
    url(r'^foldertree/$', 'backend.views.folder_tree', name='folder_tree'),
    url(r'^search/$', 'backend.views.file_search', name="file_search"),
    url(r'^meta/$', 'backend.views.file_meta', name="file_meta"),
)
