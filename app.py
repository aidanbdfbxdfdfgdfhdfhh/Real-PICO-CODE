"""Full-screen VGA gallery: landscape plus five colour wallpapers."""

import machine
import time
import ustruct

from machine import Pin
from rp2 import DMA, PIO, StateMachine, asm_pio


IMAGE_BYTES = 61_440
IMAGE_WORDS = IMAGE_BYTES // 4
SLIDE_SECONDS = 8
BUTTON_DEBOUNCE_MS = 250

BLACK = 0b000
BLUE = 0b001
GREEN = 0b010
CYAN = 0b011
RED = 0b100
MAGENTA = 0b101
YELLOW = 0b110
WHITE = 0b111

SLIDES = (
    ("Landscape", None),
    ("Rainbow road", (RED, YELLOW, GREEN, CYAN, BLUE, MAGENTA, WHITE, RED)),
    ("Neon mirror", (MAGENTA, BLUE, CYAN, WHITE, CYAN, BLUE, MAGENTA, BLACK)),
    ("Sunset glow", (BLUE, MAGENTA, RED, YELLOW, YELLOW, RED, MAGENTA, BLUE)),
    ("Ocean glass", (BLUE, CYAN, WHITE, CYAN, BLUE, GREEN, CYAN, WHITE)),
    ("Candy lights", (RED, WHITE, MAGENTA, WHITE, CYAN, WHITE, YELLOW, WHITE)),
)


@asm_pio(set_init=PIO.OUT_HIGH)
def hsync_program():
    pull(block)
    wrap_target()
    mov(x, osr)
    label("active_front")
    jmp(x_dec, "active_front")
    set(pins, 0) [31]
    set(pins, 0) [31]
    set(pins, 0) [31]
    set(pins, 1) [31]
    set(pins, 1) [13]
    irq(0)
    wrap()


@asm_pio(sideset_init=(PIO.OUT_HIGH,))
def vsync_program():
    pull(block)
    wrap_target()
    mov(x, osr)
    label("visible")
    wait(1, irq, 0)
    jmp(x_dec, "visible")
    set(y, 9)
    label("front")
    wait(1, irq, 0)
    jmp(y_dec, "front")
    wait(1, irq, 0).side(0)
    wait(1, irq, 0)
    set(y, 31)
    label("back")
    wait(1, irq, 0).side(1)
    jmp(y_dec, "back")
    wait(1, irq, 0)
    wrap()


@asm_pio(
    out_init=(PIO.OUT_LOW,) * 3,
    out_shiftdir=PIO.SHIFT_RIGHT,
    autopull=True,
    pull_thresh=30,
)
def image_program():
    # The first FIFO word is the 480-line counter. DMA supplies pixels next.
    pull(block)
    mov(isr, osr)
    pull(block)

    wrap_target()

    # Resynchronise at every V-Sync, then wait through its back porch.
    wait(0, gpio, 15)
    wait(1, gpio, 15)
    set(y, 31)
    label("vertical_back")
    wait(0, gpio, 14)
    wait(1, gpio, 14)
    jmp(y_dec, "vertical_back")

    # Display 480 scanlines. Each source pixel lasts two VGA pixel clocks.
    mov(y, isr)
    label("image_line")
    wait(0, gpio, 14)
    wait(1, gpio, 14)

    # 48-pixel horizontal back porch.
    set(x, 22)
    label("horizontal_back")
    jmp(x_dec, "horizontal_back") [1]

    # 32 words x 10 source pixels x 2 clocks = 640 visible pixels.
    set(x, 31)
    label("image_word")
    out(pins, 3) [1]
    out(pins, 3) [1]
    out(pins, 3) [1]
    out(pins, 3) [1]
    out(pins, 3) [1]
    out(pins, 3) [1]
    out(pins, 3) [1]
    out(pins, 3) [1]
    out(pins, 3) [1]
    out(pins, 3)
    jmp(x_dec, "image_word")

    set(pins, 0)
    jmp(y_dec, "image_line")
    wrap()


def load_landscape(target):
    with open("image_full.bin", "rb") as image_file:
        loaded = image_file.readinto(target)

    if loaded != IMAGE_BYTES:
        raise ValueError("image_full.bin must be exactly 61440 bytes")


def show_stripes(target, colours, enabled_colours=WHITE):
    # Each colour is 40 source pixels, doubled by PIO to 80 VGA pixels.
    line = bytearray(128)
    position = 0
    for colour in colours:
        colour &= enabled_colours
        word = 0
        for pixel in range(10):
            word |= colour << (pixel * 3)
        packed_word = ustruct.pack("<I", word)
        for _ in range(4):
            line[position:position + 4] = packed_word
            position += 4

    for y in range(480):
        start = y * 128
        target[start:start + 128] = line


def apply_colour_mask(target, enabled_colours):
    if enabled_colours == WHITE:
        return

    word_mask = 0
    for pixel in range(10):
        word_mask |= enabled_colours << (pixel * 3)
    mask = ustruct.pack("<I", word_mask)

    for offset in range(0, IMAGE_BYTES, 4):
        target[offset] &= mask[0]
        target[offset + 1] &= mask[1]
        target[offset + 2] &= mask[2]
        target[offset + 3] &= mask[3]


def render_slide(target, slide_number, enabled_colours):
    colours = SLIDES[slide_number][1]
    if colours is None:
        load_landscape(target)
        apply_colour_mask(target, enabled_colours)
    else:
        show_stripes(target, colours, enabled_colours)


machine.freq(125_000_000)
watchdog = machine.WDT(timeout=8000)
watchdog.feed()

image_storage = bytearray(IMAGE_BYTES)
image_view = memoryview(image_storage)

render_slide(image_view, 0, WHITE)
print("Loaded image_full.bin:", IMAGE_BYTES, "bytes")

# Buttons connect their GPIO pin to GND when pressed.
buttons = (
    ("RED", RED, Pin(16, Pin.IN, Pin.PULL_UP)),
    ("GREEN", GREEN, Pin(17, Pin.IN, Pin.PULL_UP)),
    ("BLUE", BLUE, Pin(18, Pin.IN, Pin.PULL_UP)),
)

# RGB owns PIO0. H/V use free PIO1 state machines beside Pico W Wi-Fi.
rgb = StateMachine(0, image_program, freq=25_175_000, out_base=Pin(11))
hsync = StateMachine(5, hsync_program, freq=25_175_000, set_base=Pin(14))
vsync = StateMachine(6, vsync_program, freq=125_000_000, sideset_base=Pin(15))

rgb.put(479)
hsync.put(655)
vsync.put(479)

# Ask MicroPython for a genuinely free DMA channel instead of colliding with
# the Pico W Wi-Fi driver. The state machine object points at its own TX FIFO.
image_dma = DMA()
dma_control = image_dma.pack_ctrl(
    size=2,
    inc_read=True,
    inc_write=False,
    treq_sel=0,
    irq_quiet=False,
)


def restart_image_dma(dma):
    # One finite transfer is exactly one 480-line picture. Restart it while
    # the monitor is in vertical blanking so the next frame starts at line 0.
    dma.read = image_view
    dma.count = IMAGE_WORDS
    dma.active(1)


image_dma.irq(restart_image_dma)
image_dma.config(
    read=image_view,
    write=rgb,
    count=IMAGE_WORDS,
    ctrl=dma_control,
    trigger=True,
)

rgb.active(1)
vsync.active(1)
hsync.active(1)

print("FULL-SCREEN VGA GALLERY RUNNING")
slide = 0
enabled_colours = WHITE
last_button_states = [button.value() for _, _, button in buttons]
last_button_presses = [time.ticks_add(time.ticks_ms(), -BUTTON_DEBOUNCE_MS)] * 3
next_slide = time.ticks_add(time.ticks_ms(), SLIDE_SECONDS * 1000)

while True:
    now = time.ticks_ms()

    for index, (name, colour_bit, button) in enumerate(buttons):
        state = button.value()
        if (
            state == 0
            and last_button_states[index] == 1
            and time.ticks_diff(now, last_button_presses[index])
            >= BUTTON_DEBOUNCE_MS
        ):
            enabled_colours ^= colour_bit
            last_button_presses[index] = now
            render_slide(image_view, slide, enabled_colours)
            status = "ON" if enabled_colours & colour_bit else "OFF"
            print(name, status)
        last_button_states[index] = state

    if time.ticks_diff(now, next_slide) >= 0:
        slide = (slide + 1) % len(SLIDES)
        render_slide(image_view, slide, enabled_colours)
        print("Slide:", SLIDES[slide][0])
        next_slide = time.ticks_add(now, SLIDE_SECONDS * 1000)

    watchdog.feed()
    time.sleep_ms(20)
