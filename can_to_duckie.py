from can import Bus, Message
import socket

class CTD:
    def __init__(self, sock) -> None:
        self.throttle = 0
        self.steering = 0
        self.gear = 1
        self.sock = sock

    def convert(self,msg):
        data = int(msg.data.hex(),16)
        if msg.arbitration_id == 1: #throttle
            self.throttle = (data/255.0)*self.gear
        elif msg.arbitration_id == 3: #gear
            self.gear = 1 if data == 1 else -1
        elif(data > 127): # steering 
            self.steering = (data - 255)/127.0
        else:
            self.steering = data/127.0
        return bytes(f"{self.throttle}:{-self.steering};",encoding="utf-8")
            
    def can_to_duck(self):
        with Bus(interface='socketcan',channel='vcan0', bitrate = 250000) as conn:
            while True:
                msg = conn.recv()
                if msg.arbitration_id>3: continue
                duckie_msg = self.convert(msg)
                self.sock.sendall(duckie_msg)

if __name__ == '__main__':
    HOST = "myrobot.local"#"192.168.0.46"#myrobot.local
    PORT = 5555

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST ,PORT))
        ctd = CTD(sock)
        ctd.can_to_duck()