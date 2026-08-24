from machine import Pin
from time import sleep_ms


onboard_led = Pin("LED", Pin.OUT)
onboard_led.on()

buttons = [Pin(pin, Pin.IN, Pin.PULL_UP) for pin in (11, 12, 13, 14, 15)]
leds = [Pin(pin, Pin.OUT) for pin in (0,1, 2, 3, 4)]

# Keep GP15 as the counter button until the buttons are mapped.
button = buttons[4]


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
        count = (count + 1) % 32
        display_number(count)
        print("Count:", count)
        wait_for_release()

    sleep_ms(10)
