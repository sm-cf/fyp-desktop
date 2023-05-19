from can import Bus, Message
import socket

class CTD:
    def __init__(self, sock) -> None:
        self.throttle = 0
        self.steering = 0
        self.gear = 1
        self.brake=0
        self.sock = sock

    def convert(self,msg):
        try:
            data = int(msg.data.hex(),16)
        except: 
            return None
        if data < 0 or data > 255: return None

        match msg.arbitration_id:
            case 1: # throttle
                self.throttle = (data/255.0)
            case 2: # brake
                self.brake = data/255.0
            case 3: # steering
                if data > 127: data -=256
                self.steering = data/127.0
            case 4: # gear
                if data == 1: self.gear=1
                elif data == 255: self.gear=-1
                else: return None

        return bytes(f"{(max(0,self.throttle-self.brake))*self.gear}:{-(self.steering*self.throttle)};",encoding="utf-8")
            
    def can_to_duck(self):
        with Bus(interface='socketcan',channel='vcan0', bitrate = 250000) as conn:
            while True:
                msg = conn.recv()
                if msg.arbitration_id>4: continue
                duckie_msg = self.convert(msg)
                if duckie_msg is not None:
                    self.sock.sendall(duckie_msg)

if __name__ == '__main__':
    HOST = "myrobot.local"#"192.168.0.46"#myrobot.local
    PORT = 5555

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST ,PORT))
        ctd = CTD(sock)
        ctd.can_to_duck()