from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotAllowed, HttpResponseNotFound, Http404
from django.shortcuts import redirect, render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.http import require_GET

from fileman.util.lib import response_json
from backend.models import *

import hashlib, json, mimetypes, os, subprocess, urllib
from datetime import datetime
from shutil import move, rmtree


def dispatcher(request):
    methods = {
        'GET': file_get,
        'POST': file_action,
    }
    return request.method in methods and methods[request.method](request) or HttpResponseNotAllowed(methods.keys())


def file_get(request):
    filename = request.GET.get('filename')
    location = request.GET.get('location', '/').strip('/')
    nodate = bool(request.GET.get('nodate'))
    if os.path.isdir(os.path.join(settings.FILE_ROOT, location, filename)):
        hashsum = request.GET.get('hashsum', '')
        try:
            filepath = os.path.realpath(os.path.join(settings.FILE_ROOT, location, filename, hashsum and '%s%s%s' % (filename, settings.HASH_CONCAT, hashsum) or settings.DEFAULT_DL_LINK))
            fsock = open(filepath, 'rb')
        except FileNotFoundError:
            return HttpResponseNotFound()
        mime_type_guess = mimetypes.guess_type(filepath.split(settings.HASH_CONCAT)[0])
        if mime_type_guess is not None:
            doc = get_object_or_404(Document, filename=filepath)
            filename_head = filename.split('.')[0]
            filename = filename.replace(filename_head, '{0}.{1}'.format(filename_head, doc.upload_time.strftime('%Y-%m-%d')))
            response = HttpResponse(fsock, content_type=mime_type_guess[0])
            response['Content-Disposition'] = 'attachment; filename=\"{0}\"'.format(filename)
            return response
    return HttpResponseNotFound()


@require_GET
def file_list(request):
    location = request.GET.get('location', '/').strip('/')
    entire = request.GET.get('entire')
    replication = request.GET.get('replication')
    if entire:
        docs = Document.objects.filter(replicate=True) if replication else Document.objects.all()
        return response_json([doc.filename.replace(settings.FILE_ROOT, '') for doc in docs])
    entries = {'dirs': [], 'files': []}
    try:
        dirlist = os.listdir(os.path.join(settings.FILE_ROOT, location))
    except FileNotFoundError:
        return HttpResponseNotFound()
    for entry in sorted(dirlist):
        filepath = os.path.realpath(os.path.join(settings.FILE_ROOT, location, entry, settings.DEFAULT_DL_LINK))
        if os.path.exists(filepath):
            filename_components = os.path.basename(filepath).split(settings.HASH_CONCAT)
            doc = Document.objects.get(filename=filepath)
            file_data = {
                'filename': filename_components[0],
                'description': doc.description,
                'replicate': doc.replicate,
                'upload_datetime': doc.upload_time.strftime(settings.DATETIME_FMT),
                'hash': len(filename_components) > 1 and filename_components[1] or "",
                'previous_versions': [],
            }
            for v in sorted(os.listdir(os.path.join(settings.FILE_ROOT, location, entry)), key=lambda x: os.stat(os.path.join(settings.FILE_ROOT, location, entry, x)).st_mtime, reverse=True):
                if v in (settings.DEFAULT_DL_LINK, os.path.basename(os.path.realpath(os.path.join(settings.FILE_ROOT, location, entry, settings.DEFAULT_DL_LINK)))):
                    continue
                vdoc = Document.objects.get(filename=os.path.realpath(os.path.join(settings.FILE_ROOT, location, entry, v)))
                file_data['previous_versions'].append({
                    'description': vdoc.description,
                    'replicate': vdoc.replicate,
                    'upload_datetime': vdoc.upload_time.strftime(settings.DATETIME_FMT),
                    'hash': v.split(settings.HASH_CONCAT)[-1],
                })
            entries['files'].append(file_data)
        else:
            entries['dirs'].append({
                'dirname': entry,
                'empty': os.listdir(os.path.join(settings.FILE_ROOT, location, entry)) == [],
            })
    return response_json(entries)


@require_GET
def file_search(request):
    items = []
    query = request.GET.get('s', '').strip()
    if not query:
        return response_json([])
    for doc in Document.objects.filter(Q(filename__icontains=query) |
                                       Q(description__icontains=query)):
        filename_components = os.path.basename(doc.filename).split(settings.HASH_CONCAT)
        items.append({
            'filename': filename_components[0],
            'description': doc.description,
            'replicate': doc.replicate,
            'upload_datetime': doc.upload_time.strftime(settings.DATETIME_FMT),
            'hash': len(filename_components) > 1 and filename_components[1] or "",
            'default': doc.filename == os.path.realpath(os.path.join(os.path.dirname(doc.filename), settings.DEFAULT_DL_LINK)),
        })
    return response_json(items)


@require_GET
def file_meta(request):
    uri = request.GET.get('uri')
    if not uri:
        return response_json({})
    try:
        doc = Document.objects.filter(filename__contains=uri).order_by('-upload_time')[0]
    except IndexError:
        return response_json({})
    return response_json({'filename': doc.filename,
                          'date': doc.upload_time.strftime(settings.DATETIME_FMT),
                          'description': doc.description,
                          'replicate': doc.replicate})


@require_GET
def folder_tree(request):
    def _build_tree(rootpath=settings.FILE_ROOT):
        tree = {}
        entries = os.listdir(rootpath)
        for entry in sorted(entries):
            entrypath = os.path.join(rootpath, entry)
            if os.path.isdir(entrypath) and not os.path.exists(os.path.realpath(os.path.join(entrypath, settings.DEFAULT_DL_LINK))):
                tree[entry] = {
                    'dest': entrypath.replace(settings.FILE_ROOT, ''),
                    'children': _build_tree(entrypath),
                }
        return tree

    return response_json(_build_tree())


def file_action(request):
    actions = (
        'add',
        'mv',
        'rm',
        'mkdir',
        'rmdir',
        'replication',
        'description',
    )
    if request.POST.get('action', '') in actions:
        return globals()[request.POST['action']](request)
    return HttpResponseNotFound()


# actions
def add(request):
    filename = request.POST.get('filename')
    location = request.POST.get('location', '/').strip('/')
    upload_date = request.POST.get('date', '')
    if upload_date:
        upload_date = datetime.strptime(upload_date, settings.DATABASE_DEFAULT_DATETIME_FMT)
    filedir = os.path.join(settings.FILE_ROOT, location, filename)
    if not os.path.isdir(filedir):
        os.makedirs(filedir)
    filedata = request.FILES.get('file', None)
    filesymlink = os.path.join(filedir, settings.DEFAULT_DL_LINK)
    if not filedata:
        return response_json({'error': "upload contained no file data"})
    filepath = os.path.join(filedir, filename)
    filepath_temp = '%s_temp' % filepath
    h = hashlib.new('sha1')
    with open(filepath_temp, 'wb+') as newfile:
        for chunk in filedata.chunks():
            h.update(chunk)
            newfile.write(chunk)
    filehashname = '%s%s%s' % (filepath, settings.HASH_CONCAT, h.hexdigest())
    if os.path.isfile(filehashname):
        os.remove(filepath_temp)
    else:
        os.rename(filepath_temp, filehashname)
        if os.path.islink(filesymlink):
            os.remove(filesymlink)
        os.symlink(filehashname, filesymlink)
    doc, created = Document.objects.get_or_create(filename=filehashname)
    doc.description = request.POST.get('description', "")
    if upload_date:
        doc.upload_time = upload_date
    doc.save()
    
    _log_action(request, "file `%s` was added to `%s`" % (filename, location or "/"))
    return HttpResponse()


def mv(request):
    filename = request.POST.get('filename')
    location = request.POST.get('location', '/').strip('/')
    destination = request.POST.get('destination', '').lstrip('/')
    destdir = os.path.join(settings.FILE_ROOT, destination)
    filedir = os.path.join(settings.FILE_ROOT, location, filename)
    filesymlink = os.path.join(filedir, settings.DEFAULT_DL_LINK)
    default_dl_file = os.path.basename(os.path.realpath(filesymlink))
    if destdir == os.path.join(settings.FILE_ROOT, location):
        return HttpResponse()
    if not os.path.isdir(filedir):
        return response_json({'error': "file `%s` does not exist" % filename})
    if not os.path.isdir(destdir):
        return response_json({'error': "destination `%s` does not exist" % destination})
    os.remove(filesymlink)
    move(filedir, destdir)
    errors = []
    for entry in os.listdir(os.path.join(destdir, filename)):
        try:
            filepath = os.path.join(settings.FILE_ROOT, location, filename, entry)
            doc = Document.objects.get(filename=filepath)
            doc.filename = os.path.join(destdir, filename, entry)
            doc.save()
        except Document.DoesNotExist:
            errors.append("file `%s` has no metadata and needs to be fixed" % filepath)
    os.symlink(os.path.join(destdir, filename, default_dl_file), os.path.join(destdir, filename, settings.DEFAULT_DL_LINK))
    if errors:
        return response_json({'error': "the following errors occured:\n" + "\n".join(errors)})
    
    _log_action(request, "file `%s` was moved from `%s` to `%s`" % (filename, location or "/", destination or "/"))
    return HttpResponse()


def rm(request):
    filename = request.POST.get('filename')
    location = request.POST.get('location', '/').strip('/')
    filedir = os.path.join(settings.FILE_ROOT, location, filename)
    if not os.path.isdir(filedir):
        return response_json({'error': "file `%s` does not exist" % filename})
    rmtree(filedir)
    Document.objects.filter(filename__startswith=filedir).delete()
    
    _log_action(request, "file `%s` was permanently removed from `%s`" % (filename, location or "/"))
    return HttpResponse()


def mkdir(request):
    filename = request.POST.get('filename')
    location = request.POST.get('location', '/').strip('/')
    if not os.path.isdir(os.path.join(settings.FILE_ROOT, location)):
        return response_json({'error': "requested target location `%s` does not exist" % location})
    newdir_path = os.path.join(settings.FILE_ROOT, location, filename)
    if os.path.isdir(newdir_path):
        return response_json({'error': "directory already exists"})
    os.mkdir(newdir_path)
    
    _log_action(request, "directory `%s` was created" % newdir_path.replace(settings.FILE_ROOT, ''))
    return HttpResponse()


def rmdir(request):
    filename = request.POST.get('filename')
    location = request.POST.get('location', '/').strip('/')
    force = request.POST.get('force', False)
    if not os.path.isdir(os.path.join(settings.FILE_ROOT, location)):
        return response_json({'error': "requested target location `%s` does not exist" % location})
    dir_path = os.path.join(settings.FILE_ROOT, location, filename)
    if not os.path.isdir(dir_path):
        return response_json({'error': "directory `%s` does not exist" % dir_path.replace(settings.FILE_ROOT, '')})
    try:
        os.rmdir(dir_path)
    except OSError as error:
        if error.errno == settings.ERRNO_DIR_NOT_EMPTY:
            if force:
                rmtree(dir_path)
                Document.objects.filter(filename__startswith=dir_path).delete()
            else:
                return response_json({'error': "directory `%s` is not empty" % filename})
        else:
            return response_json({'error': str(error)})
    
    _log_action(request, "directory `%s` was permanently removed" % dir_path.replace(settings.FILE_ROOT, ''))
    return HttpResponse()


def replication(request):
    replicate = bool(request.POST.get('replicate', False))
    filename = request.POST.get('filename')
    location = request.POST.get('location', '/').strip('/')
    hashsum = request.POST.get('hashsum', '')
    filehashname = '%s%s%s' % (filename, settings.HASH_CONCAT, hashsum)
    filepath = os.path.join(settings.FILE_ROOT, location, filename, filehashname)
    if not os.path.isfile(filepath):
        return response_json({'error': "file `%s` does not exist" % filehashname})
    for doc in Document.objects.filter(filename=filepath):
        doc.replicate = replicate
        doc.save()
    
    _log_action(request, "replication turned %s for the file `%s` located in `%s`" % (replicate and "on" or "off", filehashname, location or "/"))
    
    if replicate:
        subprocess.Popen([os.path.join(settings.ROOT, '../backend', 'replicator.py'),
                          '--backendhost', settings.BACKEND_HOST,
                          '--remotehost', settings.REMOTE_HOST,
                          '--fileroot', settings.FILE_ROOT])
    return HttpResponse()


def description(request):
    filename = request.POST.get('filename')
    location = request.POST.get('location', '/').strip('/')
    hashsum = request.POST.get('hashsum', '')
    filehashname = '%s%s%s' % (filename, settings.HASH_CONCAT, hashsum)
    filepath = os.path.join(settings.FILE_ROOT, location, filename, filehashname)
    if not os.path.isfile(filepath):
        return response_json({'error': "file `%s` does not exist" % filehashname})
    doc = get_object_or_404(Document, filename=filepath)
    doc.description = request.POST.get('description', '')
    doc.save()
    
    _log_action(request, "description updated for the file `%s` located in `%s`" % (filehashname, location or "/"))
    return HttpResponse()


# internal functions
def _log_action(request, action):
    ActionLogRecord(
        username=request.user.is_authenticated() and request.user.username or request.META.get('REMOTE_ADDR', ""),
        description=action
    ).save()
