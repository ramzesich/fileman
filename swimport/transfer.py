import http.client
import json
import os, os.path
import subprocess
import urllib.parse, urllib.request


STORAGE_HOST       = 'filebox'
WEBSITE_HOST       = 'compulab.co.il'
RELATIVE_URL_START = '/wp-content'
LINKS_FILE         = 'docs.json'
TMP_FILE           = '/tmp/{0}'
CHUNK              = 512 * 1024


def get_links():
    with open(LINKS_FILE, 'r') as links_file:
        links = json.loads(links_file.read())
    return links


def create_folders(links):
    folders = set()
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    conn = http.client.HTTPConnection(STORAGE_HOST)
    for link in links:
        product = link['product'][0]
        if product in folders:
            continue
        params = urllib.parse.urlencode({'action': 'mkdir', 'filename': product})
        try:
            conn.request('POST', '/file/action/', params, headers)
        except Exception as e:
            print("ERROR: creating folder {0}: could not connect to storage host: {1}".format(product, str(e)))
            conn.close()
            return False
        response = conn.getresponse()
        print("creating folder {0}: {1} {2} {3}".format(product,
                                                        response.status,
                                                        response.reason,
                                                        response.read()))
        folders.add(product)
    conn.close()
    return True


def transfer_files(links):
    try:
        localfiles = urllib.request.urlopen('http://{0}/file/list/?entire=true'.format(STORAGE_HOST))
    except urllib.error.URLError as e:
        print("couldn't retrieve local file list")
        exit(1)
    localfiles = json.loads(localfiles.read().decode(localfiles.headers.get_content_charset() or 'utf-8'))
    localfiles = set([os.path.basename(f).split('__')[0] for f in localfiles])
    for link in links:
        url      = link['url'][0]
        title    = link['title'][0]
        product  = link['product'][0]
        filename = os.path.basename(url)
        tmp_file = TMP_FILE.format(filename)
        if filename in localfiles:
            print("skipping existing file: {0}".format(filename))
            continue
        if url.startswith(RELATIVE_URL_START):
            url = 'http://{0}{1}'.format(WEBSITE_HOST, url)
        try:
            data = urllib.request.urlopen(url)
        except urllib.error.HTTPError as e:
            print("ERROR: could not open {0}: {1}".format(url, str(e)))
            continue
        with open(tmp_file, 'wb') as tmp_file_obj:
            chunk = data.read(CHUNK)
            while chunk:
                tmp_file_obj.write(chunk)
                chunk = data.read(CHUNK)
        print("fetched {0}".format(title))
        output = subprocess.check_output(['curl',
                                          '-F',
                                          'file=@{0}'.format(tmp_file),
                                          '-F',
                                          'filename={0}'.format(filename),
                                          '-F',
                                          'action=add',
                                          '-F',
                                          'location={0}'.format(product),
                                          '-F',
                                          'description={0}'.format(title),
                                          'http://{0}/file/action/'.format(STORAGE_HOST)])
        print("tried to upload {0}: {1}".format(title, output))
        os.unlink(tmp_file)


if __name__ == '__main__':
    links = get_links()
    if create_folders(links): transfer_files(links)
