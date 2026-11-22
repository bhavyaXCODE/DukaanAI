import sqlite3
import shutil
import os
from decimal import Decimal

db_path = os.path.join(os.path.dirname(__file__), 'dukaanai.db')
backup_path = db_path + '.backup'

# 1. Create a backup
if os.path.exists(db_path):
    shutil.copy2(db_path, backup_path)
    print(f"Backed up {db_path} to {backup_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 2. Check current state
cursor.execute("SELECT count(*) FROM transactions")
total_tx = cursor.fetchone()[0]
print(f"Total transactions before cleanup: {total_tx}")

# 3. Clean up transactions 1 to 29 (the dummy seed transactions)
cursor.execute("DELETE FROM transactions WHERE id < 30")
print("Deleted dummy seed transactions (id < 30).")

# Clear transaction drafts
cursor.execute("DELETE FROM transaction_drafts")
print("Cleared transaction drafts.")

# 4. Normalize customer names in remaining transactions (id >= 30)
# Map misrecognized customer names to clean target customer names
tx_name_map = {
    'of ravi': 'Ravi Kumar',
    'paanch sau': 'ram',
    'of Rupa': 'Rupa Devi',
    'गोविंद उदार': 'Govind',
    'सुरेश': 'सुरेश कुमार',
}

# Fetch all remaining transactions
cursor.execute("""
    SELECT t.id, t.customer_id, c.name, t.type, t.amount, t.voice_transcript
    FROM transactions t
    LEFT JOIN customers c ON t.customer_id = c.id
    ORDER BY t.id ASC
""")
remaining_txs = cursor.fetchall()

# 5. Determine unique target customers
# Standardize:
# 'सुरेश कुमार'
# 'Govind'
# 'ram'
# 'Ravi Kumar'
# 'Lakshmamma'
# 'आनंद'
# 'लक्ष्मी'
# 'Rupa Devi'
# 'Priya Devi'
# 'रमेश'
# 'ನಾನಿ ಗೋವಿಂದ್'

# Let's find or create each target customer
target_customer_names = [
    'ram',
    'Ravi Kumar',
    'सुरेश कुमार',
    'Govind',
    'Lakshmamma',
    'आनंद',
    'लक्ष्मी',
    'Rupa Devi',
    'Priya Devi',
    'रमेश',
    'ನಾನಿ ಗೋವಿಂದ್',
]

# Get shop_id (default 1)
cursor.execute("SELECT id FROM shops LIMIT 1")
shop_row = cursor.fetchone()
shop_id = shop_row[0] if shop_row else 1

customer_id_map = {}
for name in target_customer_names:
    cursor.execute("SELECT id FROM customers WHERE name = ? AND shop_id = ?", (name, shop_id))
    row = cursor.fetchone()
    if row:
        customer_id_map[name] = row[0]
    else:
        cursor.execute(
            "INSERT INTO customers (shop_id, name, outstanding_balance, is_active) VALUES (?, ?, 0, 1)",
            (shop_id, name)
        )
        customer_id_map[name] = cursor.lastrowid
        print(f"Created new customer: {name} (id={customer_id_map[name]})")

# Map transaction customer IDs to correct target customer
for tx_id, old_cust_id, old_cust_name, tx_type, amount, voice in remaining_txs:
    target_name = tx_name_map.get(old_cust_name, old_cust_name)
    if target_name in customer_id_map:
        new_cust_id = customer_id_map[target_name]
        if new_cust_id != old_cust_id:
            cursor.execute("UPDATE transactions SET customer_id = ? WHERE id = ?", (new_cust_id, tx_id))
            print(f"Updated tx #{tx_id}: customer_id {old_cust_id} ('{old_cust_name}') -> {new_cust_id} ('{target_name}')")

# 6. Delete all customers not in customer_id_map
valid_ids = tuple(customer_id_map.values())
cursor.execute(f"DELETE FROM customers WHERE id NOT IN ({','.join(['?']*len(valid_ids))})", valid_ids)
print("Removed all unused dummy and garbage customer records.")

# 7. Recalculate outstanding_balance for each customer from confirmed transactions
print("\n--- RECALCULATING BALANCES ---")
for name, cid in customer_id_map.items():
    cursor.execute("""
        SELECT 
            COALESCE(SUM(CASE WHEN type = 'CREDIT' THEN amount ELSE 0 END), 0) as total_credit,
            COALESCE(SUM(CASE WHEN type = 'PAYMENT' THEN amount ELSE 0 END), 0) as total_payment
        FROM transactions
        WHERE customer_id = ? AND status = 'CONFIRMED'
    """, (cid,))
    tot_credit, tot_payment = cursor.fetchone()
    # Kirana ledger balance = credit - payment (clamped to 0 if paid in full/advance)
    calc_balance = max(0.0, float(tot_credit) - float(tot_payment))
    cursor.execute("UPDATE customers SET outstanding_balance = ? WHERE id = ?", (calc_balance, cid))
    print(f"Customer: {name:15} (id={cid:2}) | Credits: ₹{tot_credit:7.2f} | Payments: ₹{tot_payment:7.2f} | New Balance: ₹{calc_balance:7.2f}")

conn.commit()

# Verify final counts
cursor.execute("SELECT count(*) FROM customers")
print(f"\nFinal Active Customers count: {cursor.fetchone()[0]}")
cursor.execute("SELECT count(*) FROM transactions")
print(f"Final Transactions count: {cursor.fetchone()[0]}")
cursor.execute("SELECT sum(outstanding_balance) FROM customers")
print(f"Final Total Outstanding Balance across all customers: ₹{cursor.fetchone()[0]:.2f}")

conn.close()
print("\nDatabase cleanup & recalculation completed successfully!")
