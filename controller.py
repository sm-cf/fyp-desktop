#!/usr/bin/python3.10
#https://pypi.org/project/pyjoystick/
# this script gets input from DS4, then sends it both to the duckiebot and to the VCAN network

# this script takes input from DS4, sends it on VCAN and to duckie
# a script on duckie is listening for this, converts message to ros and publishes it on ~joy
# another script on duckie is listening to wheels_cmd and sends messages to computer
# computer receives this message, converts to CAN and sends on VCAN
# analysis program listens to VCAN network and does its magic
# sends message on VCAN
# sends message to duckie, which duckie converts and publishes
# need all the duckie stuff done by like thursday so I can do the analysis part
# god help me ;p I did this to myself

#idea for flourish - maybe a GUI for controller????? I hate myself lol
#also revert change to throttle - makes no sense to do it at this stage. Actually may work out simpler if I keep it this way, less work for duckie - doesnt need to keep track of gear changes
#also script to just send random messages on the VCAN 
from math import sqrt
from numpy import sign
from can import Bus, Message
class Controller:
    def __init__(self) -> None:
        self.axes = [0,0]
        self.is_forward_gear = True
        self.throttle = 0
        self.steering = 0
        self.bus = Bus(interface='socketcan',channel='vcan0', bitrate = 250000)
    
    def calc_steering(self):
        mag = int(sqrt(self.axes[0]**2 + self.axes[1]**2) * 127 * sign(self.axes[0]))#joystick percentage distance from center
        if self.axes[0] < 0: mag += 256
        self.steering = mag

    def v2_send(self, id, val):
        match id:
            case "Axis 3" | "-Axis 3": #right analog stick left/right
                self.axes[0] = val
                self.calc_steering()
                msg_id = 3; msg_val = [self.steering]
            case "Axis 4" | "-Axis 4": #right analog stick up/down
                self.axes[1] = val
                self.calc_steering()
                msg_id = 3; msg_val = [self.steering]
            case "Axis 2": # left trigger (throttle)
                msg_id = 1; msg_val = [int(val*255)]
            case "Axis 5": #right trigger (brake)
                msg_id = 2; msg_val = [int(val*255)]
            case "Button 0": # x button (gear)
                if val:
                    self.is_forward_gear = not self.is_forward_gear
                    msg_id = 4; msg_val = [1] if self.is_forward_gear else [255]
                else: return
            case _:#wildcard
                return
        self.bus.send(Message(arbitration_id=msg_id,data=msg_val,is_extended_id=False))

        




# App with a green ball in the center that moves when you press the HAT buttons
import pyjoystick
from pyjoystick.sdl2 import Key, Joystick, run_event_loop
# from pyjoystick.pygame import Key, Joystick, run_event_loop
from qt_thread_updater import ThreadUpdater

from qtpy import QtWidgets, QtGui, QtCore

ct = Controller()

app = QtWidgets.QApplication([])

updater = ThreadUpdater()

main = QtWidgets.QWidget()
main.setLayout(QtWidgets.QHBoxLayout())
main.resize(800, 600)
main.show()

lbl = QtWidgets.QLabel()  # Absolute positioning
main.layout().addWidget(lbl, alignment=QtCore.Qt.AlignTop)

mover = QtWidgets.QLabel(parent=main)  # Absolute positioning
mover.resize(50, 50)
mover.point = main.rect().center()
mover.move(mover.point)
mover.show()


def svg_paint_event(self, event):
    painter = QtGui.QPainter(self)
    painter.setRenderHint(painter.Antialiasing, True)

    # Get Black Background
    rect = self.rect()
    center = rect.center()
    radius = 20

    # Colors
    painter.setBrush(QtGui.QColor('green'))  # Fill color
    painter.setPen(QtGui.QColor('black'))  # Line Color

    # Draw
    painter.drawEllipse(center, radius, radius)

    painter.end()

mover.paintEvent = svg_paint_event.__get__(mover, mover.__class__)

def handle_key_event(key):
    updater.now_call_latest(lbl.setText, '{}: {} = {}'.format(key.joystick, key, key.value))
    ct.v2_send(key,key.value)


# If it button is held down it should be repeated
#repeater = pyjoystick.HatRepeater(first_repeat_timeout=0.5, repeat_timeout=0.03, check_timeout=0.01)
repeater = pyjoystick.Repeater(first_repeat_timeout=1.0, repeat_timeout=0.5, check_timeout=0.01)

mngr = pyjoystick.ThreadEventManager(event_loop=run_event_loop,
                                     handle_key_event=handle_key_event,
                                     button_repeater=repeater)
mngr.start()

# Find key functionality
btn = QtWidgets.QPushButton('Find Key:')

def find_key():
    key = mngr.find_key(timeout=float('inf'))
    if key is None:
        btn.setText('Find Key:')
    else:
        btn.setText('Find Key: {} = {}'.format(key, key.value))

btn.clicked.connect(find_key)
main.layout().addWidget(btn, alignment=QtCore.Qt.AlignTop)

app.exec_()