"""Fusion add-in entrypoint for the Spoolman DB Filament Colors module."""
import os
import sys
import gc

# Insert module path into the Python search path for imports.
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

import spoolman_database_filament_colors

def run(_context):
    """Fusion add-in startup hook: register command and open the main palette."""
    spoolman_database_filament_colors.run(_context)

def stop(_context):
    """Fusion add-in shutdown hook: remove palettes, controls, and command."""
    spoolman_database_filament_colors.stop(_context)
    gc.collect()
