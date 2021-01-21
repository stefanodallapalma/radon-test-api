# app.py
import os
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)


@app.route('/models/', methods=['GET'])
def models():
    # Retrieve the name from url parameter
    language = request.args.get("language", None)
    response = {}

    # Check if user sent a name at all
    if not language:
        response["ERROR"] = "No language found, please send a language."
        return response
    elif language == 'ansible':
        model = os.path.join(os.path.join('models', 'ansible', 'ansible__workshops.joblib'))
    elif language == 'tosca':
        model = os.path.join(os.path.join('models', 'tosca', 'radondp_model_tosca.joblib'))
    else:
        response["ERROR"] = "language not supported."
        return response

    return send_file(model, as_attachment=True)


# A welcome message to test our server
@app.route('/')
def index():
    return "<h1>Welcome to our server !!</h1>"


if __name__ == '__main__':
    # Threaded option to enable multiple instances for multiple user access support
    app.run(threaded=True, port=5000)
