import sqlite3

conn = sqlite3.connect('backend/dukaanai.db')
c = conn.cursor()

# 1. Delete Tx 35 (the dummy 500 payment on Anand from seed testing)
c.execute("DELETE FROM transactions WHERE id = 35")
print("Deleted dummy Tx 35 on Anand.")

# 2. Delete phantom test customers and their test transactions
c.execute("DELETE FROM transactions WHERE customer_id IN (36, 37, 38, 39, 40, 41)")
c.execute("DELETE FROM customers WHERE id IN (36, 37, 38, 39, 40, 41)")
print("Cleaned phantom test customers 36..41.")

conn.commit()

# 3. Check Anand's transactions and balance
c.execute("SELECT id, type, amount, status, created_at FROM transactions WHERE customer_id = 14 ORDER BY created_at")
txs = c.fetchall()
print("\nAnand transactions:")
running = 0.0
tot_cr = 0.0
tot_pm = 0.0
for t in txs:
    t_id, t_type, t_amt, t_stat, t_dt = t
    t_amt = float(t_amt)
    if t_type == 'CREDIT':
        tot_cr += t_amt
        running += t_amt
    else:
        tot_pm += t_amt
        running = max(0.0, running - t_amt)
    print(f"Tx {t_id}: {t_type} ₹{t_amt} -> Running Balance: ₹{running}")

c.execute("UPDATE customers SET outstanding_balance = ? WHERE id = 14", (running,))
conn.commit()

print(f"\nAnand Summary -> Total Credited: ₹{tot_cr}, Total Paid: ₹{tot_pm}, Outstanding: ₹{running}")
conn.close()
