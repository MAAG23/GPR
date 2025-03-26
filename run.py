import os
import sys
import subprocess
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
    """Run the Streamlit app with optional ngrok tunnel"""
    try:
        # Register cleanup function
        atexit.register(cleanup)

        # Default Streamlit port
        port = 8501

        # Try to set up ngrok tunnel, but don't fail if it doesn't work
        try:
            tunnel_url = setup_ngrok(port)
            if tunnel_url:
                logger.info("-" * 70)
                logger.info("🎉 Setting up remote access...")
                logger.info(f"Local URL: http://localhost:{port}")

                # Show both HTTP and HTTPS URLs
                if tunnel_url.startswith("https://"):
                    http_url = tunnel_url.replace("https://", "http://")
                    logger.info(f"Public URLs:")
                    logger.info(f"  HTTPS: {tunnel_url}")
                    logger.info(
                        f"  HTTP:  {http_url} (use this if HTTPS doesn't work)")
                else:
                    logger.info(f"Public URL: {tunnel_url}")

                logger.info("\nTroubleshooting Tips:")
                logger.info("1. Try the HTTP URL if HTTPS doesn't work")
                logger.info(
                    "2. If on a corporate network, try a personal network")
                logger.info("3. Make sure your firewall allows the connection")
                logger.info("-" * 70)
        except Exception as e:
            logger.warning(f"Remote access (ngrok) not available: {str(e)}")
            logger.info(f"Local access only at: http://localhost:{port}")

        # Start Streamlit
        logger.info("Starting the application...")
        streamlit_cmd = [sys.executable, "-m", "streamlit", "run", "app.py"]
        process = subprocess.run(streamlit_cmd)

        # Cleanup when the app is closed
        cleanup()

    except KeyboardInterrupt:
        logger.info("Shutting down...")
        cleanup()
    except Exception as e:
        logger.error(f"Error running app: {str(e)}")
        cleanup()
        sys.exit(1)


if __name__ == "__main__":
    run_app()
