# Radon-defect-prediction-endpoints

This repository provised the APIs to expose the Ansible and Tosca defect prediction models.

## Endpoints

- Get model: https://radon-test-api.herokuapp.com/models
- Predict: https://radon-test-api.herokuapp.com/predictions



### Get model
Get a pre-trained model from the most similar project.

`GET https://radon-test-api.herokuapp.com/models?parm1=value1&...&paramN=valueN`

**Example:**
`GET https://radon-test-api.herokuapp.com/models?language=ansible&repository_size=560&comments_ratio=0.03&has_license=1`

**Parameters**

| Name | Value | Default|
|------|-------|-----------|
|`language`| string | None. Choose between {ansible, tosca} |
|`return_model` | int [0: false, 1: true] | 0 | 
|`comments_ratio` | numeric | 0 |
|`commit_frequency`| numeric | 0 |
|`core_contributors`| numeric | 0 |
|`has_ci`| [0: false, 1: true] | 0 |
|`has_license`| [0: false, 1: true] | 0 |
|`iac_ratio`| numeric | 0 |
|`issue_frequency`| numeric | 0 |
|`repository_size`| numeric | 0 |

**Return**

A json containing the model id to use for calls to the `predictions/` endpoint, a list of models, and a similarity score ([0-1]) between the client's and models' project. 

```
{
    "model_id": 24242603,
    "similarity": 0.9999,
    "models": [
      {
        "type": "general"
        "rules": "|--- num_include <= 0.44\n|... "
      },
      {
        "type": "conditional"
        "rules": "... "
      },
    ]
}
```

If `return_model=true`, it returns the raw `joblib` model.
Once saved somewhere, the model can be loaded and used in Python as follows:

```python
import joblib

model = joblib.load('path/to/model.joblib', mmap_mode='r')
    
selected_features = model['selected_features']
normalizer = model['estimator'].named_steps['normalization']
tree_classifier = model['estimator'].named_steps['classification']

# selected_features can be used to reduce a new data frame to the same subset of model features
# normalizer (if not None) must be used to normalize the new data in the same fashion as model's training data
# tree_classifier can be used for predicting failure-prone script
``` 




### Predict
Predict the failure-proneness of a file represented by a set of metrics.

`GET https://radon-test-api.herokuapp.com/predictions?parm1=value1&...&paramN=valueN`

**Example:** 
`GET https://radon-test-api.herokuapp.com/predictions?language=ansible&model_id=24242603&num_names_with_vars=10&num_ignore_errors=3&num_conditions=1`

**Parameters**

| Name | Value | Default|
|------|-------|-----------|
|`language`| string | None. Choose between {ansible, tosca} |
|`model_id` | int | None. It is mandatory. Use the model_id from the `/models` endpoint | 

The remaining parameters are the Ansible or Tosca metrics that can be extracted by the script.
**See how** extract those metrics with [AnsibleMetrics](https://github.com/radon-h2020/radon-ansible-metrics) and 
[ToscaMetrics](https://github.com/radon-h2020/radon-tosca-metrics).

**Note:** Metrics are passed instead of the raw script to avoid information disclosure.

**Result**
A json file containing the prediction (i.e., `failure_prone: true/false`), and the decision that led to the prediction 
(absent if `failure_prone: false`).

```
{
  "failure_prone": true,
  "decision": [
    [
      "num_names_with_vars",
      ">",
      2.4
    ],
    [
      "num_ignore_errors",
      "<=",
      4.16
    ],
    [
      "num_conditions",
      "<=",
      17.12
    ],
    [
      "num_filters",
      "<=",
      0.0
    ]
  ]
}
```

In this example, a script has been predicted as **failure-prone** because:

num_names_with_vars > 2.4 **AND** num_ignore_errors <= 4.16 **AND** num_conditions <= 17.12 **AND** num_filters <= 0.

