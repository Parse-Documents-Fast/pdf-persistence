import os

# Default MONGO_URL for tests if not set in environment
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
