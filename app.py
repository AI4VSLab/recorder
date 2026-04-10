# AI4VS App to collect data from the expert

# lsof -i tcp:5500
# kill -9   24579 

from flask import Flask, request, render_template, jsonify, session, send_file, abort, url_for
from experiment import Experiment
import json
import os

responses = []

RESPONSES_PATH = "saves/responses.json"

app = Flask(__name__)
app.secret_key = "ai4vs-secret-key"
AMD_STIMULI_TEMPLATE = os.getenv(
    "AMD_STIMULI_TEMPLATE",
    "/path/to/amd/stimuli/{slide_id}.png",
)
exp = Experiment(stimuli_template=AMD_STIMULI_TEMPLATE)

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
    recent_events = exp.get_recent_stimuli()
    case = {
        "id": recent_events[-1]["slide_id"] if recent_events else None,
        "images": [
            url_for("stimulus_image", slide_id=event["slide_id"])
            for event in recent_events
        ],
    }
    recent_count = len(case["images"])
    return render_template(
        "images.html",
        case=case,
        current=recent_count,
        total=5,
        current_slide=exp.current_stimulus_index + 1 if exp.current_stimulus_index >= 0 else 0,
        sdk_status=exp.get_tobii_status(),
    )


@app.route("/stimuli/image/<path:slide_id>", methods=["GET"])
def stimulus_image(slide_id):
    image_path = exp.resolve_stimulus_image_path(slide_id)
    if image_path.startswith("http://") or image_path.startswith("https://"):
        return jsonify({"status": "error", "message": "Remote image URLs are not supported by this route"}), 400
    if not os.path.exists(image_path):
        abort(404, description=f"Stimulus image not found: {image_path}")
    return send_file(image_path)


@app.route("/stimuli/show", methods=["POST"])
def show_stimulus():
    payload = request.get_json(silent=True) or request.form
    slide_id = payload.get("slide_id") or payload.get("stimulus_id")
    image_path = payload.get("image_path")
    metadata = payload.get("metadata")

    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {"raw": metadata}

    if not slide_id and not image_path:
        return jsonify({"status": "error", "message": "slide_id or image_path is required"}), 400

    if image_path:
        event = exp.register_stimulus_from_filepath(
            filepath=image_path,
            slide_id=slide_id,
            metadata=metadata,
            source="tobii_sdk",
        )
    else:
        event = exp.register_stimulus(
            slide_id=slide_id,
            metadata=metadata,
            source="tobii_sdk",
        )

    recent_case = exp.get_recent_stimuli_case()
    return jsonify(
        {
            "status": "ok",
            "event": event,
            "recent_images": recent_case["images"],
            "sdk_status": exp.get_tobii_status(),
        }
    )


@app.route("/stimuli/advance", methods=["POST"])
def advance_stimulus():
    try:
        event = exp.register_stimulus(source="tobii_sdk")
    except (ValueError, IndexError) as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400

    return jsonify(
        {
            "status": "ok",
            "event": event,
            "recent_images": exp.get_recent_stimulus_images(),
        }
    )


@app.route("/stimuli/recent", methods=["GET"])
def recent_stimuli():
    return jsonify(
        {
            "status": "ok",
            "recent": exp.get_recent_stimuli(),
            "sdk_status": exp.get_tobii_status(),
        }
    )

@app.route('/get_status', methods=['GET'])
def get_experiment_status():
    current, total, exp_id, df = exp.get_status()
    return jsonify({'current': current, 'total': total, 'exp_id': exp_id, 'df': df, 'active': exp.ACTIVE, 'exp_name': exp.exp_name})

@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json()
    current_stimulus = exp.get_current_stimulus()

    record = {
        "slide_id": current_stimulus["slide_id"] if current_stimulus else None,
        "image_path": current_stimulus["image_path"] if current_stimulus else None,
        "diagnosis": data.get("diagnosis", ""),
        "biomarkers": data.get("biomarkers", ""),   # comma-separated string
    }
    responses.append(record)

    # Persist to saves/responses.json — append to existing array, create if missing
    os.makedirs("saves", exist_ok=True)
    if os.path.exists(RESPONSES_PATH):
        with open(RESPONSES_PATH, "r") as f:
            saved = json.load(f)
    else:
        saved = []
    saved.append(record)
    with open(RESPONSES_PATH, "w") as f:
        json.dump(saved, f, indent=2)

    return jsonify(
        {
            "status": "ok",
            "done": False,
            "next": exp.current_stimulus_index + 2 if exp.current_stimulus_index >= 0 else 1,
            "total": max(len(exp.stimulus_ids), exp.current_stimulus_index + 1, 1),
        }
    )

@app.route('/reset', methods=['POST'])
def reset():
    session.pop("case_index", None)
    exp.reset_stimulus_history()
    return "success"

@app.route('/stop', methods=['POST'])
def stop_experiment():
    exp.end()
    return "success"

@app.route('/start', methods=['POST'])
def start_experiment():
    stimuli_template = request.form.get("stimuli_template") or AMD_STIMULI_TEMPLATE
    raw_slide_ids = request.form.get("slide_ids", "")
    exp.start(request.form['exp_name'], request.form['exp_count'], stimuli_template=stimuli_template)

    if raw_slide_ids:
        exp.set_stimulus_sequence(
            [slide_id.strip() for slide_id in raw_slide_ids.split(",") if slide_id.strip()]
        )
    return "success"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5500, debug= True)
