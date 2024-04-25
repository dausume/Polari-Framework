import os
import importlib
import logging

logging.basicConfig(level=logging.WARNING)

def check_modules():
    requirements_path = os.path.join(os.path.dirname(__file__), '..', 'requirements.txt')
    with open(requirements_path, 'r') as f:
        for line in f:
            module_name = line.strip()
            try:
                importlib.import_module(module_name)
                logging.info(f"Module '{module_name}' imported successfully.")
            except ImportError:
                logging.warning(f"Module '{module_name}' not found.")
