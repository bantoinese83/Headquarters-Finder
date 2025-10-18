#!/usr/bin/env python3
"""
Main entry point for Headquarters Finder application.

This script serves as the main entry point for the Headquarters Finder
application, providing command-line interface and orchestration.
"""

import sys
import os
from pathlib import Path

# Add the headquarters_finder package to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from headquarters_finder.main import HeadquartersFinderApp


def main():
    """Main entry point for the application."""
    try:
        # Import the main function from the headquarters_finder package
        from headquarters_finder.main import main as headquarters_main
        headquarters_main()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
