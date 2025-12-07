#!/usr/bin/env python3
"""Launcher for the Copperknob Import GUI application."""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the copperknob import GUI
from copperknob_import_gui import CopperknobImportGUI

if __name__ == "__main__":
    app = CopperknobImportGUI()
    app.mainloop()
