from machine import Pin
import time

on_bored_led = Pin("led",Pin.OUT)

row1 = Pin(0, Pin.OUT)

col1 = Pin(3, Pin.OUT)
col2 = Pin(4, Pin.OUT)
col3 = Pin(5, Pin.OUT)

# Turn row 1 on
row1.value(1)

# First LED ON
col1.value(0)

# Other two OFF
col2.value(1)
col3.value(1)

while True:
    time.sleep(4)
    col2.value(0)
    col3.value(0)