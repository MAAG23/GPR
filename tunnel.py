import os
import logging
from pyngrok import ngrok, conf
import requests

# Configure logger
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("tunnel")


def setup_ngrok(port):
    """
    Set up an ngrok tunnel to the specified port

    Args:
        port (int): The local port to expose

    Returns:
        str: The public URL of the tunnel
    """
    try:
        # Check if NGROK_AUTH_TOKEN is set
        auth_token = os.getenv("NGROK_AUTH_TOKEN")
        if auth_token:
            ngrok.set_auth_token(auth_token)
            logger.info("Ngrok auth token configured")
        else:
            logger.warning(
                "No Ngrok auth token found. Tunnel will expire after 2 hours.")

        # Create tunnel configuration
        conf.get_default().region = "us"

        # Create HTTP tunnel
        public_url = ngrok.connect(port, "http")
        tunnel_url = public_url.public_url

        logger.info(f"Ngrok tunnel established at: {tunnel_url}")

        # Get tunnel status
        tunnels = ngrok.get_tunnels()
        if tunnels:
            logger.info("Tunnel status: ACTIVE")

        return tunnel_url

    except Exception as e:
        logger.error(f"Failed to establish ngrok tunnel: {str(e)}")
        return None


def get_tunnel_info():
    """Get information about active tunnels"""
    try:
        tunnels = ngrok.get_tunnels()
        return tunnels
    except Exception as e:
        logger.error(f"Failed to get tunnel info: {str(e)}")
        return None


def cleanup_tunnels():
    """Clean up all active tunnels"""
    try:
        ngrok.kill()
        logger.info("All ngrok tunnels terminated")
    except Exception as e:
        logger.error(f"Failed to cleanup tunnels: {str(e)}")
