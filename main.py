from flask import Flask, render_template, jsonify, request, Response
from task_list import task_list
import time
app = Flask(__name__)
buffer_size = 24000

tempid = None
id = 0

tl = task_list()
@app.route('/')
def index_page():
    return render_template('index.html')

@app.route('/functions/play/<int:seg>')
def play(seg):
    if (seg+1)*buffer_size < tl.get_out_audio_len(id):
        print("1")
        resp = b'\x01\x00\x00\x00\x00\x00\x00\x00' + tl.read_frames(id,seg*buffer_size,(seg+1)*buffer_size)        #first byte set to one signalizing next frames will be sent
    else:
        print("2")
        resp = b'\x02\x00\x00\x00\x00\x00\x00\x00' + tl.read_frames(id,seg*buffer_size,(seg+1)*buffer_size)        #first byte set to two signalizing this is the last frame
    return Response(resp, mimetype="application/octet-stream")

@app.route('/functions/send', methods=['POST'])
def get_sound_continuous():
    global tempid, id
    print(type(request))
    s1 = int.from_bytes((bytes(request.data)[0:1]),byteorder="big")
    print(s1)
    if s1 == 1:
        if tempid == None:                                                                                             # do when recieving non-last frame
            tempid = tl.add_task(bytes(request.data)[8:buffer_size+8])
        else:
            tl.append_audio_to_task(tempid,bytes(request.data)[8:buffer_size+8])
        return Response(bytes([1]), mimetype="application/octet-stream")                                    # returning 1 and expecting next frame
    elif s1 == 2:                                                                                            # do on last frame recieved
        if tempid == None:                                                                                             # do when recieving non-last frame
            tempid = tl.add_task(bytes(request.data)[8:buffer_size+8])
        else:
            tl.append_audio_to_task(tempid,bytes(request.data)[8:buffer_size+8])                                                 # adding loading last segment into input buffer
        tl.finalize_task(tempid)
        while not tl.is_in_progress(tempid):
            time.sleep(0.01)
        id = tempid
        tempid = None
        return Response(bytes([2]), mimetype="application/octet-stream")                                    # returning 2 when output buffer is ready to be sent
    id = tempid
    tempid = None
    return  Response(bytes([0]), mimetype="application/octet-stream")

if __name__ == "__main__":
    #print(tl.text_to_speech_converted("bruh"))
    tl.run()  
    app.run(host='0.0.0.0', port=5056, debug=True, use_reloader=False)