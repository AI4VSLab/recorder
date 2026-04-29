# AI4VS App to collect data from the expert

# lsof -i tcp:5500
# kill -9   24579 

from flask import Flask, request, render_template, jsonify, session
from experiment import Experiment
import json
import os

responses = []

RESPONSES_PATH = "saves/responses.json"
TOTAL_CASES = int(os.environ.get("AI4VS_TOTAL_CASES", "20"))
CASES = [{"id": idx} for idx in range(1, TOTAL_CASES + 1)]

BIOMARKER_OPTIONS = [
    "Increased cup-to-disc ratio",
    "Vertical cupping",
    "Neuroretinal rim thinning",
    "ISNT rule violation",
    "RNFL thinning",
    "Disc hemorrhage",
    "Bayonetting of vessels",
    "Nasalization of vessels",
    "Peripapillary atrophy",
    "Asymmetry between eyes",
    "Optic disc pallor",
    "Tilted disc",
    "Vessel baring",
    "Other",
]

DIAGNOSIS_OPTIONS = [
    "Normal / no glaucoma",
    "Glaucoma suspect",
    "Glaucoma",
    "Primary open-angle glaucoma",
    "Normal-tension glaucoma",
    "Angle-closure glaucoma",
    "Advanced glaucoma",
    "Other",
]

app = Flask(__name__)
app.secret_key = "ai4vs-secret-key"
exp = Experiment()


def load_saved_responses():
    if not os.path.exists(RESPONSES_PATH):
        return []

    with open(RESPONSES_PATH, "r") as f:
        saved = json.load(f)
        if isinstance(saved, list):
            return saved
        return [saved]


def persist_case_response(idx, data):
    record = {
        "case_id": CASES[idx]["id"] if idx < len(CASES) else None,
        "diagnoses": data.get("diagnoses", []),
        "diagnosis_other": data.get("diagnosis_other", ""),
        "biomarkers": data.get("biomarkers", []),
        "biomarker_other": data.get("biomarker_other", ""),
    }

    responses.append(record)
    os.makedirs("saves", exist_ok=True)
    saved = load_saved_responses()
    saved.append(record)

    with open(RESPONSES_PATH, "w") as f:
        json.dump(saved, f, indent=2)

    return record

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # Update the last row with the form data
        exp.update_last_row(request.form['text'], request.form['slider'])
        return "success"
    else:
        # Insert empty row as soon as page is called incase they dont submit anything
        exp.update_empty()
        return render_template('home.html')

@app.route('/controller', methods=['GET'])
def controller():
    return render_template('control.html')

@app.route("/images")
def images():
    idx = session.get("case_index", 0)
    if idx >= len(CASES):
        return render_template("done.html", total=len(CASES))
    case = CASES[idx]
    return render_template(
        "images.html",
        case=case,
        current=idx + 1,
        total=len(CASES),
        biomarker_options=BIOMARKER_OPTIONS,
        diagnosis_options=DIAGNOSIS_OPTIONS,
    )

@app.route('/get_status', methods=['GET'])
def get_experiment_status():
    current, total, exp_id, df = exp.get_status()
    return jsonify({'current': current, 'total': total, 'exp_id': exp_id, 'df': df, 'active': exp.ACTIVE, 'exp_name': exp.exp_name})

@app.route("/submit", methods=["POST"])
def submit():
    idx = session.get("case_index", 0)
    data = request.get_json() or {}
    persist_case_response(idx, data)
    session["case_index"] = min(idx + 1, len(CASES))
    session["last_saved_case_index"] = idx
    return jsonify({"status": "ok", "saved": True, "next": session["case_index"]})


@app.route("/autosave", methods=["POST"])
def autosave():
    idx = session.get("case_index", 0)
    if idx >= len(CASES):
        return ("", 204)

    if session.get("last_saved_case_index") == idx:
        return ("", 204)

    data = request.get_json(silent=True)
    if data is None and request.data:
        try:
            data = json.loads(request.data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = {}
    if data is None:
        data = {}

    persist_case_response(idx, data)
    session["case_index"] = min(idx + 1, len(CASES))
    session["last_saved_case_index"] = idx
    return ("", 204)

@app.route('/reset', methods=['POST'])
def reset():
    session.pop("case_index", None)
    session.pop("last_saved_case_index", None)
    return "success"

@app.route('/stop', methods=['POST'])
def stop_experiment():
    exp.end()
    return "success"

@app.route('/start', methods=['POST'])
def start_experiment():
    exp.start(request.form['exp_name'], request.form['exp_count'])
    return "success"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5500, debug= True)
