#!/usr/bin/env python3
"""Launcher for the Dance GUI application."""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the dance GUI
from dance_gui import DanceManagerApp

if __name__ == "__main__":
    app = DanceManagerApp()
    app.mainloop()
