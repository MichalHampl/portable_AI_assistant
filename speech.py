from faster_whisper import WhisperModel
import string


#model = WhisperModel("distil-medium.en")
model = WhisperModel("distil-large-v2")

#segments, info = model.transcribe("audio.mp3")
#for segment in segments:
#    print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))



def speech_to_text_from_file(file):
    text = ""
    segments, info = model.transcribe(file)
    
    for segment in segments:
        text = text + segment.text
    return text

def speech_to_text(samples):
    text = ""
    segments, info = model.transcribe(samples)
    for segment in segments:
        text = text + segment.text
    return text
