from machine import Pin
from time import sleep

morse_code_dict = {
    "A": ".-",
    "B": "-...",
    "C": "-.-.",
    "D": "-..",
    "E": ".",
    "F": "..-.",
    "G": "--.",
    "H": "....",
    "I": "..",
    "J": ".---",
    "K": "-.-",
    "L": ".-..",
    "M": "--",
    "N": "-.",
    "O": "---",
    "P": ".--.",
    "Q": "--.-",
    "R": ".-.",
    "S": "...",
    "T": "-",
    "U": "..-",
    "V": "...-",
    "W": ".--",
    "X": "-..-",
    "Y": "-.--",
    "Z": "--..",
    "0": "-----",
    "1": ".----",
    "2": "..---",
    "3": "...--",
    "4": "....-",
    "5": ".....",
    "6": "-....",
    "7": "--...",
    "8": "---..",
    "9": "----.",
}

led = Pin(1, Pin.OUT)

UNIT = 0.5


def flash(symbol):
    led.on()

    if symbol == ".":
        sleep(UNIT)
    else:
        sleep(UNIT * 3)

    led.off()


def morse_code(sentence):
    words = sentence.upper().split()

    try:
        for word_number, word in enumerate(words):
            letters = [letter for letter in word if letter in morse_code_dict]

            for letter_number, letter in enumerate(letters):
                symbols = morse_code_dict[letter]

                for symbol_number, symbol in enumerate(symbols):
                    flash(symbol)

                    if symbol_number < len(symbols) - 1:
                        sleep(UNIT)       # Gap between dots and dashes

                if letter_number < len(letters) - 1:
                    sleep(UNIT * 3)       # Gap between letters

            if word_number < len(words) - 1:
                sleep(UNIT * 7)           # Gap between words
    finally:
        led.off()


message = "SOS"
morse_code(message)
