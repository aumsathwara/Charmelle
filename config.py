import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DB_URL = os.getenv("DB_URL", "postgresql+psycopg2://skin:skin@localhost:5432/skincare")
SECRET_KEY = os.getenv("SECRET_KEY", "change_me") 