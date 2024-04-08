# AI4VS App to collect data from the expert

# lsof -i tcp:5500
# kill -9   24579 

import threading
import pyaudio
from flask import Flask, request, render_template, jsonify, url_for
from experiment import Experiment
import wave
import audioop


app = Flask(__name__)
exp = Experiment()

class SharedState:
    def __init__(self):
        self.current_endpoint = '/'

# Create an instance of the shared state
shared_state = SharedState()


@app.route('/', methods=['GET', 'POST'])
def home():
    shared_state.current_endpoint = 'home'
    if request.method == 'POST':
        # Update the last row with the form data
        exp.update_last_row(request.form['text'], request.form['slider'])
        return "success"
    else:
        # Insert empty row as soon as page is called incase they dont submit anything
        exp.update_empty()
        return render_template('home.html')
    
# ZEISS RECORDER - IMAGES & TEXT INPUT ROUTE
@app.route('/image/<int:image_id>', methods=['GET', 'POST'])
def image_page(image_id):
    
    shared_state.current_endpoint = f'image/{image_id}'

    if request.method == 'POST':
        # Update the last row with the form data
        exp.update_last_row(request.form['text'], request.form['slider'])
        return "success"
    else:
        # Insert empty row as soon as page is called incase they dont submit anything
        exp.update_empty()
        image_url = url_for('static', filename='images/' + str(image_id) + '.png')
        return render_template('image_page.html', image_id=image_id, image_url=image_url)

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


def record_audio(shared_state):
    '''
    save l
    
    '''
        
        # 
    # Define the basic parameters for recording
    CHUNK = 1024  # Number of audio frames per buffer
    FORMAT = pyaudio.paInt16  # Audio format (16-bit integer)
    CHANNELS = 1  # Number of audio channels
    RATE = 44100  # Sampling rate (samples per second)
    OUTPUT_FILENAME = "output.wav"  # Output file name
    THRESHOLD = 500  # Threshold for audio level (example condition)

    # Initialize PyAudio
    p = pyaudio.PyAudio()

    # Open the stream for recording
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("Recording...")

    frames = []
    while True:
        if 'image' not in shared_state.current_endpoint: break
        print(f"Recording audio for the {shared_state.current_endpoint} endpoint...")
        data = stream.read(CHUNK)
        frames.append(data)

        # Check the audio level
        audio_level = audioop.rms(data, 2)  # Get the RMS of the chunk
        if audio_level < THRESHOLD:
            print("Audio level below threshold, stopping.")
            break

    print("Finished recording.")
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

    # upload to google cloud bucket 

    # call google cloud sdk using 



def run_flask_app():
    app.run(host='0.0.0.0', port=5500, debug=True)

# Create and start the threads
audio_thread = threading.Thread(target=record_audio, args=(shared_state,))
flask_thread = threading.Thread(target=run_flask_app)

audio_thread.start()
flask_thread.start()

# Wait for the threads to complete (in a real application, you might handle this differently)
audio_thread.join()
flask_thread.join()
