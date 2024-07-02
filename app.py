# AI4VS App to collect data from the expert

# EXPERIMENT PARAMETER ENTER BEFORE: CHOOSE WET NUMBER/NORMAL NUMBER, SELECTS IMAGE #N, #N+1, ...
import random
amd_number = 100
normal_number = 80

image_list = ['w3','w5','w7','w2'] + ['w' + str(i) for i in range(amd_number, amd_number+5)] + \
    ['n1','n2','n3','n5','n6'] + ['n' + str(i) for i in range(normal_number, normal_number+5)]

k=0
random.shuffle(image_list)
image_list.insert(0, 'w1')
print(image_list)
# choose wet number

######
import threading
import pyaudio
from flask import Flask, request, render_template, jsonify, url_for
from experiment import Experiment
import wave
import audioop
import os
import subprocess
import numpy as np

app = Flask(__name__)
exp = Experiment()

class SharedState:
    def __init__(self):
        self.current_endpoint = '/'

def get_image_list():
    return image_list


# Create an instance of the shared state
shared_state = SharedState()

# This dictionary represents the shared state for recording
recording_state = {'is_recording': False, 'thread': None}

def list_devices():
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    num_devices = info.get('deviceCount')
    # List all devices with their corresponding index
    for i in range(0, num_devices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            print("Input Device id ", i, " - ", p.get_device_info_by_host_api_device_index(0, i).get('name'))
    p.terminate()

def record_audio_legacy(image_id,exp_id):
    # Define the basic parameters for recording
    CHUNK = 1024  # Number of audio frames per buffer
    FORMAT = pyaudio.paInt16  # Audio format (16-bit integer)
    CHANNELS = 1  # Number of audio channels
    RATE = 44100  # Sampling rate (samples per second)

    # make folder if doesn't exists
    if not os.path.exists(f'audio/{exp_id}'): os.makedirs(f'audio/{exp_id}')

    OUTPUT_FILENAME = f"audio/{exp_id}/{image_id}_output.wav"  # Output file name

    # Initialize PyAudio
    p = pyaudio.PyAudio()

    # Open the stream for recording
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print(f"Recording started for image {image_id}...")

    print(f"Recording audio for the {shared_state.current_endpoint} endpoint...")
    frames = []
    while recording_state['is_recording']:
        # Your audio recording logic here
        data = stream.read(CHUNK)
        data = adjust_volume(data, 2)
        frames.append(data)
        # Check the audio level
        audio_level = audioop.rms(data, 2)  # Get the RMS of the chunk

    print(f"Recording stopped for {image_id}.")
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
    
    
    #result = subprocess.run([script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Output the result
    #print("stdout:", result.stdout)
    #print("stderr:", result.stderr)
    
    # TODO: call google cloud sdk using


def adjust_volume(data, factor):
    audio_array = np.frombuffer(data, dtype=np.int16)
    adjusted_audio = audio_array.copy()
    adjusted_audio *= factor
    adjusted_audio = np.clip(adjusted_audio, -32768, 32767)
    return adjusted_audio.astype(np.int16).tobytes()


def record_audio(image_id, exp_id, input_device_index=None):
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    if not os.path.exists(f'audio/{exp_id}'):
        os.makedirs(f'audio/{exp_id}')
    OUTPUT_FILENAME = f"audio/{exp_id}/{image_id}_output.wav"

    p = pyaudio.PyAudio()

    # If no specific device is provided, use the default input device
    if input_device_index is None:
        input_device_index = p.get_default_input_device_info()['index']

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK,
                    input_device_index=input_device_index)

    print(f"Recording started for image {image_id}...")

    print(f"Recording audio for the {shared_state.current_endpoint} endpoint...")
    frames = []
    while recording_state['is_recording']:
        # Your audio recording logic here
        data = stream.read(CHUNK)
        frames.append(data)
        # Check the audio level
        audio_level = audioop.rms(data, 2)  # Get the RMS of the chunk

    print(f"Recording stopped for {image_id}.")
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
    
    
    #result = subprocess.run([script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Output the result
    #print("stdout:", result.stdout)
    #print("stderr:", result.stderr)
    
    # TODO: call google cloud sdk using





def start_recording(image_id):
    '''
    note: image_id is current cound
    
    '''

    recording_state['is_recording'] = True
    recording_thread = threading.Thread(target=record_audio_legacy, args=(image_id,exp.exp_id))
    recording_state['thread'] = recording_thread
    recording_thread.start()

def stop_recording():
    recording_state['is_recording'] = False
    recording_state['thread'].join()  # Wait for the thread to finish


@app.route('/', methods=['GET', 'POST'])
def home():
    shared_state.current_endpoint = 'home'
    if request.method == 'POST':
        exp.update_last_row(request.form['text'], request.form['slider'])
        return "success"
    else:
        exp.update_empty()

        print("curr count from"+str(exp.cur_count-1)+"to"+ str(exp.cur_count))

        return render_template('home.html')

@app.route('/image/pre<patient_id>', methods=['GET', 'POST'])
def all_images_page(patient_id):
    shared_state.current_endpoint = f'/image/{patient_id}'
    if request.method == "GET":
        if not recording_state['is_recording']:  
                start_recording(exp.cur_count)
                print(exp.cur_count)

        #exp.update_empty()
        print("curr count from"+str(exp.cur_count-1)+"to"+ str(exp.cur_count))

        image_urls = []
        for i in range(1, 6):
            image_url = url_for('static', filename='amd/' + str(patient_id) + '_' + str(i) + '.png')
            image_urls.append(image_url)
        return render_template('pre_image_page.html', patient_id=patient_id, image_urls=image_urls)
    else: #post (button click)
        pass

@app.route('/image/exp<patient_id>_<j>', methods=['GET', 'POST'])
def one_image_page(patient_id,j):
    '''
    image_urls = []
    for j in range(1, 6):
        image_url = url_for('static', filename='images/' + str(patient_id) + '_' + str(j) + '.png')
        image_urls.append(image_url)
    print(image_urls)
    print(i)
    return render_template('image.html', patient_id = patient_id, image_urls = image_urls, i=int(i))
    '''
    shared_state.current_endpoint = f'/image/{patient_id}_{j}'
    image_urls = []
    print("server side "+ j)
    for i in range(1, 6):
        image_url = url_for('static', filename='amd/' + str(patient_id) + '_' + str(i) + '.png')
        image_urls.append(image_url)

    if request.method == "GET":
        #exp.update_empty()
        print(patient_id)
        print(j)
        return render_template('image.html', patient_id=patient_id, image_urls=image_urls, j=(int(j)-1), )
    else: #post (button click)
        pass


@app.route('/image/<patient_id>', methods=['GET', 'POST'])
def image_page(patient_id):
    shared_state.current_endpoint = f'/image/{patient_id}'
    if (patient_id == 'tutorial'):
        next_patient_id = 'start'
    elif (image_list.index(patient_id)+1 == 20):
        next_patient_id = ''
    else:
        next_patient_id = image_list[image_list.index(patient_id)+1]

    if request.method == 'POST':
        print('submit clicked!')
        
        # Stop recording when this page is accessed
        if recording_state['is_recording']:
            stop_recording()

        if exp.cur_count < exp.tot_count: 
            start_recording(exp.cur_count)
            print(exp.cur_count)

        else:
            print('We are done with the experiment :)')
        
        exp.update_last_row(request.form['text'], request.form['slider'])
        return "success"
    else:

        # Start recording when this page is accessed
        if not recording_state['is_recording']:  
            start_recording(exp.cur_count)
            print(exp.cur_count)


        exp.update_empty()
        print("curr count from"+str(exp.cur_count-1)+"to"+ str(exp.cur_count))

        image_urls = []
        for i in range(1, 6):
            image_url = url_for('static', filename='amd/' + str(patient_id) + '_' + str(i) + '.png')
            image_urls.append(image_url)
        return render_template('image_page.html', patient_id=patient_id, image_urls=image_urls, next_patient_id= next_patient_id)
    


@app.route('/controller', methods=['GET'])
def controller():
    return render_template('control.html')

@app.route('/start_exp')
def start_page():
    shared_state.current_endpoint = f'start_exp'
    return render_template('start.html')


@app.route('/start_action', methods=['POST'])
def start_action():
    # Put your start action code here
    print(exp.cur_count)
    start_recording(exp.cur_count)
    # Return a JSON response
    return jsonify(status="Action initiated successfully")


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

#@app.route('/tutorial', methods=['POST', 'GET'])

if __name__ == '__main__':
    print("hi")
    app.run(host='0.0.0.0', port=5500, debug=True)

