# This file is executed on every boot (including wake-boot from deepsleep)
from machine import Pin
outputs = {}
pin0  = Pin(0,  Pin.OPEN_DRAIN, value=1); outputs[0] = pin0
pin2  = Pin(2,  Pin.OPEN_DRAIN, value=1); outputs[2] = pin2
pin4  = Pin(4,  Pin.OPEN_DRAIN, value=1); outputs[4] = pin4
pin5  = Pin(5,  Pin.OPEN_DRAIN, value=1); outputs[5] = pin5
pin16 = Pin(16, Pin.OPEN_DRAIN, value=1); outputs[16] = pin16
pin17 = Pin(17, Pin.OPEN_DRAIN, value=1); outputs[17] = pin17
pin18 = Pin(18, Pin.OPEN_DRAIN, value=1); outputs[18] = pin18
pin19 = Pin(19, Pin.OPEN_DRAIN, value=1); outputs[19] = pin19
pin21 = Pin(21, Pin.OPEN_DRAIN, value=1); outputs[21] = pin21
pin22 = Pin(22, Pin.OPEN_DRAIN, value=1); outputs[22] = pin22
pin23 = Pin(23, Pin.OPEN_DRAIN, value=1); outputs[23] = pin23
pin25 = Pin(25, Pin.OPEN_DRAIN, value=1); outputs[25] = pin25
pin26 = Pin(26, Pin.OPEN_DRAIN, value=1); outputs[26] = pin26
pin27 = Pin(27, Pin.OPEN_DRAIN, value=1); outputs[27] = pin27
inputs = {}
pin32 = Pin(32, Pin.IN, None); inputs[32] = pin32
pin33 = Pin(33, Pin.IN, None); inputs[33] = pin33
pin34 = Pin(34, Pin.IN, None); inputs[34] = pin34
pin35 = Pin(35, Pin.IN, None); inputs[35] = pin35

import esp
esp.osdebug(None)

import network
ap_if = network.WLAN(network.AP_IF)
ap_if.config(essid="88", authmode=network.AUTH_WPA2_PSK, password="zzzzzzzzzzzzz")
ap_if.active(True)

import webrepl
webrepl.start()
