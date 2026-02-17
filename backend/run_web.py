#!/usr/bin/env python3
"""
Run the CloudForge Bug Intelligence web dashboard.

This script starts the Flask web server for the dashboard interface.
No Node.js required - runs entirely with Python!

Usage:
    python run_web.py
    
Then open your browser to: http://localhost:5000
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cloudforge.web.app import run_app

if __name__ == '__main__':
    print("=" * 60)
    print("CloudForge Bug Intelligence - Web Dashboard")
    print("=" * 60)
    print("\nStarting Flask web server...")
    print("Once started, open your browser to: http://localhost:5000")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60)
    print()
    
    run_app(host='0.0.0.0', port=5000, debug=True)
