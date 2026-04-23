# AI4VS App to collect data from the expert

# lsof -i tcp:5500
# kill -9   24579 

from flask import Flask, request, render_template, jsonify, session
from experiment import Experiment
import json
import os

responses = []

RESPONSES_PATH = "saves/responses.json"

CASES = [
    {
        "id": 1,
        "images": [
            "https://placehold.co/400x300/f5f0cc/333?text=Image+1",
            "https://placehold.co/400x300/f5f0cc/333?text=Image+2",
            "https://placehold.co/400x300/f5f0cc/333?text=Image+3",
            "https://placehold.co/400x300/f5f0cc/333?text=Image+4",
            "https://placehold.co/400x300/f5f0cc/333?text=Image+5",
        ],
    },
    {
        "id": 2,
        "images": [
            "https://placehold.co/400x300/f5f0cc/333?text=Image+1",
            "https://placehold.co/400x300/f5f0cc/333?text=Image+2",
            "https://placehold.co/400x300/f5f0cc/333?text=Image+3",
            "https://placehold.co/400x300/f5f0cc/333?text=Image+4",
            "https://placehold.co/400x300/f5f0cc/333?text=Image+5",
        ],
    },
]

app = Flask(__name__)
app.secret_key = "ai4vs-secret-key"
exp = Experiment()

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
    )

@app.route('/get_status', methods=['GET'])
def get_experiment_status():
    current, total, exp_id, df = exp.get_status()
    return jsonify({'current': current, 'total': total, 'exp_id': exp_id, 'df': df, 'active': exp.ACTIVE, 'exp_name': exp.exp_name})

@app.route("/submit", methods=["POST"])
def submit():
    idx = session.get("case_index", 0)
    data = request.get_json() or {}

    record = {
        "case_id":   CASES[idx]["id"] if idx < len(CASES) else None,
        "diagnosis": data.get("diagnosis", ""),
        "biomarkers": data.get("biomarkers", ""),
    }
    responses.append(record)

    os.makedirs("saves", exist_ok=True)
    if os.path.exists(RESPONSES_PATH):
        with open(RESPONSES_PATH, "r") as f:
            saved = json.load(f)
            if not isinstance(saved, list):
                saved = [saved]
    else:
        saved = []

    saved.append(record)

    with open(RESPONSES_PATH, "w") as f:
        json.dump(saved, f, indent=2)

    session["case_index"] = idx + 1
    return jsonify({"status": "ok", "saved": True})

@app.route('/reset', methods=['POST'])
def reset():
    session.pop("case_index", None)
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
