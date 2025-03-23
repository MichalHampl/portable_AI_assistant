
import threading, pyttsx4, librosa, io, wave, time, soundfile
import speech
import text_processing

class task_list:

    def __init__(self):
        #states: ready, pending, in_progress, completed
        self.tasks = [({"id":0, "prompt": "Name all planets in the solar system", "response": "", "state": "completed", "timeout": 20},bytes(),bytes()),
                      ({"id":1, "prompt": "Name all planets in the solar system", "response": "", "state": "completed", "timeout": 20},bytes(),bytes())
                      ]
        self.last_id = 2
        self.timeout_value = 20

    def read_frames(self,id,start,end):
        return next((task for task in self.tasks if task[0]['id'] == id), None)[2][start:end]
    
    def get_tuple_by_id(self,id):
        return next((task for task in self.tasks if task[0]['id'] == id), None)
    
    def generate_id(self):
        self.last_id += 1
        return self.last_id
    
    def add_task(self,prompt_audio):
        id = self.generate_id()
        self.tasks.append(({"id":id, "prompt": "", "response": "", "state": "pending", "timeout": 20},prompt_audio,bytes()))
        print("added task id:",id)
        return id
    
    def finalize_task(self,id):
        print("finalize task id: ",id)
        self.change_state(id,"ready")

    def complete_task(self,id):
        self.change_state(id,"completed")

    def append_audio_to_task(self,id,audio,which_one = 1):
        for i, task in enumerate(self.tasks):
            if task[0]["id"] == id:
                if which_one == 1:
                    new_task = ({"id": task[0]["id"], "prompt": task[0]["prompt"], "response": task[0]["response"], "state": task[0]["state"], "timeout": self.timeout_value}, task[1] + audio, task[2])
                elif which_one == 2:
                    new_task = ({"id": task[0]["id"], "prompt": task[0]["prompt"], "response": task[0]["response"], "state": task[0]["state"], "timeout": self.timeout_value}, task[1], task[2] + audio)
                else:
                    new_task = ({"id": task[0]["id"], "prompt": task[0]["prompt"], "response": task[0]["response"], "state": task[0]["state"], "timeout": self.timeout_value}, task[1], task[2])
                self.tasks[i] = new_task

    def change_prompt_text(self,id,prompt):
        for i, task in enumerate(self.tasks):
            if task[0]["id"] == id:
                new_task = ({"id": task[0]["id"], "prompt": prompt, "response": task[0]["response"], "state": task[0]["state"], "timeout": self.timeout_value}, task[1], task[2])
                self.tasks[i] = new_task

    def change_state(self,id,new_state):
        for i, task in enumerate(self.tasks):
            if task[0]["id"] == id:
                new_task = ({"id": task[0]["id"], "prompt": task[0]["prompt"], "response": task[0]["response"], "state": new_state, "timeout": self.timeout_value}, task[1], task[2])
                self.tasks[i] = new_task
    
    def change_response(self,id, new_response):
        for i, task in enumerate(self.tasks):
            if task[0]["id"] == id:
                new_task = ({"id": task[0]["id"], "prompt": task[0]["prompt"], "response": new_response, "state": task[0]["state"], "timeout": self.timeout_value}, task[1], task[2])
                self.tasks[i] = new_task
    
    def get_out_audio_len(self,id):
        return len(self.get_tuple_by_id(id)[2])
        
    def run(self):
        t0 = threading.Thread(target=self.tasker, args=( ),daemon=True)
        t0.start()

    def tasker(self):
        while True:
            for task in self.tasks:
                if task[0]["state"] == "ready":
                    print("task id: ",task[0]["id"])
                    print("task state: ","ready")
                    self.speech_to_speech_task(task[0]["id"])
            #return
            time.sleep(0.01)

    def is_in_progress(self,id):
        if   self.get_tuple_by_id(id) == None:
            return False
        elif self.get_tuple_by_id(id)[0]["state"] == "in_progress":
            return True
        else:
            return False
        
    def raw_to_wav_stream(self,raw_audio_data, channels=1, sample_width=1, frame_rate=8000):                                         
        wav_stream = io.BytesIO()
        wav_file = wave.open(wav_stream, 'wb')
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(frame_rate)   
        wav_file.writeframes(raw_audio_data)    
        wav_stream.seek(0)                      
        return wav_stream
    
    def text_to_speech_converted(self,text):
        engine = pyttsx4.init()
        voices = engine.getProperty('voices')
        engine.setProperty("voice",voices[1].id)
        out = io.BytesIO()
        engine.save_to_file(text,out)
        engine.runAndWait()
        wav_out = self.raw_to_wav_stream(out.getvalue(),1,2,22050)
        y, sr = librosa.load(wav_out ,mono=True)                                                                 #load outputted wav stream
        res_y = librosa.resample(y,orig_sr=22050,target_sr=8000,res_type="soxr_hq")                             #resample to 8000hz
        stream2 = io.BytesIO()
        soundfile.write(stream2,res_y,format="wav",samplerate=8000,subtype="PCM_U8")                            #save to stream 2 as 8bit PCM
        adio = self.raw_to_wav_stream(stream2.getvalue())                                                                          #open stream2 as wav
        to_send = wave.open(adio,"rb")
        return to_send.readframes(to_send.getnframes()) 
    
    # audio processing function that uses streaming for text to text generation it gradually fills up output buffer which can be read before the whole text is generated
    def generator_sts(self,wav_file,id,token_len = 512, segment_len = 32, cutoff = 64):
        text_prompt = speech.speech_to_text_from_file(wav_file)                                             #speech to text conversion
        print(text_prompt)
        text_out = text_processing.ttt_generator2(text_prompt,token_len)                                   #text to text
        token_counter = 0
        tmp_text = str()
        for token in text_out:                                                                              #iterating over token generator
            print(token,end="")
            token_counter += 1
            tmp_text += token
            if (token_counter > segment_len and ("." in token or ":" in token or "\n" in token)) or token_counter > cutoff:
                self.append_audio_to_task(id, self.text_to_speech_converted(tmp_text),which_one=2)                                                  #adding audio samples to the otput buffer
                tmp_text = ""
                token_counter = 0
                self.change_state(id,"in_progress")
        self.append_audio_to_task(id,self.text_to_speech_converted(tmp_text), which_one=2)                              
        self.change_state(id,"in_progress")
        return
    
    def speech_to_speech_task(self,id):
        self.generator_sts(self.raw_to_wav_stream(self.get_tuple_by_id(id)[1],1,1,16000),id=id,token_len=512)

#tl = task_list()
#tl.run()
#print(tl.text_to_speech_converted("bruh"))