import logging
import os
from datetime import datetime

# Ensure logs directory exists
os.makedirs("data/logs", exist_ok=True)

# Generate log filename with timestamp
log_file = f"data/logs/app_{datetime.now().strftime('%Y%m%d')}.log"

# Configure root logger - simpler format and only INFO level
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

# Simple logger for all modules
logger = logging.getLogger('app')

# Get logger instances for different modules
rastreio_logger = logging.getLogger('rastreio')
captura_logger = logging.getLogger('captura')
zip_logger = logging.getLogger('zip')

# Log start of application
logger.info(f"Iniciando aplicação com log em: {log_file}") 