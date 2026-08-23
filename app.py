from machine import Pin, PWM
from time import sleep



on_bored_test = True
rgb_test = False
button_test = False
rgb_button_test = False


if on_bored_test == True:
    On_bored_led = Pin("LED", Pin.OUT)

    for i in range(5):
        On_bored_led.on()
        sleep(1)
        On_bored_led.off()
        sleep(1)

    print("Passed onboard check")


if rgb_test == True:
    rgb = [Pin(i, Pin.OUT) for i in range(16, 19)]

    for i in range(5):
        for led in rgb:
            led.on()
            sleep(1)
            led.off()

    print("Passed RGB check")


if button_test == True:
    red_led = Pin(0, Pin.OUT)
    button = Pin(15, Pin.IN, Pin.PULL_UP)

    while button_test == True:
        if button.value() == 0:
            red_led.on()
        else:
            red_led.off()

        sleep(0.01)




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


if rgb_button_test == True:

    # Indicator LED/output
    sing = Pin(19, Pin.OUT)

    # Toggle button
    sing_button = Pin(7, Pin.IN, Pin.PULL_UP)

    # RGB buttons
    r, g, b = [
        Pin(i, Pin.IN, Pin.PULL_UP)
        for i in range(12, 15)
    ]

    num = 30
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

        sleep(0.01)