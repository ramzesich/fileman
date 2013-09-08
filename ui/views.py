from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound, Http404
from django.shortcuts import redirect, render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.http import require_GET

from datetime import datetime
from backend.models import Document
from fileman.util.lib import response_json

import json, re, urllib.request, urllib.parse


# views
@require_GET
@login_required
def home(request):
    location = '%s%s' % ('/', request.GET.get('location', '/').lstrip('/'))
    breadcrumbs = []
    breadcrumbs_added = []
    breadcrumb_url_base = reverse('home')
    for loc in ('%s%s' % ('Home', location.rstrip('/'))).split('/'):
        breadcrumbs_added.append(loc)
        breadcrumbs.append({
            'name': loc,
            'url': '%s?location=%s' % (breadcrumb_url_base, re.sub('^Home', '', '/'.join(breadcrumbs_added))),
        })
    try:
        file_list = urllib.request.urlopen('http://%s%s?%s' % (settings.BACKEND_HOST, reverse('file_list'), urllib.parse.urlencode({'location': location})))
        folder_tree = urllib.request.urlopen('http://%s%s' % (settings.BACKEND_HOST, reverse('folder_tree')))
    except urllib.error.HTTPError:
        return redirect('home')
    
    return render_to_response('ui/home.html', {
        'breadcrumbs': breadcrumbs,
        'entries': json.loads(file_list.read().decode(file_list.headers.get_content_charset() or settings.DEFAULT_ENCODING)),
        'folder_tree': _render_folder_tree(json.loads(folder_tree.read().decode(folder_tree.headers.get_content_charset() or settings.DEFAULT_ENCODING))),
        'location': location,
        'hash_concat': settings.HASH_CONCAT,
        'remote_host': settings.REMOTE_HOST,
    }, context_instance=RequestContext(request))


@require_GET
def search(request):
    try:
        items = urllib.request.urlopen('http://%s%s?%s' % (settings.BACKEND_HOST, reverse('file_search'), urllib.parse.urlencode({'s': request.GET.get('s', '')})))
    except urllib.error.HTTPError:
        return redirect('home')
    return render_to_response('ui/search.html', {
        'items': json.loads(items.read().decode(items.headers.get_content_charset() or settings.DEFAULT_ENCODING)),
        'breadcrumbs': [{'name': "Home",
                         'url': '/?location=/',
                         'inactive': True},
                        {'name': "Search"}]
    }, context_instance=RequestContext(request))


# internal functions
def _render_folder_tree(tree):
    def _render_branch(tree):
        html_tree = ''
        for entry in sorted(tree.keys()):
            html_tree += '<li><i class="icon-folder-close"></i><label data-dest="%s">%s</label>' % (tree[entry]['dest'], entry)
            if tree[entry]['children']:
                html_tree += '<ul>'
                html_tree += _render_branch(tree[entry]['children'])
                html_tree += '</ul>'
            html_tree += '</li>'
        return html_tree
    
    html_tree = '<div id="folder-tree" class="css-treeview"><ul><li><i class="icon-folder-close"></i><label data-dest="%s">%s</label><ul>' % ('/', "Home")
    html_tree += _render_branch(tree)
    html_tree += '</li></ul></ul></div>'
    return html_tree
