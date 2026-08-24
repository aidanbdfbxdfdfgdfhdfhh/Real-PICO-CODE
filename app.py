from machine import Pin
from time import sleep_ms


button = Pin(15, Pin.IN, Pin.PULL_UP)
leds = [Pin(pin, Pin.OUT) for pin in (0, 1, 2, 3)]


def display_number(number):
    for position, led in enumerate(leds):
        bit = (number >> position) & 1
        led.value(bit)


def wait_for_release():
    while button.value() == 0:
        sleep_ms(10)

    sleep_ms(20)


count = 0
display_number(count)
print("Count:", count)

while True:
    if button.value() == 0:
        count = (count + 1) % 16
        display_number(count)
        print("Count:", count)
        wait_for_release()

    sleep_ms(10)
