from machine import Pin
from time import sleep

red_led = Pin(1, Pin.OUT)
button = Pin(15, Pin.IN, Pin.PULL_UP)

while True:
    if button.value() == 0:
        red_led.on()
    else:
        red_led.off()

    sleep(0.01)