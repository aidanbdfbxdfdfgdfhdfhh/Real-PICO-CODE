"""640x480 VGA wallpaper demo for Raspberry Pi Pico.

The PIO and DMA layout is adapted from HughMaingauche's
PICO-VGA-Micropython project.  Five generated patterns rotate forever.

GP11 -> blue, GP12 -> green, GP13 -> red
GP14 -> H-Sync, GP15 -> V-Sync
"""

import gc
import machine
import micropython
import time

from array import array
from machine import Pin
from micropython import const
from rp2 import PIO, StateMachine, asm_pio
from uctypes import addressof


WIDTH = const(640)
HEIGHT = const(480)
TILE_HEIGHT = const(64)
PIXELS_PER_WORD = const(10)
WORDS_PER_LINE = const(64)
TILE_WORDS = const(4_096)

HSYNC_FREQ = const(25_175_000)
VSYNC_FREQ = const(125_000_000)
RGB_FREQ = const(100_700_000)
PATTERN_SECONDS = const(8)

# Bits leave the PIO on GP11, GP12 and GP13 in that order.
BLACK = const(0b000)
BLUE = const(0b001)
GREEN = const(0b010)
CYAN = const(0b011)
RED = const(0b100)
MAGENTA = const(0b101)
YELLOW = const(0b110)
WHITE = const(0b111)

PATTERN_NAMES = (
    "Diagonal rainbow tiles",
    "Neon diamond wallpaper",
    "Concentric colour frames",
    "Pixel constellation",
    "Moving zigzag waves",
)


@asm_pio(set_init=PIO.OUT_HIGH)
def hsync_program():
    pull(block)

    wrap_target()
    mov(x, osr)

    # 640 visible + 16 front porch. mov + loop = 657 clocks.
    label("active_front")
    jmp(x_dec, "active_front")

    # 96-clock negative H-Sync pulse.
    set(pins, 0) [31]
    set(pins, 0) [31]
    set(pins, 0) [31]

    # 48-clock back porch, including the line IRQ and wrap.
    set(pins, 1) [31]
    set(pins, 1) [13]
    irq(0)
    wrap()


@asm_pio(sideset_init=(PIO.OUT_HIGH,))
def vsync_program():
    pull(block)

    wrap_target()
    mov(x, osr)

    # 480 visible lines. IRQ 1 releases one RGB scanline.
    label("visible")
    wait(1, irq, 0)
    irq(1)
    jmp(x_dec, "visible")

    # 10-line front porch.
    set(y, 9)
    label("front_porch")
    wait(1, irq, 0)
    jmp(y_dec, "front_porch")

    # 2-line negative V-Sync pulse.
    wait(1, irq, 0).side(0)
    wait(1, irq, 0)

    # 33-line back porch.
    set(y, 31)
    label("back_porch")
    wait(1, irq, 0).side(1)
    jmp(y_dec, "back_porch")
    wait(1, irq, 0)
    wrap()


@asm_pio(
    out_init=(PIO.OUT_LOW,) * 3,
    out_shiftdir=PIO.SHIFT_RIGHT,
    sideset_init=(PIO.OUT_LOW,) * 3,
    autopull=True,
    pull_thresh=30,
)
def rgb_program():
    # Python places the 639-pixel loop count first in the FIFO.
    pull(block)
    mov(y, osr)

    # DMA supplies the first 10-pixel framebuffer word.
    pull(block)

    wrap_target()
    mov(x, y).side(0)
    wait(1, irq, 1)

    label("pixels")
    out(pins, 3)
    nop() [1]
    jmp(x_dec, "pixels")
    wrap()


@micropython.viper
def render_pattern(pattern: int):
    """Generate one 640x64 wallpaper tile, repeated down the screen."""
    data = ptr32(tile_address)
    y = 0

    while y < 64:
        word_x = 0

        while word_x < 64:
            packed = 0
            pixel = 0

            while pixel < 10:
                x = word_x * 10 + pixel
                colour = 0

                if pattern == 0:
                    # Slanted rainbow tiles with bright grout lines.
                    tile = ((x // 40) + (y // 30)) % 7
                    colour = tile + 1
                    if ((x + y) % 80) < 3:
                        colour = 7

                elif pattern == 1:
                    # Repeating neon diamonds on a dark background.
                    dx = (x % 80) - 40
                    dy = (y % 80) - 40
                    if dx < 0:
                        dx = 0 - dx
                    if dy < 0:
                        dy = 0 - dy
                    distance = dx + dy
                    if distance < 19:
                        colour = 3
                    elif distance < 24:
                        colour = 7
                    elif distance < 34:
                        colour = 5
                    else:
                        colour = 1

                elif pattern == 2:
                    # Nested rectangular colour frames in each tile.
                    dx = x - 320
                    dy = y - 32
                    if dx < 0:
                        dx = 0 - dx
                    if dy < 0:
                        dy = 0 - dy
                    edge = dx
                    if dy > edge:
                        edge = dy
                    band = edge // 22
                    colour = (band % 7) + 1
                    if (edge % 22) < 3:
                        colour = 7

                elif pattern == 3:
                    # Pixel constellation with bright crossing stars.
                    sparkle = (x * 17 + y * 31 + x * y) % 251
                    if sparkle < 2:
                        colour = 7
                    elif sparkle == 7:
                        colour = 3
                    elif ((x + y * 3) % 193) < 3:
                        colour = 5
                    else:
                        colour = 0

                else:
                    # Repeating zigzag waves with dark separators.
                    phase = (x + (y // 12) * 18) % 168
                    if phase >= 84:
                        phase = 167 - phase
                    colour = ((phase // 12) % 7) + 1
                    if (y % 72) < 3:
                        colour = 0

                packed |= colour << (pixel * 3)
                pixel += 1

            data[y * 64 + word_x] = packed
            word_x += 1

        y += 1


def configure_dma():
    """Configure one paced DMA over an aligned 16 KiB read ring."""
    irq_quiet = 0
    ring_select = 0
    ring_size = 0
    high_priority = 0
    increment_write = 0
    data_size = 2
    enabled = 1

    # Channel 1 continuously transfers the 64-line tile to PIO0 SM2.
    # A 16 KiB read ring repeats the tile with no control-channel chaining.
    dreq = 2
    increment_read = 1
    chain_to = 1
    ring_select = 0
    ring_size = 14
    control = (
        (irq_quiet << 21)
        | (dreq << 15)
        | (chain_to << 11)
        | (ring_select << 10)
        | (ring_size << 6)
        | (increment_write << 5)
        | (increment_read << 4)
        | (data_size << 2)
        | (high_priority << 1)
        | enabled
    )

    machine.mem32[0x50000040] = tile_address
    machine.mem32[0x50000044] = 0x50200018
    machine.mem32[0x50000048] = 0xFFFFFFFF
    machine.mem32[0x50000060] = control



def restart_rgb_dma():
    """Restart the long transfer after changing a wallpaper tile."""
    machine.mem32[0x50000444] = 0b0010
    machine.mem32[0x50000040] = tile_address
    machine.mem32[0x50000048] = 0xFFFFFFFF
    machine.mem32[0x50000430] = 0b0010


machine.freq(125_000_000)
led = Pin("LED", Pin.OUT)
led.on()

# Hardware failsafe: if a DMA test ever starves MicroPython, the Pico resets
# itself instead of requiring its USB cable to be unplugged.
watchdog = machine.WDT(timeout=8000)
watchdog.feed()

gc.collect()

# Allocate twice the tile size so an aligned 16 KiB region always exists.
tile_storage = array("L")
for _ in range(TILE_WORDS * 2):
    tile_storage.append(0)
storage_address = addressof(tile_storage)
tile_address = (storage_address + 0x3FFF) & ~0x3FFF

print("Wallpaper tile ready:", TILE_WORDS, "words")
render_pattern(0)

hsync = StateMachine(0, hsync_program, freq=HSYNC_FREQ, set_base=Pin(14))
vsync = StateMachine(1, vsync_program, freq=VSYNC_FREQ, sideset_base=Pin(15))
rgb = StateMachine(
    2,
    rgb_program,
    freq=RGB_FREQ,
    out_base=Pin(11),
    sideset_base=Pin(11),
)

hsync.put(655)
vsync.put(479)
rgb.put(639)

configure_dma()

# Start DMA channel 1, then atomically enable PIO0 state machines 0, 1 and 2.
machine.mem32[0x50000430] = 0b0010
machine.mem32[0x50200000] |= 0b0111

print("VGA RGB wallpaper running")
print("GP11 BLUE, GP12 GREEN, GP13 RED")
print("GP14 H-Sync, GP15 V-Sync")

pattern = 0
while True:
    print("Pattern:", PATTERN_NAMES[pattern])

    for _ in range(PATTERN_SECONDS):
        time.sleep(1)
        watchdog.feed()

    pattern = (pattern + 1) % len(PATTERN_NAMES)
    render_pattern(pattern)
    restart_rgb_dma()
    led.toggle()
