from datetime import datetime, timedelta, date
from django.conf import settings
from django.db import models
from django.http import HttpResponse

import json, time


def _unix_timestamp(d):
    return int(time.mktime(d.timetuple()))


def _model2dict(item, fields=[]):
    d = {}
    for field in fields:
        f = item.__dict__[field]
        if type(f) in [datetime, date]:
            d[field] = _unix_timestamp(f)
        else:
            d[field] = f
    return d


def response_json(data, fields=[]):
    if (issubclass(data.__class__, models.Model)):
        data = _model2dict(data, fields)
    elif (issubclass(data.__class__, models.query.QuerySet)):
        d = []
        for item in data:
            d.append(_model2dict(item, fields))
        data = d
    return HttpResponse(json.dumps(data, sort_keys=True, indent=4, ensure_ascii=False), content_type='application/json; charset=utf-8')


def redirect_to_json(request, data=[]):
    return response_json(data)


def unique_list(seq):
    seen = set()
    seen_add = seen.add
    return [x for x in seq if x not in seen and not seen_add(x)]
