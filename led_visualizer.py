"""
Terminal-based LED strip visualizer for debugging without hardware.

Provides FakeNeoPixel class that mimics the neopixel.NeoPixel interface
and renders LED states as colored blocks in the terminal.
"""

import sys
import os


class FakeNeoPixel:
    """
    Mock NeoPixel strip that stores colors in memory and can render to terminal.
    Implements the same interface as neopixel.NeoPixel.
    """

    def __init__(self, pin, num_leds, brightness=1.0, auto_write=False, pixel_order=None):
        self.pin = pin
        self.num_leds = num_leds
        self.brightness = brightness
        self.auto_write = auto_write
        self.pixel_order = pixel_order
        self._pixels = [(0, 0, 0)] * num_leds
        self._name = f"Strip@{pin}"

    def __setitem__(self, index, color):
        if isinstance(color, int):
            # Handle hex color like 0xFF0000
            r = (color >> 16) & 0xFF
            g = (color >> 8) & 0xFF
            b = color & 0xFF
            color = (r, g, b)
        self._pixels[index] = color

    def __getitem__(self, index):
        return self._pixels[index]

    def __len__(self):
        return self.num_leds

    def fill(self, color):
        if isinstance(color, int):
            r = (color >> 16) & 0xFF
            g = (color >> 8) & 0xFF
            b = color & 0xFF
            color = (r, g, b)
        for i in range(self.num_leds):
            self._pixels[i] = color

    def show(self):
        # No-op for fake strip; rendering is done separately
        pass


class LEDVisualizer:
    """
    Renders multiple FakeNeoPixel strips to the terminal.
    """

    def __init__(self):
        self.strips = {}  # name -> FakeNeoPixel
        self._last_render_lines = 0

    def register_strip(self, name, strip):
        """Register a strip for visualization."""
        self.strips[name] = strip

    def _color_block(self, r, g, b):
        """Return a colored block using ANSI 24-bit color."""
        if r == 0 and g == 0 and b == 0:
            return "\033[48;2;20;20;20m \033[0m"  # Dark gray for "off"
        return f"\033[48;2;{r};{g};{b}m \033[0m"

    def _format_strip_line(self, name, strip, width=80):
        """Format a single strip as a line of colored blocks."""
        blocks = []
        # Show every Nth LED to fit in terminal width
        step = max(1, len(strip) // (width - 10))

        for i in range(0, len(strip), step):
            color = strip[i]
            if isinstance(color, tuple):
                r, g, b = color
            else:
                r = (color >> 16) & 0xFF
                g = (color >> 8) & 0xFF
                b = color & 0xFF
            blocks.append(self._color_block(r, g, b))

        return f"{name:>8}: {''.join(blocks)}"

    def _move_cursor_up(self, lines):
        """Move cursor up N lines."""
        if lines > 0:
            sys.stdout.write(f"\033[{lines}A")

    def render(self, clear_previous=True):
        """Render all strips to terminal."""
        try:
            term_width = os.get_terminal_size().columns
        except OSError:
            term_width = 80

        if clear_previous and self._last_render_lines > 0:
            self._move_cursor_up(self._last_render_lines)

        lines = []
        lines.append("\033[1m=== LED Strip Visualizer ===\033[0m")

        for name, strip in sorted(self.strips.items()):
            lines.append(self._format_strip_line(name, strip, term_width - 2))

        # Add legend
        lines.append(
            f"  Legend: "
            f"{self._color_block(0, 255, 0)}=vehicle "
            f"{self._color_block(127, 18, 0)}=station "
            f"{self._color_block(255, 0, 0)}=disabled "
            f"{self._color_block(0, 0, 0)}=off"
        )

        output = "\n".join(lines)
        print(output)
        self._last_render_lines = len(lines)


# Global visualizer instance
_visualizer = None


def get_visualizer():
    """Get or create the global visualizer instance."""
    global _visualizer
    if _visualizer is None:
        _visualizer = LEDVisualizer()
    return _visualizer


def create_fake_strip(pin, num_leds, **kwargs):
    """
    Create a FakeNeoPixel strip and register it with the visualizer.
    Returns the strip instance.
    """
    strip = FakeNeoPixel(pin, num_leds, **kwargs)
    visualizer = get_visualizer()
    visualizer.register_strip(str(pin), strip)
    return strip


def render():
    """Render all registered strips to the terminal."""
    visualizer = get_visualizer()
    visualizer.render()
