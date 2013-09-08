#!/usr/bin/env python3
import argparse
import json
import os, os.path
import smtplib
import sqlite3
import subprocess
import time
import urllib.parse, urllib.request

from datetime import datetime
from email.mime.text import MIMEText


DEFAULT_ENCODING = 'utf-8'
DATETIME_FMT     = '%H:%M %b %d, %Y'
EMAIL_SENDER     = 'report@filebox'
SMTP_HOST        = 'localhost'
LOCK_FILE        = os.path.realpath(os.path.join(os.path.dirname(__file__), 'replication.lock'))
DATABASE_FILE    = os.path.realpath(os.path.join(os.path.dirname(__file__), '../filemandb'))
SLEEP_SECONDS    = 10


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--backendhost', default='localhost')
    parser.add_argument('--remotehost', default='filebox')
    parser.add_argument('--fileroot', default=os.path.realpath(os.path.join(os.path.dirname(__file__), '../fileman/media/files/')))
    parser.add_argument('--email', default='webmaster@compulab.co.il')
    return parser.parse_args()


def diff(backendhost, remotehost):
    try:
        localfiles = urllib.request.urlopen('http://{0}/file/list/?entire=true&replication=true'.format(backendhost))
    except urllib.error.URLError as e:
        return ("Error requesting local file list: {0}".format(str(e)), set())
    try:
        remotefiles = urllib.request.urlopen('http://{0}/file/list/?entire=true'.format(remotehost))
    except urllib.error.URLError as e:
        return ("Error requesting remote file list: {0}".format(str(e)), set())
    localfiles = set(json.loads(localfiles.read().decode(localfiles.headers.get_content_charset() or DEFAULT_ENCODING)))
    remotefiles = set(json.loads(remotefiles.read().decode(remotefiles.headers.get_content_charset() or DEFAULT_ENCODING)))
    files_to_replicate = localfiles - remotefiles
    orphan_files = remotefiles - localfiles
    status = "Files to replicate: {0}".format(files_to_replicate) if files_to_replicate else "No files to replicate"
    status += "\n\nFiles on remote server that missing locally: {0}".format(orphan_files) if orphan_files else ""
    return (status, files_to_replicate)


# depends on cURL utility
def replicate(remotehost, fileroot, files_to_replicate):
    report = []
    for f in files_to_replicate:
        db_conn = sqlite3.connect(DATABASE_FILE)
        db_cursor = db_conn.cursor()
        filepath = os.path.join(fileroot, f.lstrip('/'))
        location, filename = os.path.split(os.path.dirname(f))
        db_cursor.execute('select upload_time, description from backend_document where filename like ?', (filepath,))
        try:
            upload_date, description = db_cursor.fetchone()
        except TypeError:
            report.append("Meta info of {0} seems to be missing in database, moving on to next file".format(filename))
            continue
        finally:
            db_cursor.close()
            db_conn.close()
        if os.path.isfile(filepath):
            output = subprocess.check_output(['curl',
                                              '-F',
                                              'file=@{0}'.format(filepath),
                                              '-F',
                                              'filename={0}'.format(filename),
                                              '-F',
                                              'location={0}'.format(location),
                                              '-F',
                                              'description={0}'.format(description),
                                              '-F',
                                              'date={0}'.format(upload_date),
                                              '-F',
                                              'action=add',
                                              'http://{0}/file/action/'.format(remotehost)])
            report.append("Replicating {0}: {1}".format(filename, output if output else "done"))
    return '\n'.join(report)


def report(email, diff_status, replicate_status):
    message = ("Replication performed at {0}\n"
               "----------------------------\n"
               "Report:\n\n"
               "{1}\n\n"
               "{2}".format(datetime.now().strftime(DATETIME_FMT), diff_status, replicate_status))
    
    message            = MIMEText(message)
    message['Subject'] = "Filebox replication report"
    message['From']    = EMAIL_SENDER
    message['To']      = email
    
    with smtplib.SMTP(SMTP_HOST) as s:
        s.sendmail(EMAIL_SENDER, email, message.as_string())


if __name__ == '__main__':
    while os.path.isfile(LOCK_FILE):
        time.sleep(SLEEP_SECONDS)
    with open(LOCK_FILE, 'w') as lock_file:
        print('', file=lock_file)
    args = parse_arguments()
    diff_status, files_to_replicate = diff(args.backendhost, args.remotehost)
    replicate_status = replicate(args.remotehost, args.fileroot, files_to_replicate)
    os.unlink(LOCK_FILE)
    report(args.email, diff_status, replicate_status)
