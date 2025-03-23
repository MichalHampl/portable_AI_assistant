import av, wave, speech, numpy, pyaudio, io, librosa, soundfile
from flask import Flask, render_template, jsonify, request, Response
import text_processing
import timeit, pyttsx4, threading,time

app = Flask(__name__)
out_buffer = bytes()
first_seg_done = 0
in_buffer = bytes()
buffer_size = 24000                                 #this HAS to match buffer size on uC

#text to speech function, didnt work in a separate module
def text_to_speech(text):
    engine = pyttsx4.init()
    voices = engine.getProperty('voices')
    engine.setProperty("voice",voices[1].id)
    out = io.BytesIO()
    engine.save_to_file(text,out)
    engine.runAndWait()
    wav_out = raw_to_wav_stream(out.getvalue(),1,2,22050)
    return wav_out

def text_to_speech_converted(text):
    engine = pyttsx4.init()
    voices = engine.getProperty('voices')
    engine.setProperty("voice",voices[1].id)
    out = io.BytesIO()
    engine.save_to_file(text,out)
    engine.runAndWait()
    wav_out = raw_to_wav_stream(out.getvalue(),1,2,22050)
    y, sr = librosa.load(wav_out ,mono=True)                                                                 #load outputted wav stream
    res_y = librosa.resample(y,orig_sr=22050,target_sr=8000,res_type="soxr_hq")                             #resample to 8000hz
    stream2 = io.BytesIO()
    soundfile.write(stream2,res_y,format="wav",samplerate=8000,subtype="PCM_U8")                            #save to stream 2 as 8bit PCM
    adio = raw_to_wav_stream(stream2.getvalue())                                                                          #open stream2 as wav
    to_send = wave.open(adio,"rb")
    return to_send.readframes(to_send.getnframes())                                                   #put audio samples to send into output buffer


#raw data to wav stream conversion 
#The uC returns data in Unsigned 8-bit PCM, audio data sent back MUST be the same format
def raw_to_wav_stream(raw_audio_data, channels=1, sample_width=1, frame_rate=8000):                                         
    wav_stream = io.BytesIO()

    wav_file = wave.open(wav_stream, 'wb')

    wav_file.setnchannels(channels)
    wav_file.setsampwidth(sample_width)
    wav_file.setframerate(frame_rate)
    
    wav_file.writeframes(raw_audio_data)    
    wav_stream.seek(0)                      

    return wav_stream

#Most basic audio to audio processing function.
#Takes filepath or file-like object as argument in wav format of course
def process_simple(filepath):
    text = speech.speech_to_text_from_file(filepath)
    print(text)
    output = text_processing.text_to_text(text,256)
    print(output)
    return text_to_speech(output)


# audio processing function that uses streaming for text to text generation it gradually fills up output buffer which can be read before the whole text is generated
# needs to run in its own thread
def generator_sts(wav_file,token_len = 512, segment_len = 32, cutoff = 64):
    global out_buffer, first_seg_done
    first_seg_done = 0
    text_prompt = speech.speech_to_text_from_file(wav_file)
    print(text_prompt,end="")
    text_out = text_processing.ttt_generator2(text_prompt,token_len)
    token_counter = 0
    tmp_text = str()
    for token in text_out:
        print(token,end="")
        token_counter += 1
        tmp_text += token
        if (token_counter > segment_len and ("." in token or ":" in token or "\n" in token)) or token_counter > cutoff:
            out_buffer += text_to_speech_converted(tmp_text)
            tmp_text = ""
            token_counter = 0
            first_seg_done = 1
    out_buffer += text_to_speech_converted(tmp_text)
    first_seg_done = 1
    return

@app.route('/')
def index_page():
    return render_template('index.html')

@app.route('/functions/play/<int:seg>')
def play(seg):
    if (seg+1)*buffer_size < len(out_buffer):
        print("1")
        resp = b'\x01\x00\x00\x00\x00\x00\x00\x00' + out_buffer[seg*buffer_size:(seg+1)*buffer_size]        #first byte set to one signalizing next frames will be sent
    else:
        print("2")
        resp = b'\x02\x00\x00\x00\x00\x00\x00\x00' + out_buffer[seg*buffer_size:(seg+1)*buffer_size]        #first byte set to two signalizing this is the last frame
    return Response(resp, mimetype="application/octet-stream")

@app.route('/functions/send1', methods=['POST'])
def get_sound():
    global out_buffer, in_buffer
    print(type(request))
    s1 = int.from_bytes((bytearray(request.data)[0:1]),byteorder="big")
    print(s1)
    if s1 == 1:                                                                                             # do when recieving non-last frame
        in_buffer += bytearray(request.data)[8:buffer_size+8]
        return Response(bytes([1]), mimetype="application/octet-stream")                                    # returning 1 and expecting next frame
    elif s1 == 2:                                                                                            # do on last frame recieved
        in_buffer += bytearray(request.data)[8:buffer_size+8]                                                 # adding loading last segment into input buffer                                        
        wav_in = raw_to_wav_stream(in_buffer,1,1,16000)
        stream = io.BytesIO()
        t0 = timeit.default_timer()                                                                             #timing for debug
        stream = process_simple(wav_in)                                                                         #process input audio into output audio
        t1 = timeit.default_timer()
        y, sr = librosa.load(stream ,mono=True)                                                                 #load outputted wav stream
        res_y = librosa.resample(y,orig_sr=22050,target_sr=8000,res_type="soxr_hq")                             #resample to 8000hz
        stream2 = io.BytesIO()
        soundfile.write(stream2,res_y,format="wav",samplerate=8000,subtype="PCM_U8")                            #save to stream 2 as 8bit PCM
        adio = raw_to_wav_stream(stream2.getvalue())                                                                          #open stream2 as wav
        to_send = wave.open(adio,"rb")
        t2 = timeit.default_timer()
        print("Speech to text and AI: ",t1-t0,"\n","wav converion: ",t2-t1,"\n")
        out_buffer = to_send.readframes(to_send.getnframes())                                                   #put audio samples to send into output buffer
        if len(out_buffer) < buffer_size:
            out_buffer.zfill(buffer_size)
        f = open("test input.wav","wb")                                                                     #saving of inputted voice command for debugging puropses REMOVE FOR LONGER OPERATION
        f.write(wav_in.getvalue())
        f.close
        in_buffer = in_buffer[0:0]
        return Response(bytes([2]), mimetype="application/octet-stream")                                    # returning 2 when output buffer is ready to be sent
    in_buffer = 0
    return  Response(bytes([0]), mimetype="application/octet-stream")                                       

@app.route('/functions/send', methods=['POST'])
def get_sound_continuous():
    global out_buffer, in_buffer, first_seg_done
    out_buffer = out_buffer[0:0]
    print(type(request))
    s1 = int.from_bytes((bytearray(request.data)[0:1]),byteorder="big")
    print(s1)
    if s1 == 1:                                                                                             # do when recieving non-last frame
        in_buffer += bytearray(request.data)[8:buffer_size+8]
        return Response(bytes([1]), mimetype="application/octet-stream")                                    # returning 1 and expecting next frame
    elif s1 == 2:                                                                                            # do on last frame recieved
        in_buffer += bytearray(request.data)[8:buffer_size+8]                                                 # adding loading last segment into input buffer
        wav_in = raw_to_wav_stream(in_buffer,1,1,16000)
        t1 = threading.Thread(target=generator_sts , args=(wav_in, ),daemon=True)
        t1.start()
        timeout = 0
        while not first_seg_done:
            time.sleep(0.01)
            timeout += 1
        first_seg_done = 0
        in_buffer = in_buffer[0:0]
        return Response(bytes([2]), mimetype="application/octet-stream")                                    # returning 2 when output buffer is ready to be sent
    in_buffer = in_buffer[0:0]
    return  Response(bytes([0]), mimetype="application/octet-stream")

if __name__ == "__main__":  
    audio = wave.open("test4.wav",'rb')
    out_buffer = audio.readframes(audio.getnframes())
    app.run(host='0.0.0.0', port=5056, debug=True, use_reloader=False)
    t0 = timeit.default_timer()
    #output = process_simple("audio.wav")
    t1 = timeit.default_timer()
    print(t1-t0)
    