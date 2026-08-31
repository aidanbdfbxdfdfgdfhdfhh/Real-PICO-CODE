import machine
import time
from machine import Pin
from rp2 import PIO, StateMachine, asm_pio


# LED = program running
led = Pin("LED", Pin.OUT)
for i in range(3):
    led.on()
    time.sleep(1)
    led.off()
    time.sleep(1) 

# 640x480 @ ~60 Hz VGA timing
HSYNC_FREQ = 25_175_000
VSYNC_FREQ = 125_000_000


# --------------------------------------------------
# H-SYNC
# GP14 -> VGA pin 13
# --------------------------------------------------

@asm_pio(set_init=PIO.OUT_HIGH)
def vga_hsync():

    # IMPORTANT:
    # Load 655 from the TX FIFO into OSR once.
    pull(block)

    wrap_target()

    # Active area + front porch
    mov(x, osr)

    label("active_front")
    jmp(x_dec, "active_front")

    # 96 pixel clocks LOW
    set(pins, 0) [31]
    set(pins, 0) [31]
    set(pins, 0) [31]

    # Back porch
    set(pins, 1) [31]
    set(pins, 1) [13]

    # One horizontal line completed
    irq(0)

    wrap()


# --------------------------------------------------
# V-SYNC
# GP15 -> VGA pin 14
# --------------------------------------------------

@asm_pio(sideset_init=(PIO.OUT_HIGH,))
def vga_vsync():

    # Load 479 visible-line counter
    pull(block)

    wrap_target()

    # 480 visible lines
    mov(x, osr)

    label("visible")
    wait(1, irq, 0)
    jmp(x_dec, "visible")

    # 10 line front porch
    set(y, 9)

    label("front")
    wait(1, irq, 0)
    jmp(y_dec, "front")

    # 2 line negative sync pulse
    wait(1, irq, 0).side(0)
    wait(1, irq, 0)

    # 33 line back porch
    set(y, 31)

    label("back")
    wait(1, irq, 0).side(1)
    jmp(y_dec, "back")

    wait(1, irq, 0)

    wrap()


# Create state machines
hsync = StateMachine(
    0,
    vga_hsync,
    freq=HSYNC_FREQ,
    set_base=Pin(14)
)

vsync = StateMachine(
    1,
    vga_vsync,
    freq=VSYNC_FREQ,
    sideset_base=Pin(15)
)


# Give the PIO programs their counters
hsync.put(655)
vsync.put(479)


# Start VSYNC first because it waits for HSYNC
vsync.active(1)
hsync.active(1)


print("VGA sync started")
print("GP14 = H-Sync")
print("GP15 = V-Sync")
print("Target = 640x480 @ 60 Hz")


while True:
    machine.idle()