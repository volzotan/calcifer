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