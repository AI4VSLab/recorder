import os
import json
from subprocess import Popen, PIPE
import pandas as pd

def convert_to_flac(wav_file):
    flac_file = os.path.splitext(wav_file)[0] + ".flac"
    command = f"ffmpeg -i {wav_file} {flac_file}"
    process = Popen(command.split(), stdout=PIPE, stderr=PIPE)
    output, error = process.communicate()
    return flac_file if os.path.exists(flac_file) else flac_file

def json_csv(json_output, file_name): 
    # data = json.loads(json_output)

    # Concatenate transcripts
    transcript = ' '.join([result['alternatives'][0]['transcript'] for result in json_output['results']])

    # Create DataFrame
    df_iter = pd.DataFrame({'File': [file_name], 'Transcript': [transcript]})

    return df_iter



def recognize_audio(file_path):
    command = f"gcloud ml speech recognize {file_path} --language-code=en-US"
    process = Popen(command.split(), stdout=PIPE, stderr=PIPE)
    output, error = process.communicate()
    return output.decode("utf-8")

def main():
    output_file = "output.txt"
    folder_path = "$debug"
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
                try:
                    json_output = json.loads(recognition_result)
                    df_iter = json_csv(json_output, filename)
                    # df_all = df_all.append(df_iter, ignore_index=True)
                    print(df_iter)
                    df_all = pd.concat([df_all, df_iter], ignore_index=True)



                    # f_out.write(json.dumps(json_output, indent=4))
                except json.JSONDecodeError:
                    f_out.write("Error: Unable to decode JSON output")
                f_out.write("\n\n")
                os.remove(flac_file)  # Remove the temporary FLAC file
        df_all.to_csv('output.csv', index=False)


if __name__ == "__main__":
    main()
