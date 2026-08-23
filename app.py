from machine import Pin



onboard_led = Pin("LED", Pin.OUT)

def morse_code(timeings):
    for i in timeings:
        onboard_led.on()
        sleep(timeings[i])
        onboard_led.off()
        sleep(timeings[i])

timeing = [1,1,1,1]

morse_code(timeing)