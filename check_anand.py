import sqlite3

conn = sqlite3.connect('backend/dukaanai.db')
c = conn.cursor()

print("CUSTOMERS matching anand:")
for row in c.execute("SELECT id, name, outstanding_balance, is_active FROM customers WHERE name LIKE '%आनंद%' OR name LIKE '%anand%'").fetchall():
    print(row)

print("\nALL TRANSACTIONS for anand:")
for row in c.execute("SELECT t.id, t.customer_id, c.name, t.type, t.amount, t.status, t.created_at FROM transactions t LEFT JOIN customers c ON t.customer_id = c.id WHERE c.name LIKE '%आनंद%' OR c.name LIKE '%anand%' ORDER BY t.id").fetchall():
    print(row)
