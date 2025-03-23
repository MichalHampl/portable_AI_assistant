
import pyttsx4, wave
import io


def raw_to_wav_stream(raw_audio_data, channels=1, sample_width=2, frame_rate=22050):
    wav_stream = io.BytesIO()

    wav_file = wave.open(wav_stream, 'wb')

    wav_file.setnchannels(channels)
    wav_file.setsampwidth(sample_width)
    wav_file.setframerate(frame_rate)
    
    wav_file.writeframes(raw_audio_data)    
    wav_stream.seek(0)                      

    return wav_stream


engine = pyttsx4.init()
voices = engine.getProperty('voices')
engine.setProperty("voice",voices[1].id)

def text_to_speech(text):
    out = io.BytesIO()
    engine.save_to_file(text,out)
    engine.runAndWait()
    wav_out = raw_to_wav_stream(out.getvalue())
    return wav_out