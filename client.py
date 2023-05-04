import socket
class connect:
    def __init__(self) -> None:
        
        self.HOST = "myrobot.local"#"192.168.0.46"#myrobot.local
        self.PORT = 5555
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.HOST ,self.PORT))
        #with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        #    s.connect((self.HOST, self.PORT))
        #    s.sendall(b"whatup")
    
    def send(self,throttle=0,steering=0):
        #throttle =int(throttle*1024)
        #steering=min(1024,int(steering*1024))
        self.sock.sendall(bytes(f"{throttle}:{steering};", encoding="utf-8")) #utf-8 doesnt matter here as all characters have same ASCII code
        #self.sock.sendall(struct.pack('<2d', throttle,steering))
        #self.sock.sendall(bytes(f"{throttle} {steering}",encoding="utf-8"))
