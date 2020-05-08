import os
import json
import socket
import logging
import datetime
import traceback

from flask_cors import CORS
from flask import Flask, request

from logging.config import dictConfig
from werkzeug.exceptions import HTTPException

from traceback import FrameSummary

import settings

from models.database_model import db
from blueprints import all_blueprints
from exceptions.exceptions import ServerException
from exceptions.send_alert import send_dingding_alert

logger = logging.getLogger(__name__)


class JsonEncoder(json.JSONEncoder):
    def default(self, value):
        if isinstance(value, (datetime.datetime, datetime.date)):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(value, FrameSummary):
            return str(value)

        return json.JSONEncoder.default(self, value)


def create_app():
    app = Flask(__name__)
    CORS(app, supports_credentials=True)
    init_config(app)

    app.json_encoder = JsonEncoder
    return app


def init_config(app):
    app.config["SQLALCHEMY_DATABASE_URI"] = settings.SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = settings.SQLALCHEMY_TRACK_MODIFICATIONS

    register_blueprints(app)
    app.register_error_handler(Exception, handle_exception)

    db.init_app(app)

    return


def register_blueprints(app):
    for blueprint in all_blueprints:
        app.register_blueprint(blueprint)

    return


def handle_exception(e):
    code = 500
    if isinstance(e, (HTTPException, ServerException)):
        code = e.code

    logger.exception(e)
    exc = [v for v in traceback.format_exc(limit=10).split("\n")]
    if str(code) == "500":
        send_dingding_alert(request.url, request.args, request.json, repr(e), exc)
    return {'error_code': code, 'error_msg': str(e), 'traceback': exc}, code


def init_logging():
    level = 'INFO' if settings.NAMESPACE == 'PRODUCTION' else 'DEBUG'
    dir_name = "./log/{}".format(socket.gethostname())
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'brief': {
                'format': '%(message)s'
            },
            'standard': {
                'format': '[%(asctime)s] [%(levelname)s]  [%(filename)s.%(funcName)s:%(lineno)3d]  [%(process)d::%(thread)d] %(message)s'
            }
        },
        'handlers': {
            'default': {
                'level': level,
                'formatter': 'standard',
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'filename': '{}/server.log'.format(dir_name),
                'when': 'midnight',
                'interval': 1,
                'encoding': 'utf8'
            },
            'console': {
                'level': level,
                'formatter': 'standard',
                'class': 'logging.StreamHandler'
            },
            'default_access': {
                'level': level,
                'formatter': 'brief',
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'filename': '{}/access.log'.format(dir_name),
                'when': 'midnight',
                'interval': 1,
                'encoding': 'utf8'
            },
            'console_access': {
                'level': level,
                'formatter': 'brief',
                'class': 'logging.StreamHandler'
            }
        },
        'loggers': {
            'werkzeug': {
                'handlers': ['default_access', 'console_access'],
                'level': level,
                'propagate': False
            },
            '': {
                'handlers': ['default', 'console'],
                'level': level,
                'propagate': False
            }
        }
    }

    def patch_wsgi_handler():
        """
        忽略WSGIServer log标签
        """
        from gevent.pywsgi import WSGIHandler
        logger = logging.getLogger('werkzeug')

        def log_request(self):
            logger.info(WSGIHandler.format_request(self))

        WSGIHandler.log_request = log_request

    dictConfig(config)
    patch_wsgi_handler()
