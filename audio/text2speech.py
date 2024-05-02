import os
import json
from subprocess import Popen, PIPE
import pandas as pd
from google.cloud import speech
import sys

from google.cloud import storage

def delete_flac_files_in_folder(folder_path):
    # Iterate over all files in the folder
    for file_name in os.listdir(folder_path):
        # Check if the file has a .flac extension
        if file_name.endswith('.flac'):
            # Construct the full file path
            file_path = os.path.join(folder_path, file_name)
            try:
                # Attempt to delete the file
                os.remove(file_path)
                print(f"Deleted {file_path}")
            except OSError as e:
                # Handle file deletion errors
                print(f"Error deleting {file_path}: {e}")

def delete_flac_files_in_bucket(bucket_name):
    # Initialize GCS client
    client = storage.Client()

    # Get bucket
    bucket = client.get_bucket(bucket_name)

    # List blobs (objects) in the bucket
    blobs = bucket.list_blobs()

    # Iterate through the blobs and delete FLAC files
    for blob in blobs:
        # Check if the blob is a FLAC file
        if blob.name.endswith('.flac'):
            # Delete the FLAC file
            blob.delete()
            print(f"Deleted {blob.name}")

def convert_wav_to_flac(wav_file):
    import tempfile
    # download from bucket first

    # make a temp file 
    _, temp_wav_path = tempfile.mkstemp(suffix='.wav')

    
    # Download the file to a temporary file
    wav_file.download_to_filename(temp_wav_path)

    print('\n'*5)
    
    

    #flac_file = os.path.splitext(wav_file.name)[0] + ".flac"
    flac_file = wav_file.name.split('/')[-1].removesuffix('.wav') + ".flac"
    print('wav_file', wav_file)
    print('temp_wav_path', temp_wav_path)
    print('flac_file', flac_file)

    print('\n'*5)

    '''
    command = f"ffmpeg -i {temp_wav_path} -ar 44100 {flac_file}"
    print(command)
    process = Popen(command.split(), stdout=PIPE, stderr=PIPE)
    output, error = process.communicate()
    print("output")
    '''
    print()

    return flac_file if os.path.exists(flac_file) else None

def upload_to_bucket(bucket_name, local_file_path, destination_blob_name):
    # Initialize GCS client
    client = storage.Client()

    # Get bucket
    bucket = client.get_bucket(bucket_name)

    # Upload file to GCS
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(local_file_path)

def convert_and_upload_files_in_folder(bucket_name, folder_name, wav_file):
    '''
    @params:
        bucket_name: str
        folder_name: str
        wav_file: blob object
    '''
    print('\n'*5)
    print('convert_and_upload_files_in_folder wav_file', wav_file)
    print('\n'*5)


    flac_file = convert_wav_to_flac(wav_file)
    if flac_file:
        # Upload FLAC file to the bucket
        destination_blob_name = os.path.join(folder_name, os.path.basename(flac_file))
        upload_to_bucket(bucket_name, flac_file, destination_blob_name)
        print(f"Uploaded {flac_file} to {destination_blob_name}")
        # return os.path.join(folder_name, flac_file)
        return flac_file
    else:
        print(f"Failed to convert {wav_file} to FLAC")
        return None


def list_files_in_folder(bucket_name, folder_name):
    # Initialize GCS client
    client = storage.Client()

    # Get bucket
    bucket = client.get_bucket(bucket_name)

    # List blobs (files) in the specified folder
    blobs = bucket.list_blobs(prefix=folder_name)

    return blobs

def json_csv(result, file_name, alt_num): 

    alternative = result.alternatives[0]
    result_timestamps_string = ""
    for word_info in alternative.words:
        word = word_info.word
        start_time = word_info.start_time
        end_time = word_info.end_time
        timestamp_info = f"Word: {word}, start_time: {start_time.total_seconds()}, end_time: {end_time.total_seconds()}\n"
        result_timestamps_string = result_timestamps_string + timestamp_info
    file_name = file_name.name + "_" + "alternative" + "_" + str(alt_num)
    df_iter = pd.DataFrame({'File': [file_name], 'Transcript': [alternative.transcript], "Confidence": [alternative.confidence], "TimeStamps" : [result_timestamps_string]})

    return df_iter



def recognize_audio(file_path):
   
    # with open(file_path, "rb") as audio_file:
    #     file_content = audio_file.read()

    print('\n'*5)
    print('file_path 2 recg', file_path)
    print('\n'*5)


    client = speech.SpeechClient()


    # audio = speech.RecognitionAudio(content=file_content)
    audio = {"uri": file_path}

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.FLAC,
        sample_rate_hertz=44100,
        language_code="en-US",
        enable_word_time_offsets=True,
    )

    operation = client.long_running_recognize(config=config, audio=audio)

    print("Waiting for operation to complete...")
    result = operation.result(timeout=100000)

    print(result)

    return result

def main():
    '''
    Usage: 
        argument 1: folder name
        argument 2: bucket name
    
    '''
    arguments = sys.argv[1:]
    folder_path = arguments[0]
    bucket_name = arguments[1]
    print(f'We have folder_path: {folder_path}, bucket_name:{bucket_name} ')

    output_file = str(folder_path) + "_output.csv"

    df_all = pd.DataFrame(columns=['File', 'Transcript'])

    wav_files = list_files_in_folder(bucket_name, folder_path) # audio_recordings_tobii
    
    
    delete_flac_files_in_bucket(bucket_name)

    # delete_flac_files_in_folder used for local storage, ie within the console instance or on a computer locally
    # delete_flac_files_in_folder(folder_path)

    # wav_file is a Blob object
    for wav_file in wav_files:
        

        if wav_file.name.endswith(".wav"):
            print(wav_file)
            # gcloud takes flac files, need to convert from .wav to .flac using ffmepg. 
            # but ffmepg needs to run on local files (or we can mount), this is the easiet way rn
            flac_file = convert_and_upload_files_in_folder(bucket_name, folder_path, wav_file)
            print(flac_file)
            gci_file_path = f"gs://{bucket_name}/{flac_file}"
            print(gci_file_path)
            recognition_result = recognize_audio(gci_file_path)
            alt_num = 0
            try:
                for result in recognition_result.results: 
                    df_iter = json_csv(result, wav_file, alt_num)                        
                    df_all = pd.concat([df_all, df_iter], ignore_index=True)
                    alt_num+=1
            except json.JSONDecodeError:
                print("Error: Unable to decode JSON output")
    delete_flac_files_in_bucket(bucket_name)   
    df_all.to_csv(output_file, index=False)


if __name__ == "__main__":
    main()