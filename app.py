from machine import Pin
import time

# Pico onboard LED
on_board_led = Pin("LED", Pin.OUT)



# Rows
row1 = Pin(0, Pin.OUT)
row2 = Pin(1, Pin.OUT)
row3 = Pin(2, Pin.OUT)

# Columns
col1 = Pin(3, Pin.OUT)
col2 = Pin(4, Pin.OUT)
col3 = Pin(5, Pin.OUT)

# Only Row 1 active
row1.value(1)
row2.value(0)
row3.value(0)

# All 3 LEDs in Row 1 ON
col1.value(0)
col2.value(0)
col3.value(0)

while True:
    time.sleep(1)