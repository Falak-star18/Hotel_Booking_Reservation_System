import shutil
from pathlib import Path

# Get the project directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Original database
original_db = BASE_DIR / "database" / "hotel.db"

# Temporary testing database
test_db = BASE_DIR / "database" / "hotel_test.db"

# Copy the original database
shutil.copy2(original_db, test_db)

print("Test database created successfully!")
print(f"Location: {test_db}")