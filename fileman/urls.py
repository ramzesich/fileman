from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import login, logout_then_login

admin.autodiscover()

urlpatterns = patterns('',
    # the admin site
    (r'^admin/', include(admin.site.urls)),
    
    url(r'^$', 'ui.views.home', name='home'),
    url(r'^search/$', 'ui.views.search', name="search"),
    url(r'^file/', include('backend.urls')),
    
    # authentication
    url(r'^login/$', login, {'template_name': 'ui/login.html'}, name='login'),
    url(r'^logout/$', logout_then_login, {'login_url': '/login/?next=/'}, name='logout'),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
