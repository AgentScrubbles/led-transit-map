import neopixel
import board
import time

# Define constants for the strip
LED_COUNT = 100        # Number of LED pixels
LED_PIN = board.D18    # GPIO pin connected to the pixels
LED_FREQ_HZ = 400000   # LED signal frequency in hertz (usually 800kHz)
LED_DMA = 10           # DMA channel to use for generating signal
LED_BRIGHTNESS = 255   # Set to 0 for darkest and 255 for brightest
LED_INVERT = False     # True to invert the signal (if using common cathode LED strip)
LED_CHANNEL = 0        # GPIO channel

# Initialize the NeoPixel strip
strip = neopixel.NeoPixel(board.D10, 160, brightness=0.8, pixel_order=neopixel.GRB)

def gamma_correct(value, gamma=2.5):
    """Apply gamma correction to a single color value."""
    if gamma == 0:
        return 0
    corrected_value = (value / 255.0) ** (1.0 / gamma) * 255
    print("Corrected: {}".format(corrected_value))
    return min(max(int(corrected_value), 0), 255)

def hex_to_rgb(hex_color):
    """Convert hex color (int format) to RGB tuple."""
    r = (hex_color >> 16) & 0xFF
    g = (hex_color >> 8) & 0xFF
    b = hex_color & 0xFF
    return (r, g, b)

def display_colors(r, g, b, gamma_correction):
    
    # Clear the strip
    strip.fill((0, 0, 0))
    strip.show()

    counter = 0
    current_gamma = 0
    max_gamma = 3.6
    step = max_gamma / LED_COUNT
    while current_gamma < max_gamma:
        r_corr = gamma_correct(r, current_gamma)
        g_corr = gamma_correct(g, current_gamma)
        b_corr = gamma_correct(b, current_gamma)
        strip[counter] = (r_corr, g_corr, b_corr)
        print ('Gamma: {} ({}, {}, {})'.format(current_gamma, r_corr, g_corr, b_corr))
        current_gamma = current_gamma + step
        counter = counter + 1
        
        
    strip.show()

# Main script execution
if __name__ == "__main__":
    import sys
    
    # Read the hex color input
    r = int(sys.argv[1], 16)
    g = int(sys.argv[2], 16)
    b = int(sys.argv[3], 16)
    
    # Define gamma values to experiment with
    gamma_values = [2.2, 2.4, 2.6, 2.8]
    
    # Display the color variations
    display_colors(r, g, b, gamma_values)
    
    print(f"Displaying variations of color ({r} {g} {b}) with gamma values {gamma_values}")
    
