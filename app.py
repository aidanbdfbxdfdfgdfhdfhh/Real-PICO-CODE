"""Reliable 640x480 VGA rotating stripe wallpapers for Raspberry Pi Pico.

No DMA is used. PIO0 generates VGA sync and PIO1 generates eight coloured
80-pixel stripes, blanked during the horizontal porches and sync pulse.

GP11 -> blue, GP12 -> green, GP13 -> red
GP14 -> H-Sync, GP15 -> V-Sync
"""

import machine
import time

from machine import Pin
from rp2 import PIO, StateMachine, asm_pio


BLACK = 0b000
BLUE = 0b001
GREEN = 0b010
CYAN = 0b011
RED = 0b100
MAGENTA = 0b101
YELLOW = 0b110
WHITE = 0b111

PATTERN_SECONDS = 8

PATTERN_NAMES = (
    "Rainbow road",
    "Neon mirror",
    "Sunset glow",
    "Ocean glass",
    "Candy lights",
)


def pack_stripes(colours):
    packed = 0
    for index, colour in enumerate(colours):
        packed |= colour << (index * 3)
    return packed


PATTERNS = (
    pack_stripes((RED, YELLOW, GREEN, CYAN, BLUE, MAGENTA, WHITE, RED)),
    pack_stripes((MAGENTA, BLUE, CYAN, WHITE, CYAN, BLUE, MAGENTA, BLACK)),
    pack_stripes((BLUE, MAGENTA, RED, YELLOW, YELLOW, RED, MAGENTA, BLUE)),
    pack_stripes((BLUE, CYAN, WHITE, CYAN, BLUE, GREEN, CYAN, WHITE)),
    pack_stripes((RED, WHITE, MAGENTA, WHITE, CYAN, WHITE, YELLOW, WHITE)),
)


@asm_pio(set_init=PIO.OUT_HIGH)
def hsync_program():
    pull(block)

    wrap_target()
    mov(x, osr)

    # 640 visible + 16 front porch.
    label("active_front")
    jmp(x_dec, "active_front")

    # 96-clock negative H-Sync pulse.
    set(pins, 0) [31]
    set(pins, 0) [31]
    set(pins, 0) [31]

    # Back porch and end-of-line IRQ.
    set(pins, 1) [31]
    set(pins, 1) [13]
    irq(0)
    wrap()


@asm_pio(sideset_init=(PIO.OUT_HIGH,))
def vsync_program():
    pull(block)

    wrap_target()
    mov(x, osr)

    # 480 visible lines.
    label("visible")
    wait(1, irq, 0)
    jmp(x_dec, "visible")

    # 10-line front porch.
    set(y, 9)
    label("front")
    wait(1, irq, 0)
    jmp(y_dec, "front")

    # 2-line negative V-Sync pulse.
    wait(1, irq, 0).side(0)
    wait(1, irq, 0)

    # 33-line back porch.
    set(y, 31)
    label("back")
    wait(1, irq, 0).side(1)
    jmp(y_dec, "back")
    wait(1, irq, 0)
    wrap()


# This 31-instruction RGB program occupies PIO0 by itself. On Pico W, Wi-Fi
# reserves PIO1 SM4, so H/V sync use the remaining PIO1 state machines.
@asm_pio(out_init=(PIO.OUT_LOW,) * 3, out_shiftdir=PIO.SHIFT_RIGHT)
def stripe_program():
    wrap_target()

    # Find H-Sync, then wait through the 48-pixel back porch.
    wait(0, gpio, 14)
    wait(1, gpio, 14)
    set(y, 22)
    label("back_porch_delay")
    jmp(y_dec, "back_porch_delay") [1]

    # Use a new FIFO pattern if present; otherwise reuse X.
    pull(noblock)
    mov(x, osr)

    # Eight stripes. Each group is exactly 80 pixel clocks:
    # out[31] + nop[31] + nop[15] = 32 + 32 + 16.
    out(pins, 3) [31]
    nop() [31]
    nop() [15]

    out(pins, 3) [31]
    nop() [31]
    nop() [15]

    out(pins, 3) [31]
    nop() [31]
    nop() [15]

    out(pins, 3) [31]
    nop() [31]
    nop() [15]

    out(pins, 3) [31]
    nop() [31]
    nop() [15]

    out(pins, 3) [31]
    nop() [31]
    nop() [15]

    out(pins, 3) [31]
    nop() [31]
    nop() [15]

    out(pins, 3) [31]
    nop() [31]
    nop() [15]

    set(pins, 0)
    wrap()


machine.freq(125_000_000)
watchdog = machine.WDT(timeout=8000)
watchdog.feed()

led = Pin("LED", Pin.OUT)
led.on()

stripes = StateMachine(0, stripe_program, freq=25_175_000, out_base=Pin(11))
hsync = StateMachine(5, hsync_program, freq=25_175_000, set_base=Pin(14))
vsync = StateMachine(6, vsync_program, freq=125_000_000, sideset_base=Pin(15))

hsync.put(655)
vsync.put(479)
stripes.put(PATTERNS[0])

# RGB waits for H-Sync edges. V-Sync waits for H-Sync's line IRQ.
stripes.active(1)
vsync.active(1)
hsync.active(1)

print("VGA PIO wallpaper running without DMA")
print("GP11 BLUE, GP12 GREEN, GP13 RED")
print("GP14 H-Sync, GP15 V-Sync")

pattern = 0
while True:
    print("Pattern:", PATTERN_NAMES[pattern])

    for _ in range(PATTERN_SECONDS):
        time.sleep(1)
        watchdog.feed()

    pattern = (pattern + 1) % len(PATTERNS)
    stripes.put(PATTERNS[pattern])
    led.toggle()
