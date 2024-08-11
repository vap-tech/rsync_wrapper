import os
from dotenv import load_dotenv

load_dotenv()

DEBUG = os.getenv("DEBUG") == "True"

SOURCE = os.getenv("SOURCE")
DESTINATION = os.getenv("DESTINATION")
