# -*- coding: utf-8 -*-
import pydub

def convert_to_wav_from_mp3(file_path):
    file_type = file_path[file_path.rfind('.') + 1:].lower()
    if file_type != 'mp3':
        return None
    
    new_file_path = file_path[:file_path.rfind('.')] + ".wav"

    sound = pydub.AudioSegment.from_mp3(file_path)
    sound.export(new_file_path, format="wav")

    return new_file_path

if __name__ == "__main__":
    new_file_name = convert_to_wav_from_mp3("news.mp3")
    print(new_file_name)