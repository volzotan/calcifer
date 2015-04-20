from flask import Flask
from flask import Response

import json

app = Flask(__name__)
mainframe = None

@app.route('/message', methods=['GET'])
def get_all_messages():
    msglist = mainframe.backstore.get_all()
    resp = Response(json.dumps(msglist), mimetype="application/json")
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


