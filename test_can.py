from can import Bus, Message
import time
with Bus(interface='socketcan',channel='vcan0', bitrate = 250000) as conn:
    for i in range(0,255):
        conn.send(Message(arbitration_id=1,data=[i]))
        conn.send(Message(arbitration_id=2,data=[i]))
        conn.send(Message(arbitration_id=3,data=[int(i/2)]))
        conn.send(Message(arbitration_id=4, data = [255-i]))
        time.sleep(0.1)