import time
import board
import neopixel_spi


pixels = neopixel_spi.NeoPixel_SPI(board.SPI(), 10)

pixels.fill(0xff0000)
for i in range(10):
    pixels.fill(0x000000)
    pixels[i] = 0x00ff00
    time.sleep(1)
