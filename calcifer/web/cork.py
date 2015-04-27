from flask import Flask
from flask import Response
from flask import request, abort

import json
import logging

import util

logger = logging.getLogger(__name__)
app = Flask(__name__)
mainframe = None


def _dump(obj):
    return json.dumps(obj, cls=util.MessageJSONEncoder)


@app.route('/messages/all', methods=['GET'])
def get_all_messages():
    msglist = mainframe.backstore.get_all_data()
    resp = Response(_dump(msglist), mimetype="application/json")
    return resp


@app.route('/messages/get/<mid>', methods=['GET'])
def get_message(mid):
    resp = Response(_dump(mainframe.backstore.get(mid)), mimetype="application/json")
    return resp


@app.route('/messages/add', methods=['POST'])
def add_message():
    """ returns created message with the message id set (if generated) """
    try:
        msg = util.MessageJSONDecoder().decode(request.get_json())
        mainframe.backstore.add(msg)
        resp = Response(_dump(msg), mimetype="application/json")
        return resp
    except Exception as e:
        logger.warn("/messages/add failed", exc_info=True)
        abort(400)


@app.route('/messages/update', methods=['POST'])
def update_message():
    pass


