from machine import Pin
import time

row1 = Pin(0, Pin.OUT)
row2 = Pin(1, Pin.OUT)
row3 = Pin(2, Pin.OUT)

col1 = Pin(3, Pin.OUT)
col2 = Pin(4, Pin.OUT)
col3 = Pin(5, Pin.OUT)

rows = [row1, row2, row3]
cols = [col1, col2, col3]


def turn_on_leds(*leds):
        for led in leds:

            if led < 1 or led > 9:
                continue

            # Everything OFF first
            for row in rows:
                row.value(0)

            for col in cols:
                col.value(1)

            index = led - 1
            row = index // 3
            col = index % 3

            # Selected LED ON
            rows[row].value(1)
            cols[col].value(0)

            time.sleep_ms(2)


state1 = 1
state2 = 5
state3 = 9
while True:
    start = time.ticks_ms()

    while time.ticks_diff(time.ticks_ms(), start) < 1000:
        turn_on_leds(state1, state2, state3)
        
    state1 +=  1
    state2 += 1
    state3 += 1

    if state1 == 4:
        state1 = 1
    if state2 == 7:
        state2 = 4
    if state3 == 10:
        state3 = 7
