import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(name)s.%(funcName)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("cloner.log"),
        logging.StreamHandler()
    ]
)