# AI4VS App to collect data from the expert

# lsof -i tcp:5500
# kill -9   24579 

from flask import Flask, request, render_template, jsonify, session
from experiment import Experiment

responses = []

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
    data = request.get_json()
    responses.append(
        {
            "case_id": CASES[idx]["id"] if idx < len(CASES) else None,
            "diagnosis": data.get("diagnosis", ""),
            "time_remaining": data.get("time_remaining", 0),
        }
    )
    session["case_index"] = idx + 1
    next_idx = idx + 1
    return jsonify(
        {
            "status": "ok",
            "done": next_idx >= len(CASES),
            "next": next_idx + 1,
            "total": len(CASES),
        }
    )

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