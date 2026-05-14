import sys
from loguru import logger

# Configure logger
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)

logger.add(
    "logs/app.log",
    rotation="500 MB",
    retention="10 days",
    level="DEBUG"
)


def get_logger(name: str):
    """Get logger for specific module"""
    return logger.bind(name=name)
