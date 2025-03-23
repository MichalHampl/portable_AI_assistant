from machine import Pin, Timer, ADC, SPI, I2S, PWM
import machine
import _thread, time, network, urequests, gc, sys

machine.freq(240000000)

#i2s = I2S(0, sck=Pin(0), ws=Pin(1), sd=Pin(2), mode=I2S.RX, bits=16, format=I2S.MONO, rate=8000, ibuf=16000)
#spi = SPI(0, baudrate=64_000, polarity=0, phase=0, bits=8, sck=Pin(6), mosi=Pin(7), miso=Pin(4))
led = Pin('LED',Pin.OUT)
rec_pin = Pin(6,mode=Pin.IN,pull=Pin.PULL_UP)
wlan = network.WLAN()
wlan.active(True)
pwm0 = PWM(Pin(1), freq=253000, duty_u16=32768)
pwm0.init()
#spi.deinit()

ADC_pin = ADC(Pin(27))
tim0 = Timer()

SSID = "SSID"
PASSWORD = "PASSWORD"

URL = "http://10.0.0.39:5056"


buffer_size = const(24000)
i = 0
j = 0
bfswitch = 0
bf0s = 0                         # 0 - buffer empty, 1 - buffer full
bf1s = 0
status = 0                       # 0 - doing nothing, 1 - playing 2 - recording, 3 - last frame recieved, 4 - sending last frame
lf_size = 0                      # size of the last frame
bf0 = bytearray(buffer_size)
bf1 = bytearray(buffer_size)

def connect():
    i = 0
    wlan.connect(SSID,PASSWORD)
    while (not wlan.isconnected())  and i < 10:
        i = i + 1
        time.sleep(1)
    if wlan.isconnected():
        led.on()
        return 1
    return 0

def read_ADC_0(n):
    global i, status, bf0
    bf0[i] = ADC_pin.read_u16() >> 8
    i = i + 1
    if rec_pin.value():
        status = 4
        tim0.deinit()
        bf0 = bf0[0:i]
        i = buffer_size-1
    
def read_buff_0(size = buffer_size):
    global i, status
    i = 0
    tim0.init(mode=Timer.PERIODIC,freq=16000,callback=read_ADC_0)
    while i < (size-2):
        pass
    tim0.deinit()

def read_ADC_1(n):
    global i, status, bf1
    bf1[i] = ADC_pin.read_u16() >> 8
    i = i + 1
    if rec_pin.value():
        status = 4
        tim0.deinit()
        bf1 = bf1[0:i]
        i = buffer_size-1
    
def read_buff_1(size = buffer_size):
    global i, status
    i = 0
    tim0.init(mode=Timer.PERIODIC,freq=16000,callback=read_ADC_1)
    while i < (size-2):
        pass
    tim0.deinit()

def pwm0_duty_0(x):
    global j, status
    pwm0.duty_u16(bf0[j]*256)
    j = j + 1
    if rec_pin.value() == 0:
        status = 0
        tim0.deinit()
        j = buffer_size +1

def pwm_write_0(size = buffer_size):
    global j
    j = 0
    tim0.init(mode=Timer.PERIODIC,freq=8000,callback=pwm0_duty_0)
    while j < size:
        pass
    tim0.deinit()

def pwm0_duty_1(x):
    global j, status
    pwm0.duty_u16(bf1[j]*256)
    j = j + 1
    if rec_pin.value() == 0:
        status = 0
        tim0.deinit()
        j = buffer_size +1
    
def pwm_write_1(size = buffer_size):
    global j
    j = 0
    tim0.init(mode=Timer.PERIODIC,freq=8000,callback=pwm0_duty_1)
    while j < size:
        pass
    tim0.deinit()

def recieve():
    global bf0s, bf1s, bf0, bf1, status, lf_size
    seg = 0
    status = 1
    bf0s = 0
    bf1s = 0
    while True:
        if bf0s == 0:
            result = urequests.get(URL + '/functions/play/'+ str(seg))
            bf0 = result.content[8:buffer_size+8]
            length = len(result.content)-8
            s1 = int.from_bytes(result.content[0:1],"big")
            seg = seg + 1
            print("r1 sent")            
            if s1 == 2:
                
                lf_size = length
                status = 3
                bf0s = 1
                print("r1 last")
                while status == 3:
                    pass
                return "Rx finished"
            bf0s = 1
            del result
            gc.collect()
        if status != 1 and status != 3:
            return "Rx finished"    
        if bf1s == 0:
            result = urequests.get(URL + '/functions/play/'+ str(seg))
            bf1 = result.content[8:buffer_size+8]
            length = len(result.content)-8
            s1 = int.from_bytes(result.content[0:1],"big")
            seg = seg + 1
            print("r2 sent")
            if s1 == 2:
                lf_size = length
                status = 3
                bf1s = 1
                print("r1 last")
                while status == 3:
                    pass
                return "Rx finished"
            bf1s = 1
            del result
            gc.collect()
        if status != 1 and status != 3:
            return "Rx finished"
            
def send_seg_0(signal):
    header = {"content-type": "application/octet-stream"}
    data = int(signal).to_bytes(1,"big") + b'\x00\x00\x00\x00\x00\x00\x00' + bf0
    result = urequests.post(url=URL + "/functions/send",headers=header,data=data)
    del data
    gc.collect()
    return int.from_bytes(result.content[0:1],"big")

# 
def send_seg_1(signal):
    header = {"content-type": "application/octet-stream"}
    data = int(signal).to_bytes(1,"big") + b'\x00\x00\x00\x00\x00\x00\x00' + bf1
    result = urequests.post(url= URL + "/functions/send",headers=header,data=data)
    del data
    gc.collect()
    return int.from_bytes(result.content[0:1],"big")
         
def transmit():
    print("transmitting")
    global bf0s, bf1s, bf0, bf1, status
    print("bf0s: ",bf0s,"bf1s: ",bf1s, "status: ", status)
    header = {"content-type": "application/octet-stream"}
    bf0s = 0
    bf1s = 0
    status = 2                                                 #set status to 2 - recording
    print("bf0s: ",bf0s,"bf1s: ",bf1s, "status: ", status)
    while True:
        if (bf0s == 1) and (status == 2):
            send_seg_0(1)
            bf0s = 0
        if (bf1s == 1) and (status == 2):
            send_seg_1(1)
            bf1s = 0
        if status == 4:
            time.sleep(0.1)                                    #this is necesseary
            if bf0s and bf1s:
                send_seg_0(1)
                send_seg_1(2)
                bf0s = 0
                bf1s = 0
            elif bf0s == 1:
                send_seg_0(2)
                bf0s = 0
            elif bf1s == 1:
                send_seg_1(2)
                bf1s = 0
            status = 0
            return "channel closed"
            

#control loop for handling the buffers
#when playing (status == 1), it  checks of buffer signal is 1, then plays segment and then sets the signal to 0
#when recording it checks if bfxs 0 then records into the buffer and sets that bfxs 1
#this will run in parallel to the main program
def the_loop():
    global bf0s, status, bf1s, lf_size
    while True:
        if status == 0:
            pass
        elif status == 1 and bf0s == 1:                           #the playing mode            
                print("write 1")
                pwm_write_0()
                bf0s = 0                      #buffer is emptied
        elif status == 1 and bf1s == 1:
                print("write 2")
                pwm_write_1()
                bf1s = 0
        elif status == 2 and bf0s == 0:                           #the recording mode
            print("read 1")
            read_buff_0()
            print("read 1 done")
            bf0s = 1                            # buffer 1 be full
        elif status == 2 and bf1s == 0:
            print("read 2")
            read_buff_1()
            print("read 2 done")
            bf1s = 1
        elif (status == 3):
            if bf0s == 1:
                print("write 1")
                pwm_write_0(lf_size-1)
                bf0s = 0                      #buffer is emptied
                status = 0
            if bf1s == 1:
                print("write 2")
                pwm_write_1(lf_size-1)
                bf1s = 0
                status = 0
        while status == 4:
            pass
    print("here")
        #print("delta:", (t1 - t0)/1000,"us")
while connect() == 0:
    pass
_thread.start_new_thread(the_loop, ())
while True:
    if not rec_pin.value():
        transmit()
        gc.collect()
        print(recieve())
        gc.collect()
        bf0 = bytearray(buffer_size)
        bf1 = bytearray(buffer_size)
        time.sleep(1)
        
#debugging parking lot
#print("here")

#

#read_buff_0()
#send_seg(2)
#pwm0.init()
#thread_one()