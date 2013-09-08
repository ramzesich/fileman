import json
import os, os.path
import sqlite3
import subprocess

from datetime import datetime


LINKS_FILE         = 'docs.json'
DATE_FMT           = '%B %d, %Y'
DATABASE           = os.path.join(os.path.realpath(os.path.dirname(__file__)), '../filemandb')


def get_links():
    print("harvesting file links")
    subprocess.call(['scrapy', 'crawl', 'compulab', '-o', LINKS_FILE, '-t', 'json'])
    with open(LINKS_FILE, 'r') as links_file:
        links = json.loads(links_file.read())
    return links


def update_dates(links):
    db_conn = sqlite3.connect(DATABASE)
    db_cursor = db_conn.cursor()
    for link in links:
        url      = link['url'][0]
        product  = link['product'][0]
        date     = link['date'][0]
        filename = os.path.basename(url)
        db_cursor.execute("""
        update backend_document
        set upload_time=?
        where filename like ?
        """, (datetime.strptime(date, DATE_FMT), '%{0}%'.format(os.path.join(product, filename))))
    db_conn.commit()
    db_cursor.close()
    db_conn.close()


if __name__ == '__main__':
    update_dates(get_links())
