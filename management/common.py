import logging
import os
import sys

fc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(fc_path)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
