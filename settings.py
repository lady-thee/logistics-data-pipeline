from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    api_key: str

    class Config:
        env_file = ".env"


OUTPUT_FILE = BASE_DIR / "files/output.xlsx"
INPUT_FILE = BASE_DIR / "files/FREIGHT DISTANCE.xlsx"
INPUT_FILE_CSV = BASE_DIR / "files/FREIGHT DISTANCE.csv"