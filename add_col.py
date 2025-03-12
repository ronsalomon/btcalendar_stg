import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env file, if available.
load_dotenv()

# Get the database URL from environment variables.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://btwpcaldb_user:5tBjRRmg6AlRyxxyCvCpI6mmbZMqQEd7@dpg-cv7qsaij1k6c739h9mmg-a.virginia-postgres.render.com/btwpcaldb"
)

def add_organizer_column():
    """Connect to the database and add the 'organizer' column to the events table."""
    try:
        # Establish database connection.
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Execute the ALTER TABLE command.
        alter_query = "ALTER TABLE events ADD COLUMN organizer TEXT;"
        cur.execute(alter_query)
        
        # Commit the change.
        conn.commit()
        print("Column 'organizer' added successfully.")
        
    except Exception as e:
        print("Error adding column 'organizer':", e)
        if conn:
            conn.rollback()
    finally:
        # Clean up and close the connection.
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    add_organizer_column()
