from can import Bus, Message
from threading import Thread
from random import randrange
from time import sleep
from math import sin,cos,tan


def send_increase(pause, id):
    counter=0
    with Bus(interface='socketcan',channel='vcan0', bitrate = 250000) as conn:
        while True:
            counter = (counter + 1) % 256
            conn.send(Message(arbitration_id=id, data=[counter]))
            sleep(pause)

def send_decrease(pause, id):
    counter=256
    with Bus(interface='socketcan',channel='vcan0', bitrate = 250000) as conn:
        while True:
            counter = (counter - 1) % 256
            conn.send(Message(arbitration_id=id, data=[counter]))
            sleep(pause)

def send_random(pause, id):
    with Bus(interface='socketcan',channel='vcan0', bitrate = 250000) as conn:
        while True:
            data = randrange(0,256)
            conn.send(Message(arbitration_id=id, data=[data]))
            sleep(pause)

def send_sin(pause, id):
    counter=0
    with Bus(interface='socketcan',channel='vcan0', bitrate = 250000) as conn:
        while True:
            counter = counter + 0.1
            if counter > 6.1:counter=0
            data = int((sin(counter)+1)*127)
            conn.send(Message(arbitration_id=id, data=[data]))
            sleep(pause)

def send_cos(pause, id):
    counter=0
    with Bus(interface='socketcan',channel='vcan0', bitrate = 250000) as conn:
        while True:
            counter = counter + 0.1
            if counter > 6.1:counter=0
            data = int((cos(counter)+1)*127)
            conn.send(Message(arbitration_id=id, data=[data]))
            sleep(pause)

def send_cube(pause, id):
    counter=0
    with Bus(interface='socketcan',channel='vcan0', bitrate = 250000) as conn:
        while True:
            counter = counter + 0.1
            if counter > 2:counter=0
            data = int((((1-counter)**3)+1)*127)
            conn.send(Message(arbitration_id=id, data=[data]))
            sleep(pause)

def send_fibonnaci(pause, id):
    fib = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]
    counter =0
    with Bus(interface='socketcan',channel='vcan0', bitrate = 250000) as conn:
        while True:
            counter = (counter + 1) % 14
            data = fib[counter]
            conn.send(Message(arbitration_id=id, data=[data]))
            sleep(pause)
# one increasing
# one decreasing
# one random
# one sin
# one cos
# one tan
# one fibonnaci
pause= 0.1
inc_thread = Thread(target=send_increase, args=(pause,10))
dec_thread = Thread(target=send_decrease, args=(pause,11))
sin_thread = Thread(target=send_sin, args=(pause,12))
cos_thread = Thread(target=send_cos, args=(pause,13))
cub_thread = Thread(target=send_cube, args=(pause,14))
ran_thread = Thread(target=send_random, args=(pause,15))
fib_thread = Thread(target=send_fibonnaci, args=(pause,16))

inc_thread.start()
dec_thread.start()
sin_thread.start()
cos_thread.start()
cub_thread.start()
ran_thread.start()
fib_thread.start()