import time
import board
import neopixel

pixels = neopixel.NeoPixel(board.D10, 10)
pixels.fill((0, 255, 0))
time.sleep(3)
while(True):
    for i in range(10):
        pixels.fill((0, 0, 0))
        pixels[i] = (255, 0, 0)
        time.sleep(1)
    print('sleep')
    time.sleep(1)