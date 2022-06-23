from django.shortcuts import render
from Home.models import Videos
from VoiceOver.settings import MEDIA_ROOT

import subprocess
import numpy as np
from pydub import AudioSegment
import wave
from moviepy.editor import *
import pyttsx3
import contextlib
# from googletrans import Translator



def index(request):
    if request.method == "POST":
        video_obj = Videos()
        video_file = request.FILES['video_file']
        sub_file = request.FILES['sub_file']
        lang = request.POST['lang']
        video_obj.video = video_file
        video_obj.sub = sub_file
        video_obj.save()
        video_name_ext = video_obj.video.name
        sub_name_ext = video_obj.sub.name
        video_path = f"{MEDIA_ROOT}{video_name_ext}"
        sub_path = f"{MEDIA_ROOT}{sub_name_ext}"
        video_name = video_name_ext.split(".")[0]
        sub_name = sub_name_ext.split(".")[0]
        command = f'ffmpeg -i "{video_path}" -ac 1 -ar 16000 -acodec pcm_s16le -vn "{MEDIA_ROOT}{video_name}.wav"'
        subprocess.call(command, shell=True)
# ...........................................................................................................
        sub_file = open(sub_path, 'r', encoding='utf-8')
        interval_file = open(f'{MEDIA_ROOT}interval_{sub_name}.srt', 'w', encoding='utf-8')
        output_file = open(f"{MEDIA_ROOT}{sub_name}.txt", "w", encoding='utf-8')
        sub_read = sub_file.read()
        list_of_lines = sub_read.split('\n')
        interval_line_list = []

        for line in list_of_lines:
            line = line.replace("<i>", '')
            line = line.replace("</i>", '')
            line = line.replace("</ i>", '')

            output_file.write(line + "\n")

            if line.find('-->') > 0:
                interval_line_list.append(line)
        output_file.close()

        no_of_audio_files = len(interval_line_list)

        # interval_2d_list = []
        # for i in range(len(interval_line_list)):
        #     interval_2d_list.append(interval_line_list[i].split(' --> '))

        interval_2d_list = []
        for line in interval_line_list:
            interval_2d_list.append(line.split(' --> '))

        for i in range(len(interval_2d_list)):
            for j in range(2):
                interval_2d_list[i][j] = interval_2d_list[i][j].replace(",", ":")
                time = interval_2d_list[i][j].split(':')
                interval_2d_list[i][j] = int(
                    time[0]) * 3600 + int(time[1]) * 60 + int(time[2]) + float(int(time[3]) / 1000)

        for i in range(len(interval_2d_list)):
            interval_file.write(
                str(interval_2d_list[i][0]) + " " + str(interval_2d_list[i][1]) + '\n')
        interval_file.close()
        sub_file.close()

# ..........................................................................................................

        file_open = open(f"{MEDIA_ROOT}{sub_name}.txt", 'r', encoding='utf8')
        file_read = file_open.read()
        line_list = file_read.split('\n')
        dialog_list = []
        i = 2
        while i < len(line_list):
            dialog_list.append(line_list[i])
            if line_list[i + 1] != '':
                while line_list[i +1] != '':
                    dialog_list[-1] += line_list[i+1]
                    i = i + 1   # bcs next dialog is after 4 lines
            i = i + 4 
#............................................................................................................    
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        engine.setProperty('rate', 120)
        engine.setProperty('voice', voices[int(lang)].id)
        g = 0
        for j in dialog_list:
            engine.save_to_file(j, f'{MEDIA_ROOT}{video_name} {g}.wav')
            g = g + 1
            engine.runAndWait()
# ................................................................................................................
        intervals = np.loadtxt(f'{MEDIA_ROOT}interval_{sub_name}.srt')  # 2D list
        start = 0
        result = AudioSegment.silent(duration=0)  # empty audio file
        original_audio = AudioSegment.from_file(f"{MEDIA_ROOT}{video_name}.wav", format="wav")  # Original audio file
        for i in range(no_of_audio_files):
            interval_start = intervals[i][0]
            interval_end = intervals[i][1]
            interval_start_milli_sec = interval_start * 1000  # added
            interval_end_milli_sec = interval_end * 1000  # added
            fname = f'{MEDIA_ROOT}{video_name} {i}.wav'

            temp_file = AudioSegment.from_file(fname, format="wav")
            result = result + original_audio[start: interval_start_milli_sec] + temp_file
            start = interval_end_milli_sec

            print(f"{i + 1} done out of {no_of_audio_files}")

        result = result + original_audio[start:]
        result.export(f"{MEDIA_ROOT}final_{video_name}.mp3", format="wav")

        # intervals = np.loadtxt('interval_srt.srt')  # 2D list
        clip = VideoFileClip(video_path)
        file_length = clip.duration

        for i in reversed(range(no_of_audio_files)):
            interval_start = intervals[i][0]
            interval_end = intervals[i][1]
            time_period = interval_end - interval_start
            fname = f'{MEDIA_ROOT}{video_name} {i}.wav'

            with contextlib.closing(wave.open(fname, 'r')) as f:
                frames = f.getnframes()
                rate = f.getframerate()
                audio_clip_time = frames / float(rate)

            start_part = clip.subclip(0, interval_start)
            main = clip.subclip(interval_start, interval_end)
            end_part = clip.subclip(interval_end, file_length)
            speed_find = time_period / audio_clip_time
            main = main.fx(vfx.speedx, speed_find)
            clip = concatenate_videoclips([start_part, main, end_part])
            file_length = clip.duration
            print(f"{no_of_audio_files- i} done out of {no_of_audio_files}")

        audioclip = AudioFileClip(f"{MEDIA_ROOT}final_{video_name}.mp3")

        new_audioclip = CompositeAudioClip([audioclip])
        clip.audio = new_audioclip
        clip.write_videofile(f"{MEDIA_ROOT}final_{video_name}.mp4")
        final_video_ext = f"final_{video_name}.mp4"

        return render(request,'home/index.html',{'video_name_ext': video_name_ext, 'final_video_ext': final_video_ext})

    return render(request,'home/index.html')
