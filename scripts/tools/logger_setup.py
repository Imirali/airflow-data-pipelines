import sys
import os
from loguru import logger

path = os.path.join("C:\\", "imir_docs", "airflow-data-pipelines", "logs", "logs.log")

logger.remove()

logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
)
logger.add(
    path,
    rotation="10 MB",
    encoding="utf-8",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
)
