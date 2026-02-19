"""
CloudForge Bug Intelligence - Main Entry Point

This module provides the main entry point for running the CloudForge platform.
"""

import logging
import sys
from cloudforge.web.app import app
from cloudforge.utils.logging_config import setup_logging


def main():
    """Main entry point for CloudForge Bug Intelligence."""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting CloudForge Bug Intelligence platform")
    
    try:
        # Run Flask web application
        app.run(
            host="0.0.0.0",
            port=5000,
            debug=False
        )
    except Exception as e:
        logger.error(f"Failed to start CloudForge: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
