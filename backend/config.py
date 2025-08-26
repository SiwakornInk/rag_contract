import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database
    USE_READONLY_USER = os.getenv('USE_READONLY_USER', 'false').lower() == 'true'
    SQL_READ_ONLY_USER = os.getenv('SQL_READ_ONLY_USER')
    SQL_READ_ONLY_PASSWORD = os.getenv('SQL_READ_ONLY_PASSWORD')
    
    # Features
    USE_SQL_SEARCH = True
    DEFAULT_TOP_K = 15