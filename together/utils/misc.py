
import ast
import json
import re

import urllib.parse
import urllib.request


def request(url, data, method, headers, timeout=3):

    if method == 'GET':
        url = f"{url}?{urllib.parse.urlencode(data)}"
        r = urllib.request.Request(url)
        for item in headers.items():
            r.add_header(*item)
        response = urllib.request.urlopen(r, timeout=timeout)
        data = response.read().decode('utf-8')
        return data

    if method == 'POST':
        data = json.dumps(data).encode('utf-8')
        request = urllib.request.Request(url, data=data, headers=headers)  # this will make the method "POST"
        response = urllib.request.urlopen(request, timeout=timeout).read()
        return response

    raise ValueError(f"Unknown HTTP method {method}")


def parse_event(event):
    query_param_string = event['rawQueryString']
    query_kwargs = dict([tuple(kwarg.split('=')) for kwarg in query_param_string.split('&')])
    method = event['requestContext']['http']['method']

    return method, query_kwargs


def eval_or_none(expression):
    """Safely evaluate a python expression including strings and None"""
    if type(expression) is not str:
        return expression
    elif not expression:
        return None
    elif expression in ('True', 'False'):
        return ast.literal_eval(expression)
    elif re.match(r'^[a-zA-Z0-9_-]+$', expression):
        return str(expression)
    else:
        return ast.literal_eval(expression)


def apply_custom_filters(qs, filters, kwargs):
    for filter_field, method in filters.items():
        assert hasattr(method, 'apply'), f"`apply` method not found on {method}"
        value = eval_or_none(kwargs.get(filter_field, None))
        if value:
            qs = method.apply(qs, value)

    return qs
