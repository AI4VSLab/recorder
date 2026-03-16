# AI4VS App to collect data from the expert

# lsof -i tcp:5500
# kill -9   24579 

from flask import Flask, request, render_template, jsonify
from experiment import Experiment

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

@app.route('/get_status', methods=['GET'])
def get_experiment_status():
    current, total, exp_id, df = exp.get_status()
    return jsonify({'current': current, 'total': total, 'exp_id': exp_id, 'df': df, 'active': exp.ACTIVE, 'exp_name': exp.exp_name})

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