from can import Bus, Message

class can_sender:
    def __init__(self,throttle_id=0x01, wheel_id=0x02,gear_id=0x03,brake_id=0x04) -> None:
        self.bus = Bus(interface='socketcan',channel='vcan0', bitrate = 250000)
        self.ids = {"throttle":throttle_id, "wheel":wheel_id,"gear":gear_id,"brake":brake_id}
    
    def convert(self, type, value):
        val = [0]
        match type:
            case "throttle" | "brake":
                val = [int (abs(value) * 255)] #range 0->255               
            case "wheel":
                val = [int(value * 127)] if value >= 0 else [int(value * 127 + 256)]
            case "gear":
                val = [1] if value else [255]
        self.send_msg(Message(arbitration_id=self.ids[type], data = val))
    def send_msg(self,msg):
        try:
            self.bus.send(msg)
            return True
        except:
            return False
    def connect():
        pass
    def send(self,type,bytes):
        msg = Message(arbitration_id=id, data=bytes)
        try:
            self.bus.send(msg)
            return True
        except:
            return False
        
if __name__ == "__main__":
    a = can_sender()
    b = a.send(0x23, [3,5,7])
    print(b)