import socket
from can import Bus, Message 
from math import sqrt
class connect:
    def __init__(self) -> None:
        
        self.HOST = "myrobot.local"#"192.168.0.46"#myrobot.local
        self.PORT = 5556
        self.wheel_ids = [0x5,0x6,0x7]
        self.can_connect()
        #self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.sock.connect((self.HOST ,self.PORT))
        #with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        #    s.connect((self.HOST, self.PORT))
        #    s.sendall(b"whatup")
    
    def send_to_can(self,id, val):
        #throttle =int(throttle*1024)
        
        val = [int(val * 127)] if val >= 0 else [int(val * 127 + 256)]
        msg = Message(arbitration_id=id,data=val)
        try:
            self.bus.send(msg)
        except:
            print("was?")
        #steering=min(1024,int(steering*1024))
        #self.sock.sendall(bytes(f"{throttle}:{steering};", encoding="utf-8")) #utf-8 doesnt matter here as all characters have same ASCII code
        #self.sock.sendall(struct.pack('<2d', throttle,steering))
        #self.sock.sendall(bytes(f"{throttle} {steering}",encoding="utf-8"))
        pass
    def convert_to_can(self, msg):
        print(msg)
        msg = msg.decode("utf-8").split(";")[-2].split(":")
        vel_left = float(msg[0]); vel_right = float(msg[1])
        avg_vel = (vel_left + vel_right) / 2
        self.send_to_can(self.wheel_ids[0], vel_left)
        self.send_to_can(self.wheel_ids[1], vel_right)
        self.send_to_can(self.wheel_ids[2], avg_vel)
    
    def can_connect(self):
        self.bus = Bus(interface='socketcan',channel='vcan0', bitrate = 250000)
    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.HOST,self.PORT))
            while True:
                try:
                    msg = s.recv(1024)
                except:
                    print("help?")
                    break
                self.convert_to_can(msg)


if __name__=="__main__":
    client = connect()
    client.run()
