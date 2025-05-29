from dotenv import load_dotenv
import os


load_dotenv()

class Config:
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    UPSPLASH_VECTOR_DATABASE_TOKEN: str  = os.getenv("UPSPLASH_VECTOR_DATABASE_TOKEN")
    UPSTASH_URL: str = os.getenv("UPSTASH_URL")
