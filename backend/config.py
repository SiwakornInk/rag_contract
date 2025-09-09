import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Core database connection (Oracle Free thin driver)
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_HOST = os.getenv('DB_HOST', 'oracle-db')
    DB_PORT = int(os.getenv('DB_PORT', '1521'))
    DB_SERVICE = os.getenv('DB_SERVICE', 'FREEPDB1')

    # Features
    USE_SQL_SEARCH = True
    DEFAULT_TOP_K = 15

    @classmethod
    def build_dsn(cls) -> str:
        # Easy thin format host:port/service_name
        return f"{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_SERVICE}"
