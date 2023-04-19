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
import socket
class Duckie_Sender:
    def __init__(self,port,ip) -> None:
        self.port = port
        self.ip=ip

class VCAN_Sender:
    def __init__(self) -> None:
        pass

class Controller:
    #axes = [0,0]
    #is_forward_gear = True #is the gear forward or reverse
    def __init__(self, axes=[0,0], forward_gear=True, throttle=0) -> None:
        self.axes = axes
        self.is_forward_gear = forward_gear
        self.throttle = throttle
        self.steering_percent = 0
        self.calc_steering()
    
    def update_axes(self, axis, pos):
        self.axes[axis] = pos
        self.calc_steering()

    def update_throttle(self, throttle):
        self.throttle = (throttle * 100 if self.is_forward_gear else -(throttle*100))
        print(self.throttle)

    def change_gear(self, change=True):
        if change:
            self.is_forward_gear = not self.is_forward_gear
            self.throttle = - self.throttle
            print(self.is_forward_gear)
    
    def calc_steering(self):
        mag = sqrt(self.axes[0]**2 + self.axes[1]**2) * 100 #joystick percentage distance from center
        mag = min( 100, max( 0, mag ) ) #clamping value to between 0 -> 100
        self.steering_percent = mag * sign(self.axes[0]) # adding left/right direction info
        print(self.steering_percent)




# App with a green ball in the center that moves when you press the HAT buttons
import pyjoystick
from pyjoystick.sdl2 import Key, Joystick, run_event_loop
# from pyjoystick.pygame import Key, Joystick, run_event_loop
from qt_thread_updater import ThreadUpdater

from qtpy import QtWidgets, QtGui, QtCore

ct = Controller([0,0],True)

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

    #print(key, '-', key.keytype, '-', key.number, '-', key.value)

    #if key.keytype == "Button":
        #change gear

    #if key in ["Axis 2", "-Axis 2"]: #right analog stick left-right
    #   ct.update_axes(0,key.value)

    #elif key in ["Axis 3", "-Axis 3"]: #right analog stick up-down
    #    ct.update_axes(1,key.value)

    #elif key == "Axis 4": #left trigger
    #    ct.update_throttle(key.value)

    match key: #requires python 3.10 or higher
        case "Axis 2" | "-Axis 2": #right analog stick left/right
            ct.update_axes(0,key.value)
        case "Axis 3" | "-Axis 3": #right analog stick up/down
            ct.update_axes(1,key.value)
        case "Axis 4": # left trigger
            ct.update_throttle(key.value)
        case "Button 0": # x button
            ct.change_gear(key.value)

    return
    updater.now_call_latest(mover.move, mover.point)

# If it button is held down it should be repeated
repeater = pyjoystick.HatRepeater(first_repeat_timeout=0.5, repeat_timeout=0.03, check_timeout=0.01)

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