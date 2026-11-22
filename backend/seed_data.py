import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import logging
from sqlalchemy import select
from app.core.database import engine, Base, AsyncSessionLocal
from app.models.shop import Shop
from app.models.customer import Customer
from app.models.transaction import Transaction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed():
    # Ensure tables are created
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Check if shop already exists
        result = await db.execute(select(Shop).where(Shop.id == 1))
        existing_shop = result.scalar_one_or_none()
        if existing_shop:
            logger.info("Database already seeded with shop '%s'. Skipping seed.", existing_shop.name)
            return

        logger.info("Starting DukaanAI database seeding...")

        # 1. Create Shop
        shop = Shop(
            id=1,
            name="Shri Lakshmi Kirana Store",
            owner_name="santhoshini",
            username="santhoshini",
            language_preference="kn",
            demo_mode=True,
        )
        db.add(shop)
        await db.flush()

        # 2. Create 12 Customers
        customers_data = [
            {
                "id": 1,
                "name": "Ramesh Kumar",
                "alias": None,
                "phone": "+91 98450 11223",
                "landmark": "near bus stop",
                "notes": "Regular morning customer, takes groceries on weekly credit",
                "outstanding_balance": Decimal("2250.00"),
            },
            {
                "id": 2,
                "name": "Ramesh Sharma",
                "alias": None,
                "phone": "+91 98450 44556",
                "landmark": "MG Road",
                "notes": "Shopkeeper neighbor, buys bulk wheat and oil",
                "outstanding_balance": Decimal("1450.00"),
            },
            {
                "id": 3,
                "name": "Suresh Patel",
                "alias": "dairy Suresh",
                "phone": "+91 98451 22334",
                "landmark": "next to Nandini milk booth",
                "notes": "Runs local dairy distribution, clears balance bi-weekly",
                "outstanding_balance": Decimal("1200.00"),
            },
            {
                "id": 4,
                "name": "Mahesh Hegde",
                "alias": None,
                "phone": "+91 98452 33445",
                "landmark": "opp. State Bank",
                "notes": "Teacher at local school, prompt monthly payer",
                "outstanding_balance": Decimal("1620.00"),
            },
            {
                "id": 5,
                "name": "Priya Devi",
                "alias": None,
                "phone": "+91 98453 44556",
                "landmark": "behind temple",
                "notes": "Buys provisions on credit, pays via UPI every Saturday",
                "outstanding_balance": Decimal("1220.00"),
            },
            {
                "id": 6,
                "name": "Ravi Kumar",
                "alias": "corner shop Ravi",
                "phone": "+91 98454 55667",
                "landmark": "crossroads corner",
                "notes": "Operates tea stall, daily snacks and sugar supplier",
                "outstanding_balance": Decimal("1570.00"),
            },
            {
                "id": 7,
                "name": "Anitha Gowda",
                "alias": None,
                "phone": "+91 98455 66778",
                "landmark": "near municipal park",
                "notes": "Homemaker, monthly grocery credit account",
                "outstanding_balance": Decimal("1000.00"),
            },
            {
                "id": 8,
                "name": "Venkatesh Rao",
                "alias": None,
                "phone": "+91 98456 77889",
                "landmark": "near post office",
                "notes": "Retired bank officer, pays on pension day",
                "outstanding_balance": Decimal("1580.00"),
            },
            {
                "id": 9,
                "name": "Kavitha Reddy",
                "alias": None,
                "phone": "+91 98457 88990",
                "landmark": "2nd cross residential",
                "notes": "Family account, buys spices and rice",
                "outstanding_balance": Decimal("1120.00"),
            },
            {
                "id": 10,
                "name": "Sathish Kumar",
                "alias": None,
                "phone": "+91 98458 99001",
                "landmark": "near auto stand",
                "notes": "Auto drivers association president",
                "outstanding_balance": Decimal("830.00"),
            },
            {
                "id": 11,
                "name": "Deepa Nair",
                "alias": None,
                "phone": "+91 98459 00112",
                "landmark": "near hospital road",
                "notes": "Staff nurse, purchases dairy and baby care products",
                "outstanding_balance": Decimal("498.00"),
            },
            {
                "id": 12,
                "name": "Manjunath B",
                "alias": None,
                "phone": "+91 98460 11223",
                "landmark": "near railway gate",
                "notes": "Tailoring shop owner, weekly settle",
                "outstanding_balance": Decimal("690.00"),
            },
        ]

        cust_objs = {}
        for c in customers_data:
            cust = Customer(
                id=c["id"],
                shop_id=shop.id,
                name=c["name"],
                alias=c["alias"],
                phone=c["phone"],
                landmark=c["landmark"],
                notes=c["notes"],
                outstanding_balance=c["outstanding_balance"],
                is_active=True,
            )
            db.add(cust)
            cust_objs[c["id"]] = cust

        await db.flush()

        # 3. Create Transactions over past 7 days
        now = datetime.now(timezone.utc)
        today_morning = datetime(now.year, now.month, now.day, 8, 30, tzinfo=timezone.utc)

        # Historical transactions (Day -6 to Day -1)
        # Net sum of historical = ₹13,368.
        # Combined with today's 5 credits of ₹1,660 = ₹15,028 outstanding.
        historical_transactions = [
            # Day -6
            {"cust_id": 3, "type": "CREDIT", "amount": 1500.0, "days_ago": 6, "desc": "1500 rupees udhar ghee and sweets", "voice": "suresh patel ge 1500 ghee udhar"},
            {"cust_id": 6, "type": "CREDIT", "amount": 1810.0, "days_ago": 6, "desc": "tea leaves and bakery stock 1810", "voice": "ravi corner shop 1810 tea stock credit"},
            {"cust_id": 8, "type": "CREDIT", "amount": 2080.0, "days_ago": 6, "desc": "monthly provisions bag 2080", "voice": "venkatesh rao monthly groceries 2080 credit"},

            # Day -5
            {"cust_id": 2, "type": "CREDIT", "amount": 1950.0, "days_ago": 5, "desc": "wheat flour sack and oil 1950", "voice": "ramesh sharma mg road 1950 udhar"},
            {"cust_id": 4, "type": "CREDIT", "amount": 2000.0, "days_ago": 5, "desc": "rice bag and spices 2000", "voice": "mahesh hegde 2000 rice udhar"},
            {"cust_id": 7, "type": "CREDIT", "amount": 1250.0, "days_ago": 5, "desc": "dal, pulses and cooking oil 1250", "voice": "anitha gowda 1250 credit"},
            {"cust_id": 10, "type": "CREDIT", "amount": 1330.0, "days_ago": 5, "desc": "dry rations and soap 1330", "voice": "sathish kumar 1330 udhar"},
            {"cust_id": 12, "type": "CREDIT", "amount": 1190.0, "days_ago": 5, "desc": "household groceries 1190", "voice": "manjunath b 1190 credit"},

            # Day -4
            {"cust_id": 1, "type": "CREDIT", "amount": 2500.0, "days_ago": 4, "desc": "25kg sona masoori rice 2500", "voice": "ramesh kumar bus stop 2500 udhar"},
            {"cust_id": 5, "type": "CREDIT", "amount": 1440.0, "days_ago": 4, "desc": "sunflower oil and masalas 1440", "voice": "priya devi 1440 credit"},
            {"cust_id": 9, "type": "CREDIT", "amount": 1620.0, "days_ago": 4, "desc": "spices and pulses 1620", "voice": "kavitha reddy 1620 udhar"},

            # Day -3
            {"cust_id": 2, "type": "PAYMENT", "amount": 500.0, "days_ago": 3, "desc": "cash payment received 500", "voice": "ramesh sharma 500 cash payment received"},
            {"cust_id": 3, "type": "PAYMENT", "amount": 620.0, "days_ago": 3, "desc": "UPI payment received 620", "voice": "dairy suresh 620 upi jama"},
            {"cust_id": 7, "type": "PAYMENT", "amount": 500.0, "days_ago": 3, "desc": "cash payment 500", "voice": "anitha gowda 500 waapas diye"},
            {"cust_id": 11, "type": "CREDIT", "amount": 998.0, "days_ago": 3, "desc": "baby powder and hygiene items 998", "voice": "deepa nair 998 credit"},

            # Day -2
            {"cust_id": 1, "type": "PAYMENT", "amount": 700.0, "days_ago": 2, "desc": "partial cash payment 700", "voice": "ramesh kumar 700 cash diye"},
            {"cust_id": 4, "type": "PAYMENT", "amount": 380.0, "days_ago": 2, "desc": "cash payment 380", "voice": "mahesh hegde 380 payment aagide"},
            {"cust_id": 6, "type": "PAYMENT", "amount": 600.0, "days_ago": 2, "desc": "UPI payment 600", "voice": "corner shop ravi 600 upi payment"},
            {"cust_id": 9, "type": "PAYMENT", "amount": 500.0, "days_ago": 2, "desc": "cash settlement 500", "voice": "kavitha reddy 500 jama"},
            {"cust_id": 10, "type": "PAYMENT", "amount": 500.0, "days_ago": 2, "desc": "cash 500", "voice": "sathish kumar 500 diye"},
            {"cust_id": 12, "type": "PAYMENT", "amount": 500.0, "days_ago": 2, "desc": "cash 500", "voice": "manjunath 500 payment"},

            # Day -1 (yesterday)
            {"cust_id": 5, "type": "PAYMENT", "amount": 500.0, "days_ago": 1, "desc": "UPI payment 500", "voice": "priya devi 500 upi paid"},
            {"cust_id": 8, "type": "PAYMENT", "amount": 500.0, "days_ago": 1, "desc": "cash payment 500", "voice": "venkatesh rao 500 cash payment"},
            {"cust_id": 11, "type": "PAYMENT", "amount": 500.0, "days_ago": 1, "desc": "cash payment 500", "voice": "deepa nair 500 payment"},
        ]

        for h in historical_transactions:
            tx_time = today_morning - timedelta(days=h["days_ago"], hours=h["days_ago"] % 3)
            tx = Transaction(
                shop_id=shop.id,
                customer_id=h["cust_id"],
                type=h["type"],
                amount=Decimal(str(h["amount"])),
                description=h["desc"],
                voice_transcript=h["voice"],
                status="CONFIRMED",
                created_at=tx_time,
                confirmed_at=tx_time,
            )
            db.add(tx)

        # 4. Today's Transactions (Exactly 5 CONFIRMED CREDIT transactions totalling ₹1,660, 0 payments)
        todays_transactions = [
            {
                "cust_id": 1,
                "amount": 450.0,
                "desc": "rice and sugar 450 credit",
                "voice": "Ramesh Kumar bus stop ge 450 rupayi udhar",
                "minutes_ago": 180,
            },
            {
                "cust_id": 3,
                "amount": 320.0,
                "desc": "milk packets and curd 320 credit",
                "voice": "Dairy Suresh 320 milk udhar khathe",
                "minutes_ago": 140,
            },
            {
                "cust_id": 5,
                "amount": 280.0,
                "desc": "cooking oil 280 credit",
                "voice": "Priya Devi 280 oil credit needi",
                "minutes_ago": 90,
            },
            {
                "cust_id": 6,
                "amount": 360.0,
                "desc": "pulses and biscuits 360 credit",
                "voice": "Ravi Kumar corner shop 360 udhar le gaya",
                "minutes_ago": 45,
            },
            {
                "cust_id": 7,
                "amount": 250.0,
                "desc": "wheat flour 250 credit",
                "voice": "Anitha Gowda 250 wheat flour credit",
                "minutes_ago": 15,
            },
        ]

        for t in todays_transactions:
            tx_time = now - timedelta(minutes=t["minutes_ago"])
            tx = Transaction(
                shop_id=shop.id,
                customer_id=t["cust_id"],
                type="CREDIT",
                amount=Decimal(str(t["amount"])),
                description=t["desc"],
                voice_transcript=t["voice"],
                status="CONFIRMED",
                created_at=tx_time,
                confirmed_at=tx_time,
            )
            db.add(tx)

        await db.commit()
        logger.info("Database seeding completed successfully!")
        logger.info("- 1 Shop created: %s", shop.name)
        logger.info("- 12 Customers created (total outstanding: ₹15,028)")
        logger.info("- 5 Transactions created today (credit: ₹1,660, payment: ₹0)")


async def main():
    await seed()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
