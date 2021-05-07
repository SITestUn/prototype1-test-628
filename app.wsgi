#!/usr/bin/python

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

def application(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/plain')])
    message = 'It works!\n'
    version = 'Python %s\n' % sys.version.split()[0]
    response = '\n'.join([message, version])
    return [response.encode()]


"""
activate_this = 'var/http/users/staff/sluca/dev/FLASK003_ProtoWebserviceUN/venv/bin/activate'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate))

import sys
sys.path.insert(0, '/var/http/users/staff/sluca/dev/FLASK003_ProtoWebserviceUN')
from FLASK003_ProtoWebserviceUN import app as application
"""

"""
import sys
sys.path.insert(0,"/var/http/users/staff/sluca/dev/FLASK003_ProtoWebserviceUN/")
import __init__ as application
"""