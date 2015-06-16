from flask import Flask
from flask import Response
from flask import request, abort
from flask.ext.httpauth import HTTPDigestAuth

import json
import logging
from functools import wraps

import util

logger = logging.getLogger(__name__)
mainframe = None
disable_auth = False

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret key'
auth = HTTPDigestAuth()

users = {
    "admin": "admin"
}


def _dump(obj):
    return json.dumps(obj, cls=util.MessageJSONEncoder)


def authenticate(func):
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        if not disable_auth:
            return auth.login_required(func)(*args, **kwargs)
        else:
            return func(*args, **kwargs)

    return func_wrapper


@auth.get_password
def _get_pw(username):
    if username in users:
        return users.get(username)
    return None


@app.route('/messages/all', methods=['GET'])
@authenticate
def get_all_messages():
    msglist = mainframe.backstore.get_all_data()
    resp = Response(_dump(msglist), mimetype="application/json")
    return resp


@app.route('/messages/get/<mid>', methods=['GET'])
@authenticate
def get_message(mid):
    resp = Response(_dump(mainframe.backstore.get(mid)), mimetype="application/json")
    return resp


@app.route('/messages/add', methods=['POST'])
@authenticate
def add_message():
    """ returns created message with the (optionally generated) message id set """
    try:
        msg = util.MessageJSONDecoder().decode(request.get_json())
        mainframe.backstore.add(msg)
        resp = Response(_dump(msg), mimetype="application/json")
        return resp
    except Exception as e:
        logger.warn("/messages/add failed", exc_info=True)
        return abort(400)


@app.route('/messages/update', methods=['POST'])
@authenticate
def update_message():
    return


@app.route('/messages/setasread', methods=['POST'])
@authenticate
def set_multiple_messages_as_read():
    try:
        json = request.get_json()

        if json["ids"] is None:
            raise Exception("no ids submitted")
    except Exception as e:
        logger.error("corrupted request data", exc_info=True)
        return abort(400)

    for id in json["ids"]:

        try:
            mainframe.backstore.update_status(id, util.Status.read)
        except LookupError as e:
            logger.info("messages/setasread message not found [{}]".format(id))
            continue

    return Response()


