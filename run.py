import os
import sys
import subprocess
import time
import signal
import logging
from tunnel import setup_ngrok, cleanup_tunnels
import atexit

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("runner")


def cleanup():
    """Cleanup function to be called on exit"""
    logger.info("Cleaning up...")
    cleanup_tunnels()


def run_app():
    """Run the Streamlit app with ngrok tunnel"""
    try:
        # Register cleanup function
        atexit.register(cleanup)

        # Default Streamlit port
        port = 8501

        # Start Streamlit in a separate process
        streamlit_cmd = [sys.executable, "-m", "streamlit", "run", "app.py"]
        process = subprocess.Popen(streamlit_cmd)

        # Wait for Streamlit to start
        logger.info("Waiting for Streamlit to start...")
        time.sleep(5)

        # Set up ngrok tunnel
        tunnel_url = setup_ngrok(port)
        if tunnel_url:
            logger.info("-" * 50)
            logger.info("🎉 Application is now running!")
            logger.info(f"Local URL: http://localhost:{port}")
            logger.info(f"Public URL: {tunnel_url}")
            logger.info("-" * 50)

            # Keep the script running
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                process.terminate()
                cleanup()
        else:
            logger.error("Failed to establish ngrok tunnel")
            process.terminate()

    except Exception as e:
        logger.error(f"Error running app: {str(e)}")
        cleanup()
        sys.exit(1)


if __name__ == "__main__":
    run_app()
