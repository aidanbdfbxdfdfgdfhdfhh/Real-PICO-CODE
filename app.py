from machine import Pin, PWM
from time import sleep

on_board_led = Pin("LED", Pin.OUT)
on_board_led.value(1)
# VGA 640x480-ish sync test

# Horizontal sync
hsync = PWM(
    Pin(14),
    freq=31469,
    duty_ns=3813,
    invert=True
)

# Vertical sync
vsync = PWM(
    Pin(16),
    freq=60,
    duty_ns=63500,
    invert=True
)

print("VGA sync running")

while True:
    sleep(1)