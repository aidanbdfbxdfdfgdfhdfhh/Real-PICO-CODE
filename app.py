from machine import Pin
from time import sleep

on_off_led = Pin("LED",Pin.OUT)
on_off_led.on()



button = Pin(15, Pin.IN, Pin.PULL_UP)
leds = [Pin(pin, Pin.OUT) for pin in (0, 1,)]



num = 0

def update_led(num):

    biner = [int(x) for x in f"{num:02b}"]

    led = -1
    for item in biner:
        led += 1
        if item == 1:
            leds[led].on()
        if item == 0:
            leds[led].off()


update_led(num)

while True:
    while button.value() == 1:
        sleep(0.1)
    num += 1

    if num > 3:
        num = 0

    update_led(num)
    while button.value() == 0:
        sleep(0.01)
