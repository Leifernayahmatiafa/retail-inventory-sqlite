import sqlite3

# Define a single source of truth for the local database filename.
# SQLite creates this file in the local directory if it does not already exist.
DATABASE_NAME = "inventory.db"


def get_connection():
    """
    Establish and return an active connection to the SQLite database.
    Separating connection logic prevents duplicate code across CRUD functions.
    """
    conn = sqlite3.connect(DATABASE_NAME)
    return conn


def init_db():
    """
    Database Initialization:
    Ensures tables exist before any read/write operations execute.
    Using 'IF NOT EXISTS' prevents runtime crashes on subsequent launches.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Schema Design & Constraints:
    # 1. AUTOINCREMENT: Automatically manages surrogate primary keys for row identification.
    # 2. UNIQUE on 'sku': Guarantees stock-keeping units remain distinct at the database level.
    # 3. NOT NULL: Enforces strict data completeness; prevents partial/corrupt record entries.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL
        )
    """)

    # Commit the transaction to disk and close the resource
    conn.commit()
    conn.close()


def add_product(sku, name, category, quantity, price):
    """
    Create Operation (CRUD):
    Inserts a new product record using parameterized SQL execution.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Security Measure - Parameterized Queries:
        # We pass values as a tuple into '?' placeholders instead of string formatting (f-strings).
        # This forces the SQL engine to treat inputs purely as literal data, completely
        # neutralizing SQL Injection vulnerabilities.
        cursor.execute("""
            INSERT INTO products (sku, name, category, quantity, price)
            VALUES (?, ?, ?, ?, ?)
        """, (sku, name, category, quantity, price))

        conn.commit()
        print(f"[SUCCESS] Added product '{name}' (SKU: {sku}) to catalog.")

    except sqlite3.IntegrityError:
        # Defensive Programming:
        # If an identical SKU is inserted, SQLite raises an IntegrityError due to the UNIQUE constraint.
        # We catch it gracefully here rather than allowing the application to crash unexpectedly.
        print(f"[CONFLICT] Skipped: SKU '{sku}' already exists in the system.")

    finally:
        # Ensure database handles are closed even if an exception occurs
        conn.close()


def list_products():
    """
    Read Operation (CRUD):
    Retrieves all records from the database and formats them into a clean terminal view.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Query only the required columns in an explicit order rather than using SELECT *
    cursor.execute("SELECT sku, name, category, quantity, price FROM products")
    items = cursor.fetchall()
    conn.close()

    # Early return guard clause if the database has no rows
    if not items:
        print("\n[INFO] No products found in the inventory database.")
        return

    # Dynamic column formatting:
    # Uses string alignment specifiers (<10, <22) to produce structured tabular CLI output
    print("\n" + "=" * 68)
    print(f"{'SKU':<10} {'Product Name':<22} {'Category':<15} {'Qty':<8} {'Price'}")
    print("-" * 68)
    for sku, name, cat, qty, price in items:
        print(f"{sku:<10} {name:<22} {cat:<15} {qty:<8} ${price:.2f}")
    print("=" * 68 + "\n")


def update_stock(sku, quantity_change):
    """
    Update Operation (CRUD):
    Increments or decrements stock levels for a specific SKU.
    Accepts positive integers for restocks and negative integers for sales.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Relative Update:
    # Modifies existing quantity in-place (quantity + ?) to avoid race conditions
    # where multiple processes overwrite each other's stale state.
    cursor.execute("""
        UPDATE products 
        SET quantity = quantity + ? 
        WHERE sku = ?
    """, (quantity_change, sku))

    conn.commit()

    # Validation:
    # 'cursor.rowcount' checks how many rows were actually touched by the SQL query.
    # If 0, the specified SKU does not exist in the database.
    if cursor.rowcount == 0:
        print(f"[NOT FOUND] Cannot update stock: SKU '{sku}' does not exist.")
    else:
        print(f"[UPDATED] Modified stock level for SKU '{sku}' by {quantity_change:+d}.")

    conn.close()


if __name__ == "__main__":
    # 1. Guarantee DB tables exist
    init_db()

    # 2. Seed mock records for demo/testing
    print("--- Seeding Initial Products ---")
    add_product("SKU-001", "Daily Multivitamin", "Health", 50, 11.99)
    add_product("SKU-002", "Protein Powder", "Nutrition", 25, 29.99)
    add_product("SKU-003", "Almond Milk", "Grocery", 40, 3.49)

    # Attempt a duplicate insert to demonstrate defensive error handling
    add_product("SKU-001", "Daily Multivitamin Dup", "Health", 10, 11.99)

    # 3. Process a transaction update (-5 units sold)
    update_stock("SKU-002", -5)

    # 4. Render the finalized inventory table
    list_products()
