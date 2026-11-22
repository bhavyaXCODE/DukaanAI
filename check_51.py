import sqlite3

conn = sqlite3.connect('backend/dukaanai.db')
c = conn.cursor()

print("ALL transactions where amount = 51 or customer_id in (14, 41):")
for r in c.execute("SELECT t.id, t.customer_id, c.name, t.type, t.amount, t.status, t.created_at FROM transactions t LEFT JOIN customers c ON t.customer_id = c.id WHERE t.amount = 51 OR t.customer_id IN (14, 41) ORDER BY t.id DESC").fetchall():
    print(r)
