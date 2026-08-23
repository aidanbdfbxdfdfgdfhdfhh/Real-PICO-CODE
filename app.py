import network

import ota
import wifi

from machine import Pin, PWM
from time import sleep


# Enable only the hardware test you want to run.
onboard_test = False
rgb_test = False
button_test = False
rgb_button_test = False
auto_update_check_seconds = 60


On_bored_led = Pin("LED", Pin.OUT)
On_bored_led.on()

if onboard_test:
    onboard_led = Pin("LED", Pin.OUT)

    for _ in range(5):
        onboard_led.on()
        sleep(1)
        onboard_led.off()
        sleep(1)

    print("Passed onboard LED check")


if rgb_test:
    rgb_pins = [Pin(pin, Pin.OUT) for pin in range(16, 19)]

    for _ in range(5):
        for led in rgb_pins:
            led.on()
            sleep(1)
            led.off()

    print("Passed RGB output check")


if button_test:
    red_led = Pin(0, Pin.OUT)
    button = Pin(15, Pin.IN, Pin.PULL_UP)

    while True:
        red_led.value(button.value() == 0)
        sleep(0.01)


# Keep checking GitHub after the hardware test finishes. Changing GitHub's
# version.txt makes ota.check_for_update() install app.py and restart the Pico.
if not button_test and not rgb_button_test:
    print("Automatic OTA checks every", auto_update_check_seconds, "seconds")

    while True:
        sleep(auto_update_check_seconds)

        wlan = network.WLAN(network.STA_IF)
        if not wlan.isconnected():
            wlan = wifi.connect()

        if wlan is not None and wlan.isconnected():
            ota.check_for_update()


if rgb_button_test:
    # RGB PWM outputs. This assumes a common-cathode RGB LED.
    blue = PWM(Pin(16))
    green = PWM(Pin(17))
    red = PWM(Pin(18))

    for output in (red, green, blue):
        output.freq(1000)
        output.duty_u16(0)

    def set_color(rgb):
        red.duty_u16(rgb[0] * 257)
        green.duty_u16(rgb[1] * 257)
        blue.duty_u16(rgb[2] * 257)

    indicator = Pin(19, Pin.OUT)
    direction_button = Pin(7, Pin.IN, Pin.PULL_UP)
    red_button, green_button, blue_button = [
        Pin(pin, Pin.IN, Pin.PULL_UP) for pin in range(12, 15)
    ]

    amount = 30
    rgb = [0, 0, 0]
    decrease_mode = False
    last_direction = 1

    while True:
        current_direction = direction_button.value()

        if current_direction == 0 and last_direction == 1:
            decrease_mode = not decrease_mode
            indicator.value(decrease_mode)
            print("Mode:", "DOWN" if decrease_mode else "UP")
            sleep(0.05)

        last_direction = current_direction
        change = -amount if decrease_mode else amount

        for index, button in enumerate(
            (red_button, green_button, blue_button)
        ):
            if button.value() == 0:
                rgb[index] = max(0, min(rgb[index] + change, 255))
                set_color(rgb)
                print(rgb)
                sleep(0.15)

        sleep(0.01)
