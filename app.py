from machine import Pin
from time import sleep


onboard_led = Pin("LED", Pin.OUT)

def morse_code(timeings):
    for i in timeings:
        onboard_led.on()
        sleep(i)
        onboard_led.off()
        sleep(i)

timeing = [1,1,1,1]

morse_code(timeing)


while True:
    onboard_led.on()
    sleep(1)
    onboard_led.off()
    sleep(1)