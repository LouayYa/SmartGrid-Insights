import os
from dotenv import load_dotenv

load_dotenv()

COLLECTION_SERVICE_URL = os.getenv("COLLECTION_SERVICE_URL","http://localhost:8002")
ANALYSIS_SERVICE_URL = os.getenv("ANALYSIS_SERVICE_URL","http://localhost:8003")
METER_SERVICE_URL = os.getenv("METER_SERVICE_URL","http://localhost:8000")