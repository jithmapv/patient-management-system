from app.database import engine
from sqlalchemy import text

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print("PostgreSQL connection successful:", result.scalar())

except Exception as e:
    print("Database connection failed:")
    print(e)