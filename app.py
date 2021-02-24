# app.py
import json
import joblib
import os
import numpy as np
import pandas as pd

from flask import Flask, request, send_file
from pathlib import Path
from scipy.spatial import distance
from sklearn.tree import export_text

app = Flask(__name__)

with open(os.path.join('models', 'ansible', 'metadata.json')) as f:
    ansible_models_metadata = json.load(f)

with open(os.path.join('models', 'tosca', 'metadata.json')) as f:
    tosca_models_metadata = json.load(f)


@app.route('/models/', methods=['GET'])
def models():
    """ Get a defect prediction model from the most similar project.
    The client's project is compared with all the projects for which a defect prediction model exists for the language
    requested.
    Projects similarity is computed as the cosine similarity between the client's project metrics vector and any of the
    available projects'.

    Return
    ------
    response: json/file
        A json response with the project id to use in future calls of /prediction, if return_model = False.
        Otherwise, the model.
    """

    # Retrieve the name from url parameter
    language = request.args.get("language", None)
    return_model = request.args.get("return_model", False)

    client_project_metrics = [
        float(request.args.get("comments_ratio", 0)),
        float(request.args.get("commit_frequency", 0)),
        float(request.args.get("core_contributors", 0)),
        int(request.args.get("has_ci", False)),
        int(request.args.get("has_license", False)),
        float(request.args.get("iac_ratio", 0)),
        float(request.args.get("issue_frequency", 0)),
        float(request.args.get("repository_size", 0))
    ]

    response = {}

    if language == 'ansible':
        metadata = ansible_models_metadata
    elif language == 'tosca':
        metadata = tosca_models_metadata
    else:
        response["ERROR"] = "Set a valid language."
        return response

    path_to_model = None
    most_similar_score = 0

    for project in metadata:
        project_metrics = [
            project["comments_ratio"],
            project["commit_frequency"],
            project["core_contributors"],
            int(project["has_ci"]),
            int(project["has_license"]),
            project["iac_ratio"],
            project["issue_frequency"],
            project["repository_size"]
        ]

        sim = 1 - distance.cosine(project_metrics, client_project_metrics)
        if sim > most_similar_score:
            
            response['model_id'] = project['id']
            response['similarity'] = sim
            response['models'] = []
            
            most_similar_score = sim

            for defect_type in ('conditional', 'configuration_data', 'service', 'general'):
                path_to_model = project['models'].get(defect_type)

                if not path_to_model:
                    continue

                path_to_model = str(Path(path_to_model))
                model = joblib.load(path_to_model, mmap_mode='r')
                
                response['models'].append(
                    {
                      'type': defect_type,
                      'rules': export_text(model['estimator'].named_steps['classification'], feature_names=model['selected_features'])
                    })


    return send_file(path_to_model, as_attachment=True) if return_model else response


@app.route('/predictions/', methods=['GET'])
def predict():
    response = {}

    language = None
    model_id = 0
    metrics = {}

    for k, v in dict(request.args).items():
        if k == 'language':
            language = str(v).lower()
        elif k == 'model_id':
            model_id = int(v)
        else:
            metrics[k] = float(v)

    unseen_data = pd.DataFrame(metrics, index=[0])

    if language == 'ansible':
        models_metadata = ansible_models_metadata
    elif language == 'tosca':
        models_metadata = tosca_models_metadata
    else:
        response["ERROR"] = 'Language not supported'
        return response

    i = 0
    while i < len(models_metadata) and models_metadata[i]['id'] != model_id:
        i += 1

    if  i == len(models_metadata):
        response["ERROR"] = "Model not found."
        return response

    response['failure_prone'] = False

    for defect_type in ('conditional', 'configuration_data', 'service', 'general'):
        path_to_model = models_metadata[i]['models'].get(defect_type)
       
        if not path_to_model:
            continue     

        path_to_model = str(Path(path_to_model))

        model = joblib.load(path_to_model, mmap_mode='r')
        tree_clf = model['estimator'].named_steps['classification']
        unseen_data_local = unseen_data

        for feature in model['selected_features']:
            if feature not in unseen_data_local.columns:
                unseen_data_local[feature] = 0

        # Reduce unseen_data_local to the same subset of features
        unseen_data_local = unseen_data_local[np.intersect1d(unseen_data_local.columns, model['selected_features'])]

        features_name = unseen_data_local.columns

        # Perform pre-process if any
        if model['estimator'].named_steps['normalization']:
            unseen_data_local = pd.DataFrame(model['estimator'].named_steps['normalization'].transform(unseen_data_local), columns=features_name)

        failure_prone = bool(tree_clf.predict(unseen_data_local)[0])

        if failure_prone:

            response['failure_prone'] = True

            decision = []
            decision_path = tree_clf.decision_path(unseen_data_local)
            level_length = len(decision_path.indices)
            i = 1
            for node_id in decision_path.indices:
                # Ignore last level because it is the last node
                # without decision criteria or rule
                if i < level_length:
                    col_name = unseen_data_local.columns[tree_clf.tree_.feature[node_id]]
                    threshold_value = round(tree_clf.tree_.threshold[node_id], 2)
                    original_value = metrics.get(col_name, 0)

                    # Inverse normalize threshold to make it more comprehensible to the final user
                    normalized_value = unseen_data_local[col_name].values[0] if unseen_data_local[col_name].values[0] > 0 else 1
                    threshold_value *= original_value/normalized_value

                    decision.append((col_name, '<=' if original_value <= threshold_value else '>', threshold_value))

                i += 1

            response.setdefault('defects', []).append({'type': defect_type, 'decision': decision})

    return response


# A welcome message to test our server
@app.route('/')
def index():
    return "<h1>Welcome to our server !!</h1>"


if __name__ == '__main__':
    # Threaded option to enable multiple instances for multiple user access support
    app.run(threaded=True, port=5000)
