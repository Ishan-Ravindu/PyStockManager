#!/usr/bin/env python
import os
import sys
import random
from decimal import Decimal
from datetime import datetime, timedelta

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure Django settings BEFORE any app imports
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mssports.settings')

# Initialize Django
import django
django.setup()

# Import after Django is fully set up
from django.utils import timezone
from faker import Faker

# Now it's safe to import models
from entity.models import Shop, Supplier, Customer, Product
from accounts.models import Account, Withdraw, AccountTransfer
from inventory.models.stock import Stock
from inventory.models.purchases import PurchaseInvoice, PurchaseInvoiceItem
from inventory.models.stock_transfers import StockTransfer, StockTransferItem
from inventory.models.sales import Receipt, SalesInvoice, SalesInvoiceItem

fake = Faker()

def create_shops(count=5):
    """Create shops including at least one warehouse."""
    print(f"Creating {count} shops...")
    
    # Create one warehouse for sure
    warehouse = Shop.objects.create(
        name="Main Warehouse",
        code="WH01",
        location=fake.address(),
        is_warehouse=True
    )
    
    # Create regular shops
    shops = [
        Shop.objects.create(
            name=f"{fake.company()} Store",
            code=f"ST{i:02d}",
            location=fake.address(),
            is_warehouse=False
        )
        for i in range(1, count)
    ]
    
    shops.insert(0, warehouse)  # Add warehouse to the list
    return shops

def create_suppliers(count=10):
    """Create suppliers."""
    print(f"Creating {count} suppliers...")
    suppliers = []
    
    for i in range(count):
        suppliers.append(Supplier.objects.create(
            name=fake.company(),
            mobile_number=f"0{fake.random_number(digits=9)}",
            address=fake.address(),
            email=fake.company_email()
        ))
    
    return suppliers

def create_customers(count=30):
    """Create customers with various credit conditions."""
    print(f"Creating {count} customers...")
    customers = []
    
    for i in range(count):
        credit_limit = random.choice([0, 0, 0, 1000, 2000, 5000, 10000])
        credit_period = random.choice([0, 0, 0, 7, 14, 30, 45, 60])
        credit = Decimal('0.00')
        
        # Some customers with existing credit
        if credit_limit > 0 and random.random() < 0.6:
            credit = Decimal(str(round(random.uniform(0, credit_limit * 1.2), 2)))
        
        customers.append(Customer.objects.create(
            name=fake.name(),
            mobile_number=f"0{fake.random_number(digits=9)}",
            address=fake.address(),
            email=fake.email(),
            credit=credit,
            credit_limit=Decimal(str(credit_limit)),
            credit_period=credit_period,
            black_list=random.random() < 0.05  # 5% blacklisted
        ))
    
    return customers

def create_products(count=20):
    """Create products."""
    print(f"Creating {count} products...")
    products = []
    
    for i in range(count):
        products.append(Product.objects.create(
            name=f"{fake.word().capitalize()} {fake.word().capitalize()}",
            description=fake.paragraph(),
            profit_margin=Decimal(str(round(random.uniform(5, 30), 2)))
        ))
    
    return products

def create_accounts(count=5):
    """Create accounts."""
    print(f"Creating {count} accounts...")
    accounts = []
    
    # Create standard accounts
    account_names = ["Cash", "Bank", "Credit Card", "PayPal", "Other"]
    for i in range(min(count, len(account_names))):
        accounts.append(Account.objects.create(
            name=account_names[i],
            balance=Decimal(str(round(random.uniform(10000, 50000), 2)))
        ))
    
    # Add more accounts if needed
    for i in range(len(account_names), count):
        accounts.append(Account.objects.create(
            name=f"Account {i+1}",
            balance=Decimal(str(round(random.uniform(1000, 10000), 2)))
        ))
    
    return accounts

def create_account_transactions(accounts, count=20):
    """Create withdrawals and transfers between accounts."""
    print(f"Creating {count} account transactions...")
    
    # Create withdrawals
    for _ in range(count // 2):
        account = random.choice(accounts)
        amount = Decimal(str(round(random.uniform(50, 500), 2)))
        
        # Only create if there's sufficient balance
        if account.balance >= amount:
            Withdraw.objects.create(
                account=account,
                amount=amount
            )
    
    # Create transfers
    for _ in range(count // 2):
        from_account = random.choice(accounts)
        to_account = random.choice([a for a in accounts if a != from_account])
        amount = Decimal(str(round(random.uniform(100, 1000), 2)))
        
        # Only create if there's sufficient balance
        if from_account.balance >= amount:
            AccountTransfer.objects.create(
                from_account=from_account,
                to_account=to_account,
                amount=amount
            )

def create_purchase_invoices(shops, suppliers, products, count=15):
    """Create purchase invoices and items."""
    print(f"Creating {count} purchase invoices...")
    purchase_invoices = []
    
    # Find warehouses
    warehouses = [shop for shop in shops if shop.is_warehouse]
    
    for _ in range(count):
        invoice = PurchaseInvoice.objects.create(
            supplier=random.choice(suppliers),
            shop=random.choice(warehouses if warehouses else shops)
        )
        
        # Add 1-5 items to each invoice
        num_items = random.randint(1, 5)
        selected_products = random.sample(products, num_items)
        
        for product in selected_products:
            quantity = random.randint(10, 100)
            price = Decimal(str(round(random.uniform(10, 200), 2)))
            
            PurchaseInvoiceItem.objects.create(
                purchase_invoice=invoice,
                product=product,
                quantity=quantity,
                price=price
            )
            
            # Update stock in the warehouse
            stock, created = Stock.objects.get_or_create(
                shop=invoice.shop,
                product=product,
                defaults={'quantity': 0}
            )
            stock.update_stock(quantity)
        
        # Update total amount
        invoice.update_total_amount()
        purchase_invoices.append(invoice)
    
    return purchase_invoices

def create_stock_transfers(shops, products, count=10):
    """Create stock transfers between shops."""
    print(f"Creating {count} stock transfers...")
    
    warehouses = [shop for shop in shops if shop.is_warehouse]
    retail_shops = [shop for shop in shops if not shop.is_warehouse]
    
    if not warehouses or not retail_shops:
        print("Need at least one warehouse and one retail shop for transfers")
        return []
    
    transfers = []
    
    for _ in range(count):
        # Typically transfers are from warehouse to retail
        if random.random() < 0.8:  # 80% from warehouse to retail
            from_shop = random.choice(warehouses)
            to_shop = random.choice(retail_shops)
        else:  # 20% between retail shops or returns to warehouse
            shops_copy = shops.copy()
            from_shop = random.choice(shops_copy)
            shops_copy.remove(from_shop)
            to_shop = random.choice(shops_copy)
        
        transfer = StockTransfer.objects.create(
            from_shop=from_shop,
            to_shop=to_shop,
            description=random.choice([
                "Regular stock transfer",
                "Emergency restock",
                "New product distribution",
                "Return to warehouse",
                "Balancing inventory"
            ])
        )
        
        # Get products that have stock in from_shop
        available_products = []
        for product in products:
            stock = Stock.objects.filter(shop=from_shop, product=product, quantity__gt=0).first()
            if stock:
                available_products.append((product, stock.quantity))
        
        if not available_products:
            continue
        
        # Add 1-3 items to transfer
        num_items = min(len(available_products), random.randint(1, 3))
        selected_products = random.sample(available_products, num_items)
        
        for product_tuple in selected_products:
            product, max_quantity = product_tuple
            quantity = random.randint(1, min(max_quantity, 20))
            
            StockTransferItem.objects.create(
                stock_transfer=transfer,
                product=product,
                quantity=quantity
            )
            
            # Update stock in both shops
            from_stock = Stock.objects.get(shop=from_shop, product=product)
            from_stock.update_stock(-quantity)
            
            to_stock, created = Stock.objects.get_or_create(
                shop=to_shop,
                product=product,
                defaults={'quantity': 0}
            )
            to_stock.update_stock(quantity)
        
        transfers.append(transfer)
    
    return transfers

def create_sales_invoices(shops, customers, products, accounts, count=30):
    """Create sales invoices, items, and receipts."""
    print(f"Creating {count} sales invoices...")
    
    sales_invoices = []
    now = timezone.now()
    
    # Filter out blacklisted customers
    valid_customers = [c for c in customers if not c.black_list]
    
    for i in range(count):
        # Randomly decide invoice date (between 90 days ago and today)
        days_ago = random.randint(0, 90)
        invoice_date = now - timedelta(days=days_ago)
        
        # Select a customer
        customer = random.choice(valid_customers)
        shop = random.choice(shops)
        
        # Determine due date based on customer's credit period
        # Always convert to date object for consistency
        due_date = (invoice_date + timedelta(days=customer.credit_period)).date() if customer.credit_period > 0 else invoice_date.date()
        
        # Create the invoice
        invoice = SalesInvoice.objects.create(
            customer=customer,
            shop=shop,
            due_date=due_date,  # due_date is now always a date object
            created_at=invoice_date
        )
        
        # Find products with stock in this shop
        available_products = []
        for product in products:
            stock = Stock.objects.filter(shop=shop, product=product, quantity__gt=0).first()
            if stock:
                available_products.append((product, stock.quantity))
        
        if not available_products:
            continue
        
        # Add 1-5 items to invoice
        num_items = min(len(available_products), random.randint(1, 5))
        selected_products = random.sample(available_products, num_items)
        
        for product_tuple in selected_products:
            product, max_quantity = product_tuple
            quantity = random.randint(1, min(max_quantity, 5))
            
            # Get a sensible price based on product's average cost and margin
            avg_cost = product.get_average_cost()
            if avg_cost > 0:
                # Convert profit_margin to Decimal if it isn't already
                margin_factor = Decimal('1') + (product.profit_margin / Decimal('100'))
                # Ensure price doesn't exceed field limits
                price = min(avg_cost * margin_factor, Decimal('9999999.99'))
            else:
                price = Decimal(str(round(random.uniform(50, 250), 2)))
            
            SalesInvoiceItem.objects.create(
                sales_invoice=invoice,
                product=product,
                quantity=quantity,
                price=price
            )
            
            # Update stock
            stock = Stock.objects.get(shop=shop, product=product)
            stock.update_stock(-quantity)
        
        # Update total amount
        invoice.update_total_amount()
        
        # Create receipts (payments) for this invoice
        # 70% chance of some payment, 50% chance of full payment
        if random.random() < 0.7:
            payment_status = random.random()
            
            # Debug the total_amount to see if it's reasonable
            print(f"Invoice {invoice.id} total amount: {invoice.total_amount}")
            
            if payment_status < 0.5:  # Full payment
                # Be extra careful with the payment amount - keep it small for testing
                payment_amount = min(invoice.total_amount, Decimal('999.99'))
                print(f"Full payment: {payment_amount}")
            else:  # Partial payment
                # Use a very small percentage for testing
                percentage = Decimal('0.1')  # Just 10%
                payment_amount = min(invoice.total_amount * percentage, Decimal('999.99'))
                print(f"Partial payment: {payment_amount}")
                
            try:
                Receipt.objects.create(
                    sales_invoice=invoice,
                    amount=payment_amount,
                    account=random.choice(accounts)
                )
                print("Receipt created successfully")
            except Exception as e:
                print(f"Error creating receipt: {e}")
            
            # If invoice has due date in the past, 30% chance of additional payment
            if due_date < now.date() and random.random() < 0.3 and invoice.get_due_amount() > 0:
                # Use small known values that will work for testing
                additional_amount = min(
                    Decimal('50.00'),
                    invoice.get_due_amount(),
                    Decimal('999.99')
                )
                
                if additional_amount > 0:
                    try:
                        Receipt.objects.create(
                            sales_invoice=invoice,
                            amount=additional_amount,
                            account=random.choice(accounts)
                        )
                        print(f"Additional receipt created: {additional_amount}")
                    except Exception as e:
                        print(f"Error creating additional receipt: {e}")
        
        sales_invoices.append(invoice)
    
    return sales_invoices

def run_seed():
    """Run the complete seed process."""
    # Clear existing data (uncomment if needed)
    # SalesInvoiceItem.objects.all().delete()
    # SalesInvoice.objects.all().delete()
    # Receipt.objects.all().delete()
    # StockTransferItem.objects.all().delete()
    # StockTransfer.objects.all().delete()
    # PurchaseInvoiceItem.objects.all().delete()
    # PurchaseInvoice.objects.all().delete()
    # Stock.objects.all().delete()
    # Withdraw.objects.all().delete()
    # AccountTransfer.objects.all().delete()
    # Account.objects.all().delete()
    # Product.objects.all().delete()
    # Customer.objects.all().delete()
    # Supplier.objects.all().delete()
    # Shop.objects.all().delete()
    
    # Create base entities
    shops = create_shops(count=5)
    suppliers = create_suppliers(count=8)
    customers = create_customers(count=20)
    products = create_products(count=15)
    accounts = create_accounts(count=4)
    
    # Create transactions and activities
    create_account_transactions(accounts, count=30)
    purchase_invoices = create_purchase_invoices(shops, suppliers, products, count=20)
    stock_transfers = create_stock_transfers(shops, products, count=15)
    sales_invoices = create_sales_invoices(shops, customers, products, accounts, count=40)
    
    print("Seed completed successfully!")

if __name__ == "__main__":
    run_seed()