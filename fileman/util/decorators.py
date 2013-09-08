from django.conf import settings
from django.utils.decorators import available_attrs

from fileman.util.lib import response_json

from functools import wraps


def ajax_login_required(view_func):
    @wraps(view_func, assigned=available_attrs(view_func))
    def wrap(request, *args, **kwargs):
        if request.user.is_authenticated():
            return view_func(request, *args, **kwargs)
        return response_json([])
    return wrap
