
import os
import json
import sys
import pandas as pd
from subprocess import Popen, PIPE
from google.cloud import storage
import requests
import subprocess
from google.oauth2 import service_account
from google.cloud import speech_v1p1beta1 as speech

# Function to delete FLAC files in a local folder
def delete_flac_files_in_folder(folder_path):
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.flac'):
            file_path = os.path.join(folder_path, file_name)
            try:
                os.remove(file_path)
                print(f"Deleted {file_path}")
            except OSError as e:
                print(f"Error deleting {file_path}: {e}")

# Function to delete FLAC files in a GCS bucket
def delete_flac_files_in_bucket(bucket_name):
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    blobs = bucket.list_blobs()
    for blob in blobs:
        if blob.name.endswith('.flac'):
            blob.delete()
            print(f"Deleted {blob.name}")

# Function to download a file from GCS
def download_file_from_gcs(bucket_name, source_blob_name, destination_file_name):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    print(destination_file_name)
    blob.download_to_filename(destination_file_name)
    print(f"Downloaded {source_blob_name} from bucket {bucket_name} to {destination_file_name}.")

# Function to convert WAV file to FLAC format
def convert_wav_to_flac(folder_path_flac, wav_file, bucket_name):
    # Construct the local WAV file path
    print(folder_path_flac, wav_file)
    # Step 1: Download the WAV file from GCS to the correct path
    download_file_from_gcs(bucket_name, wav_file, wav_file)

    # Create the output FLAC file path
    flac_file = os.path.join(folder_path_flac, os.path.splitext(os.path.basename(wav_file))[0] + ".flac")
    print(flac_file)
    input_ = "EEM_1_2024-04-30_12-59-28/5_output.wav"
    if input_ == wav_file: 
        print("EQUAL")
    # Command to convert WAV to FLAC using ffmpeg

    if os.path.exists(wav_file):
        print(f"The file exists: {wav_file}")
    else:
        print(f"File not found: {wav_file}")
    command = [
    "ffmpeg",          # The FFmpeg command
    "-i", wav_file, # Input file
    "-ar", "44100",   # Set the audio sample rate
    flac_file       # Output file
    ]

# Run the command
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print("FFmpeg output:", result.stdout)
    except subprocess.CalledProcessError as e:
        print("FFmpeg error:", e.stderr)
    print(wav_file)
    print(f"Running command: {command}")

    
    return flac_file if os.path.exists(flac_file) else None


# Function to upload a file to GCS
def upload_to_bucket(bucket_name, local_file_path, destination_blob_name):
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(local_file_path)
    print(f"Uploaded {local_file_path} to {destination_blob_name}")
    return destination_blob_name

# Function to recognize audio using Google Speech-to-Text
def recognize_audio(file_path):
    credentials = service_account.Credentials.from_service_account_file(
        "/home/sc4789/recorder/audio/ai4vslabrecordings-3897c071815b.json"
    )

    client = speech.SpeechClient(credentials=credentials)

    audio = speech.RecognitionAudio(uri=f"gs://{file_path}")
    print(audio)
    
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.FLAC,
        sample_rate_hertz=44100,
        language_code="en-US",
        enable_word_time_offsets=True
    )

    operation = client.long_running_recognize(config=config, audio=audio)
    print("Waiting for operation to complete...")
    response = operation.result(timeout=90) 

    if operation.done:
        print("Operation finished successfully.")
    else:
        print("Operation is still in progress.")

    # Check the response
    if not response.results:
        print("No results found.")
    else:
        for result in response.results:
            print(f"Transcript: {result.alternatives[0].transcript}")

    return response

    

# Function to convert and upload files
def convert_and_upload_files_in_folder(bucket_name, folder_name, wav_file, folder_path_wav_files):
    folder_path_flac = f"{folder_name}_flac"
    
    if not os.path.exists(folder_path_flac):
        os.makedirs(folder_path_flac)
        print(f"Created folder: {folder_path_flac}")

    if not os.path.exists(folder_path_wav_files):
        os.makedirs(folder_path_wav_files)
        print(f"Created folder: {folder_path_wav_files}")

    delete_flac_files_in_folder(folder_path_flac)
    flac_file = convert_wav_to_flac(folder_path_flac, wav_file, bucket_name)
    
    if flac_file:
        destination_blob_name = os.path.join(folder_name, os.path.basename(flac_file))
        f_file = upload_to_bucket(bucket_name, flac_file, destination_blob_name)
        return f_file
    else:
        print(f"Failed to convert {wav_file} to FLAC")
        return None

def main():
   

    list_of_folders_in_gs = ['EEM_1_2024-04-30_12-59-28', 'EEM_2_2024-06-07_10-05-48', 'EEM_3_2024-06-25_13-10-47', 'EEM_4_2024-07-02_12-37-13', 'EEM_6_ set_1_2024-08-06_11-11-41', 'EEM_7_2024-09-06_13-32-31', 'EEM_8-2024-09-11-control-1', 'EEM_8-2024-9-11-control-2']

    for folder_name in list_of_folders_in_gs: 
        output_file = f"{folder_name}_output.csv"
        df_all = pd.DataFrame(columns=['File', 'Transcript'])

        bucket_name = "audio_recordings_tobii_v1"
        wav_files = [blob.name for blob in storage.Client().bucket(bucket_name).list_blobs(prefix=folder_name) if blob.name.endswith('.wav')]
        
        delete_flac_files_in_bucket(bucket_name)

        for wav_file in wav_files:
            print(f"Processing {wav_file}...")
            flac_file = convert_and_upload_files_in_folder(bucket_name, folder_name, wav_file, folder_name)  # Pass bucket_name here
            
            if flac_file:
                recognition_result = recognize_audio(f"audio_recordings_tobii_v1/{flac_file}")
                print(recognition_result)

                results = recognition_result.results

                if results: 
                # Loop through each result in the recognition response
                    for result in results:
                        alternative = result.alternatives[0]
                        
                        # Extract words and their timestamps
                        word_time_offsets = alternative.words
                        timestamps = []
                        for word_info in word_time_offsets:
                            # Use total_seconds() to extract start and end times
                            start_time = word_info.start_time.total_seconds()
                            end_time = word_info.end_time.total_seconds()
                            timestamps.append((word_info.word, start_time, end_time))
                        # Create a DataFrame with the required columns
                        df_iter = pd.DataFrame({
                            'File': [wav_file],
                            'Transcript': [alternative.transcript],
                            'Confidence': [alternative.confidence],
                            'Timestamps': [timestamps]  # Timestamps as list of tuples
                        })

                        print(df_iter)

                        df_all = pd.concat([df_all, df_iter], ignore_index=True)

        df_all.to_csv(output_file, index=False)
        print(f"Results saved to {output_file}")

if __name__ == "__main__":
    main()
