from flask import Flask
from flask import Response

import json

import util

app = Flask(__name__)
mainframe = None

def _dump(obj):
    return json.dumps(obj, cls=util.MessageJSONEncoder)

@app.route('/message', methods=['GET'])
def get_all_messages():
    msglist = mainframe.backstore.get_all_data()
    resp = Response(_dump(msglist), mimetype="application/json")
    return resp


@app.route('/message/<mid>', methods=['GET'])
def get_message(mid):
    pass


@app.route('/message', methods=['POST'])
def add_message():
    pass


@app.route('/message', methods=['PUT'])
def update_message():
    pass


