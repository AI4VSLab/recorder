# AI4VS App to collect data from the expert

import threading
import pyaudio
from flask import Flask, request, render_template, jsonify, url_for
from experiment import Experiment
import wave
import audioop
import os
import subprocess

app = Flask(__name__)
exp = Experiment()

class SharedState:
    def __init__(self):
        self.current_endpoint = '/'

# Create an instance of the shared state
shared_state = SharedState()

# This dictionary represents the shared state for recording
recording_state = {'is_recording': False, 'thread': None}

def record_audio(image_id,exp_id):
    # Define the basic parameters for recording
    CHUNK = 1024  # Number of audio frames per buffer
    FORMAT = pyaudio.paInt16  # Audio format (16-bit integer)
    CHANNELS = 1  # Number of audio channels
    RATE = 44100  # Sampling rate (samples per second)

    # make folder if doesn't exists
    if not os.path.exists(f'audio/${exp_id}'): os.makedirs(f'audio/${exp_id}')

    OUTPUT_FILENAME = f"audio/${exp_id}/${image_id}_output.wav"  # Output file name

    # Initialize PyAudio
    p = pyaudio.PyAudio()

    # Open the stream for recording
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("Recording started...")

    print(f"Recording audio for the {shared_state.current_endpoint} endpoint...")
    frames = []
    while recording_state['is_recording']:
        # Your audio recording logic here
        data = stream.read(CHUNK)
        frames.append(data)
        # Check the audio level
        audio_level = audioop.rms(data, 2)  # Get the RMS of the chunk

    print("Recording stopped.")
    # Stop and close the stream
    stream.stop_stream()
    stream.close()
    p.terminate()

    # Save the recorded data as a WAV file
    wf = wave.open(OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

    # TODO: upload to google cloud bucket 
    script_path = 'push2git.sh'
    # Call the script
    result = subprocess.run([script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Output the result
    print("stdout:", result.stdout)
    print("stderr:", result.stderr)

    # TODO: call google cloud sdk using





# Define the path to the script




@app.route('/', methods=['GET', 'POST'])
def home():
    shared_state.current_endpoint = 'home'
    if request.method == 'POST':
        exp.update_last_row(request.form['text'], request.form['slider'])
        return "success"
    else:
        exp.update_empty()
        return render_template('home.html')

@app.route('/image/<int:image_id>', methods=['GET', 'POST'])
def image_page(image_id):
    # Start recording when this page is accessed
    if not recording_state['is_recording']:
        recording_state['is_recording'] = True
        recording_thread = threading.Thread(target=record_audio(image_id,exp.exp_id))
        recording_thread.start()
        recording_state['thread'] = recording_thread

    shared_state.current_endpoint = f'image/{image_id}'
    if request.method == 'POST':
        exp.update_last_row(request.form['text'], request.form['slider'])
        return "success"
    else:
        exp.update_empty()
        image_url = url_for('static', filename='images/' + str(image_id) + '.png')
        return render_template('image_page.html', image_id=image_id, image_url=image_url)

@app.route('/controller', methods=['GET'])
def controller():
    # Stop recording when this page is accessed
    if recording_state['is_recording']:
        recording_state['is_recording'] = False
        recording_state['thread'].join()  # Wait for the thread to finish

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
    app.run(host='0.0.0.0', port=5500, debug=True)
