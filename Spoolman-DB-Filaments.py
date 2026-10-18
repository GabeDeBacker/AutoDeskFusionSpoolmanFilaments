import importlib
import os
import sys

# Insert module path into the Python search path for imports.
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

import spoolman_database_filament_colors

def run(_context):
    """Fusion add-in startup hook: register command and open the main palette."""
    importlib.reload(spoolman_database_filament_colors)
    spoolman_database_filament_colors.run(_context)
    


def stop(_context):
    """Fusion add-in shutdown hook: remove palettes, controls, and command."""
    importlib.reload(spoolman_database_filament_colors)
    spoolman_database_filament_colors.stop(_context)
