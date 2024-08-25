import time
import board
import neopixel

pixels = neopixel.NeoPixel(board.GPIO10, 10)
pixels.fill((0, 255, 0))