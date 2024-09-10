import neopixel
import board
import time

# Define constants for the strip
LED_COUNT = 100        # Number of LED pixels
LED_PIN = board.D18    # GPIO pin connected to the pixels
LED_FREQ_HZ = 800000   # LED signal frequency in hertz (usually 800kHz)
LED_DMA = 10           # DMA channel to use for generating signal
LED_BRIGHTNESS = 255   # Set to 0 for darkest and 255 for brightest
LED_INVERT = False     # True to invert the signal (if using common cathode LED strip)
LED_CHANNEL = 0        # GPIO channel

# Initialize the NeoPixel strip
strip = neopixel.NeoPixel(board.D10, 160, brightness=0.2, pixel_order=neopixel.GRB)

def gamma_correct(value, gamma=2.5):
    """Apply gamma correction to a single color value."""
    corrected_value = int((value / 255.0) ** (1.0 / gamma) * 255)
    return min(max(corrected_value, 0), 255)

def hex_to_rgb(hex_color):
    """Convert hex color (int format) to RGB tuple."""
    r = (hex_color >> 16) & 0xFF
    g = (hex_color >> 8) & 0xFF
    b = hex_color & 0xFF
    return (r, g, b)

def display_colors(hex_color, gamma_values):
    """Display various gamma-corrected versions of the color on the LED strip."""
    r, g, b = hex_to_rgb(hex_color)
    
    # Clear the strip
    strip.fill(neopixel.Color(0, 0, 0))
    strip.show()
    
    for i, gamma in enumerate(gamma_values):
        # Apply gamma correction
        r_corr = gamma_correct(r, gamma)
        g_corr = gamma_correct(g, gamma)
        b_corr = gamma_correct(b, gamma)
        
        # Determine the position of this color display
        start_index = (i * LED_COUNT) // len(gamma_values)
        end_index = ((i + 1) * LED_COUNT) // len(gamma_values)
        
        # Set the segment of the strip to the corrected color
        for j in range(start_index, end_index):
            strip[j] = (r_corr, g_corr, b_corr)
        
    strip.show()

# Main script execution
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python script.py <hex_color>")
        sys.exit(1)
    
    # Read the hex color input
    hex_color = int(sys.argv[1], 16)
    
    # Define gamma values to experiment with
    gamma_values = [2.2, 2.4, 2.6, 2.8]
    
    # Display the color variations
    display_colors(hex_color, gamma_values)
    
    print(f"Displaying variations of color {hex(hex_color)} with gamma values {gamma_values}")
    