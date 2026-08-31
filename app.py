import machine
import time
from machine import Pin
from rp2 import PIO, StateMachine, asm_pio


# Onboard LED so you know the program started
led = Pin("LED", Pin.OUT)
led.on()


# Standard 640x480 VGA timing
SM0_FREQ = 25_175_000
SM1_FREQ = 125_000_000


# --------------------------------------------------
# HORIZONTAL SYNC
# VGA pin 13 -> Pico GP14
# --------------------------------------------------

@asm_pio(
    set_init=PIO.OUT_HIGH,
    autopull=True,
    pull_thresh=32
)
def VGA_Hsync():

    wrap_target()

    # Active video + front porch
    # 640 + 16 = 656 pixel clocks
    mov(x, osr)

    label("activeporch")
    jmp(x_dec, "activeporch")

    # 96 pixel-clock H-Sync pulse
    # H-Sync is active LOW
    set(pins, 0) [31]
    set(pins, 0) [31]
    set(pins, 0) [31]

    # 48 pixel-clock back porch
    set(pins, 1) [31]
    set(pins, 1) [13]

    # Signal the vertical state machine
    # that another scan line has completed
    irq(0)

    wrap()


hsync = StateMachine(
    0,
    VGA_Hsync,
    freq=SM0_FREQ,
    set_base=Pin(14)
)


# --------------------------------------------------
# VERTICAL SYNC
# VGA pin 14 -> Pico GP15
# --------------------------------------------------

@asm_pio(
    sideset_init=(PIO.OUT_HIGH,),
    autopull=True,
    pull_thresh=32
)
def VGA_Vsync():

    # Pull visible-line count once
    pull(block)

    wrap_target()

    # 480 visible lines
    mov(x, osr)

    label("active")
    wait(1, irq, 0)
    jmp(x_dec, "active")

    # 10-line front porch
    set(y, 9)

    label("frontporch")
    wait(1, irq, 0)
    jmp(y_dec, "frontporch")

    # 2-line V-Sync pulse
    # V-Sync active LOW
    wait(1, irq, 0).side(0)
    wait(1, irq, 0)

    # 33-line back porch
    set(y, 31)

    label("backporch")
    wait(1, irq, 0).side(1)
    jmp(y_dec, "backporch")

    wait(1, irq, 0)

    wrap()


vsync = StateMachine(
    1,
    VGA_Vsync,
    freq=SM1_FREQ,
    sideset_base=Pin(15)
)


# --------------------------------------------------
# START VGA
# --------------------------------------------------

# 655 because the PIO jmp(x_dec) loop effectively
# produces the required 656 clocks.
hsync.put(655)

# 479 produces 480 visible scan lines
vsync.put(479)


# Start vertical first because it waits for H-Sync
vsync.active(1)
hsync.active(1)


print("VGA sync running")
print("GP14 -> VGA pin 13 H-Sync")
print("GP15 -> VGA pin 14 V-Sync")
print("Expected mode: 640x480 @ approximately 60Hz")


while True:
    machine.idle()