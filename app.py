

import machine
import time

from machine import Pin
from rp2 import PIO, StateMachine, asm_pio




# -------------------------------------------------------
# Raspberry Pi Pico VGA SYNC TEST
#
# VGA pin 1  -> GP13 through the two series resistors  RED
# VGA pin 13 -> GP14                              H-Sync
# VGA pin 14 -> GP15                              V-Sync
#
# GP0, GP1 and GP2 are not used.
# -------------------------------------------------------


# Make sure Pico is running at normal 125 MHz
machine.freq(125_000_000)


# Turn onboard LED on so we know the program started
led = Pin("LED", Pin.OUT)

led.off()
time.sleep(0.2)
led.on()
time.sleep(0.2)
led.off()
time.sleep(0.2)
led.on()


# Standard VGA 640x480 timing
#
# Pixel clock:       25.175 MHz
#
# Horizontal:
# Visible            640
# Front porch         16
# Sync                96
# Back porch          48
# Total               800
#
# Vertical:
# Visible             480
# Front porch         10
# Sync                 2
# Back porch          33
# Total               525


HSYNC_FREQ = 25_175_000
VSYNC_FREQ = 125_000_000
RED_FREQ = 25_175_000


# -------------------------------------------------------
# HORIZONTAL SYNC
#
# GP14 -> VGA pin 13
# -------------------------------------------------------

@asm_pio(set_init=PIO.OUT_HIGH)
def hsync_program():

    # Get the horizontal count from Python
    pull(block)

    wrap_target()

    # Copy 655 into X
    mov(x, osr)

    # 640 visible pixels
    # +
    # 16 pixel front porch
    #
    # = 656 clocks
    label("active_front")
    jmp(x_dec, "active_front")

    # H-Sync LOW for 96 pixel clocks
    set(pins, 0) [31]
    set(pins, 0) [31]
    set(pins, 0) [31]

    # Back porch
    set(pins, 1) [31]
    set(pins, 1) [13]

    # Tell the V-Sync state machine
    # that one complete horizontal line occurred
    irq(0)

    wrap()


# -------------------------------------------------------
# VERTICAL SYNC
#
# GP15 -> VGA pin 14
# -------------------------------------------------------

@asm_pio(sideset_init=(PIO.OUT_HIGH,))
def vsync_program():

    # Get 479 from Python
    pull(block)

    wrap_target()

    # 480 visible lines
    mov(x, osr)

    label("visible")
    wait(1, irq, 0)
    irq(1)
    jmp(x_dec, "visible")

    # 10-line front porch
    set(y, 9)

    label("front_porch")
    wait(1, irq, 0)
    jmp(y_dec, "front_porch")

    # V-Sync LOW for 2 lines
    wait(1, irq, 0).side(0)
    wait(1, irq, 0)

    # Bring V-Sync HIGH again
    # and wait through the back porch
    set(y, 31)

    label("back_porch")
    wait(1, irq, 0).side(1)
    jmp(y_dec, "back_porch")

    # Final back-porch line
    wait(1, irq, 0)

    wrap()


# -------------------------------------------------------
# SOLID RED VIDEO
#
# GP13 -> two 220 ohm resistors in series -> VGA pin 1
#
# Red is high for 640 pixel clocks and low during blanking.
# IRQ 1 comes from the V-Sync program only on visible lines.
# -------------------------------------------------------

@asm_pio(set_init=PIO.OUT_LOW)
def red_program():
    # 637 gives 638 loop cycles. Together with set + mov, red stays
    # high for exactly 640 PIO clocks.
    pull(block)

    wrap_target()
    wait(1, irq, 1)
    set(pins, 1)
    mov(x, osr)

    label("visible_red")
    jmp(x_dec, "visible_red")

    set(pins, 0)
    wrap()


# -------------------------------------------------------
# CREATE STATE MACHINES
# -------------------------------------------------------

hsync = StateMachine(
    0,
    hsync_program,
    freq=HSYNC_FREQ,
    set_base=Pin(14)
)


vsync = StateMachine(
    1,
    vsync_program,
    freq=VSYNC_FREQ,
    sideset_base=Pin(15)
)


red = StateMachine(
    2,
    red_program,
    freq=RED_FREQ,
    set_base=Pin(13)
)


# -------------------------------------------------------
# LOAD TIMING COUNTERS
# -------------------------------------------------------

# 0..655 = 656 horizontal clocks
hsync.put(655)

# 0..479 = 480 visible lines
vsync.put(479)

# 1 set cycle + 1 mov cycle + 638 loop cycles = 640 red clocks
red.put(637)


# Red waits for V-Sync, and V-Sync waits for H-Sync.
red.active(1)
vsync.active(1)

# Now start H-Sync
hsync.active(1)


print("")
print("VGA TEST RUNNING")
print("----------------")
print("GP13 -> resistors -> VGA pin 1 RED")
print("GP14 -> VGA pin 13 H-Sync")
print("GP15 -> VGA pin 14 V-Sync")
print("Target: 640x480 @ ~60 Hz")
print("")
print("Leave this program running.")


# Keep Pico alive. WiFi/OTA remains handled by the existing main.py at boot.
while True:
    machine.idle()
