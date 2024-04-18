import os
import json
from subprocess import Popen, PIPE
import pandas as pd
from google.cloud import speech
import sys




def convert_to_flac(wav_file):
    flac_file = os.path.splitext(wav_file)[0] + ".flac"
    command = f"ffmpeg -i {wav_file} -ar 44100 {flac_file}"
    process = Popen(command.split(), stdout=PIPE, stderr=PIPE)
    output, error = process.communicate()
    return flac_file if os.path.exists(flac_file) else flac_file

def json_csv(result, file_name, alt_num): 

    alternative = result.alternatives[0]
    result_timestamps_string = ""
    for word_info in alternative.words:
        word = word_info.word
        start_time = word_info.start_time
        end_time = word_info.end_time
        timestamp_info = f"Word: {word}, start_time: {start_time.total_seconds()}, end_time: {end_time.total_seconds()}\n"
        result_timestamps_string = result_timestamps_string + timestamp_info
    file_name = file_name + "_" + "alternative" + "_" + str(alt_num)
    df_iter = pd.DataFrame({'File': [file_name], 'Transcript': [alternative.transcript], "Confidence": [alternative.confidence], "TimeStamps" : [result_timestamps_string]})

    return df_iter



def recognize_audio(file_path):
   
    with open(file_path, "rb") as audio_file:
        file_content = audio_file.read()

    client = speech.SpeechClient()


    audio = speech.RecognitionAudio(content=file_content)
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
    arguments = sys.argv[1:]
    print(sys.argv[1:])
    output_file = "output.txt"
    folder_path = arguments[0]
    df_all = pd.DataFrame(columns=['File', 'Transcript'])

    
    with open(output_file, "w") as f_out:
        for filename in os.listdir(folder_path):
            if filename.endswith(".wav"):
                audio_file = os.path.join(folder_path, filename)
                print(audio_file)
                flac_file = convert_to_flac(audio_file)
                print(flac_file)
                recognition_result = recognize_audio(flac_file)
                f_out.write(f"File: {filename}\n")
                alt_num = 0
                try:
                    for result in recognition_result.results: 
                        df_iter = json_csv(result, filename, alt_num)                        
                        df_all = pd.concat([df_all, df_iter], ignore_index=True)
                        alt_num+=1
                except json.JSONDecodeError:
                    f_out.write("Error: Unable to decode JSON output")
                f_out.write("\n\n")
                os.remove(flac_file)  # Remove the temporary FLAC file
        df_all.to_csv('output.csv', index=False)


if __name__ == "__main__":
    main()
