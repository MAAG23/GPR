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
        str: The public URL of the tunnel, or None if setup fails
    """
    # Check if NGROK_AUTH_TOKEN is set
    auth_token = os.getenv("NGROK_AUTH_TOKEN")
    if not auth_token:
        logger.warning("Ngrok auth token not found in .env file")
        logger.info("To enable remote access:")
        logger.info("1. Sign up at https://dashboard.ngrok.com/signup")
        logger.info(
            "2. Get your auth token from https://dashboard.ngrok.com/get-started/your-authtoken")
        logger.info(
            "3. Add it to your .env file as NGROK_AUTH_TOKEN=your_token_here")
        return None

    try:
        # Configure ngrok with auth token
        ngrok.set_auth_token(auth_token)
        logger.info("Ngrok auth token configured")

        # Create tunnel configuration
        config = {
            "bind_tls": True,  # Force HTTPS/TLS
            "inspect": True,   # Enable inspection
        }

        # Create HTTP tunnel with configuration
        public_url = ngrok.connect(f"localhost:{port}", **config)
        tunnel_url = public_url.public_url

        logger.info(f"Ngrok tunnel established at: {tunnel_url}")
        logger.info(
            "Note: If you're behind a corporate firewall or using Fortinet, you may need to:")
        logger.info(
            "1. Use a personal network instead of corporate/school network")
        logger.info("2. Add an exception in Fortinet for this domain")
        logger.info(
            "3. Access via http:// instead of https:// if SSL issues persist")

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
