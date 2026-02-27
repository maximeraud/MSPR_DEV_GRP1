import typer
import mariadb
app = typer.Typer()

@app.command("run")
def run():
    """Diagnostic (placeholder)."""
    print("TODO: module 1 diagnostic")


# Connection parameters
db_config = {
    'user': 'admin',
    'password': 'admin',
    'host': '172.16.135.60',
    'port': 3306,
    'database': 'diagTest'
}

conn = None
cursor = None

try:
    # Establish connection
    conn = mariadb.connect(**db_config)
    print("Connected successfully!")

    # Create a cursor
    cursor = conn.cursor()

    # Execute a query
    cursor.execute("SELECT * FROM contacts")
    results = cursor.fetchall()

    # Display results
    for row in results:
        print(row)

except mariadb.Error as err:
    print(f"Error: {err}")

finally:
    # Close connection and cursor safely
    if cursor is not None:
        cursor.close()
    if conn is not None:
        conn.close()