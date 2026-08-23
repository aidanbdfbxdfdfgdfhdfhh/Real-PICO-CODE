from machine import Pin
from time import sleep


onboard_led = Pin("LED", Pin.OUT)

def morse_code(timeings):

    for i in timeings:
        if i == "-":
            t = 1
        if i == ".":
            t = 0.5
        onboard_led.on()
        sleep(t)
        onboard_led.off()
        sleep(t)

timeing = "...---..."

morse_code(timeing)



onboard_led.off()
