from machine import Pin,PWM
from time import sleep_ms,sleep


onboard_led = Pin("LED", Pin.OUT)
onboard_led.on()

button = Pin(15, Pin.IN, Pin.PULL_UP)
leds = [Pin(pin, Pin.OUT) for pin in (0,1, 2, 3, 4,5)]



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




def color(rgb):

    # RGB PWM outputs
    blue = PWM(Pin(16))
    green = PWM(Pin(17))
    red = PWM(Pin(18))

    blue.freq(1000)
    green.freq(1000)
    red.freq(1000)

    r = rgb[0]
    g = rgb[1]
    b = rgb[2]

    red.duty_u16(r * 257)
    green.duty_u16(g * 257)
    blue.duty_u16(b * 257)

color([255, 0, 0])   # MUST be RED
sleep(2)

color([0, 255, 0])   # MUST be GREEN
sleep(2)

color([0, 0, 255])   # MUST be BLUE
sleep(2)

# Indicator LED/output
sing = Pin(19, Pin.OUT)

# Toggle button
sing_button = Pin(14, Pin.IN, Pin.PULL_UP)

# RGB buttons
r, g, b = [
    Pin(i, Pin.IN, Pin.PULL_UP)
    for i in range(11, 14)
]

num = 10
rgb_list = [0, 0, 0]

# False = increase
# True = decrease
decrease_mode = False

last_toggle = 1

while True:

    # Detect one press of the toggle button
    current_toggle = sing_button.value()

    if current_toggle == 0 and last_toggle == 1:
        decrease_mode = not decrease_mode

        if decrease_mode:
            print("Mode: DOWN")
            sing.on()
        else:
            print("Mode: UP")
            sing.off()

        sleep(0.05)  # debounce

    last_toggle = current_toggle

    # Decide whether RGB buttons add or subtract
    if decrease_mode:
        inter = -num
    else:
        inter = num

    # RED button
    if r.value() == 0:
        rgb_list[0] = max(
            0,
            min(rgb_list[0] + inter, 255)
        )
        color(rgb_list)
        print(rgb_list)
        sleep(0.15)

    # GREEN button
    if g.value() == 0:
        rgb_list[1] = max(
            0,
            min(rgb_list[1] + inter, 255)
        )
        color(rgb_list)
        print(rgb_list)
        sleep(0.15)

    # BLUE button
    if b.value() == 0:
        rgb_list[2] = max(
            0,
            min(rgb_list[2] + inter, 255)
        )
        color(rgb_list)
        print(rgb_list)
        sleep(0.15)


    if button.value() == 0:
        if decrease_mode:
            count = (count - 1) % 64
        else:
            count = (count + 1) % 64

        display_number(count)
        print("Count:", count)
        wait_for_release()

    sleep_ms(10)
