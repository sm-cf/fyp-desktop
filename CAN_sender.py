from can import Bus, Message

class Can_sender:
    def __init__(self,throttle_id=0x10, wheel_id=0x20,gear_id=0x30) -> None:
        self.bus = Bus(interface='socketcan',channel='vcan0', bitrate = 250000)
        self.ids = {"throttle":throttle_id, "wheel":wheel_id,"gear":gear_id}
    
    def convert(self, type, value):
        val = None
        match type:
            case "throttle":
                val = [int (abs(value) * 255)]                
            case "wheel":
                val = [int(value * 128)]
            case "gear":
                val = [value]
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
    a = Can_sender()
    b = a.send(0x23, [3,5,7])
    print(b)