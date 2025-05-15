from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
import datetime

from inventory.models.stock import Stock
from sale_invoice.admin.forms import SalesInvoiceForm, SalesInvoiceItemForm
from sale_invoice.models import SalesInvoice, SalesInvoiceItem
from shop.models import Shop
from customer.models import Customer
from product.models import Product, Category


class SalesInvoiceItemTestCase(TestCase):
    """Test the sales invoice item creation, updates, and deletions."""
    
    def setUp(self):
        """Set up test data for sales invoice tests."""
        # Create a shop
        self.shop = Shop.objects.create(
            name="Test Shop",
            code="TS01",
            location="123 Test St",
            is_warehouse=False
        )
        
        # Create a customer
        self.customer = Customer.objects.create(
            name="Test Customer",
            mobile_number="9876543210",
            address="456 Customer St",
            email="customer@test.com",
            credit=Decimal('0.00'),
            credit_limit=Decimal('1000.00'),
            credit_period=30,
            whole_sale=False,
            black_list=False
        )
        
        # Create category
        self.category = Category.objects.create(
            name="Test Category",
            description="Test Category Description",
            profit_margin=Decimal('15.00')
        )
        
        # Create products
        self.product1 = Product.objects.create(
            name="Product 1",
            description="Test Product 1",
            profit_margin=Decimal('10.00'),
            category=self.category
        )
        
        self.product2 = Product.objects.create(
            name="Product 2",
            description="Test Product 2",
            profit_margin=Decimal('20.00'),
            category=self.category
        )
        
        # Create stock for these products
        self.stock1 = Stock.objects.create(
            shop=self.shop,
            product=self.product1,
            quantity=100,
            average_cost=Decimal('10.00'),
        )
        
        self.stock2 = Stock.objects.create(
            shop=self.shop,
            product=self.product2,
            quantity=50,
            average_cost=Decimal('20.00'),
            selling_price=Decimal('30.00')
        )
        
        # Create a sales invoice
        today = timezone.now().date()
        self.invoice = SalesInvoice.objects.create(
            shop=self.shop,
            customer=self.customer,
            total_amount=Decimal('0.00'),
            paid_amount=Decimal('0.00'),
            due_date=today + datetime.timedelta(days=30)
        )

    def test_create_sales_invoice_item(self):
        """Test creating a new sales invoice item."""
        # Initial check of stock and customer credit
        initial_stock = Stock.objects.get(shop=self.shop, product=self.product1).quantity
        initial_credit = Customer.objects.get(pk=self.customer.pk).credit
        
        # Create a sales invoice item
        item = SalesInvoiceItem.objects.create(
            sales_invoice=self.invoice,
            product=self.product1,
            quantity=10,
            price=Decimal('15.00'),
            average_cost=Decimal('10.00'),
            discount_method='amount',
            discount_amount=Decimal('0.00')
        )
        
        # Check that stock was reduced
        updated_stock = Stock.objects.get(shop=self.shop, product=self.product1).quantity
        self.assertEqual(updated_stock, initial_stock - 10)
        
        # Check that invoice total was updated
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.total_amount, Decimal('150.00'))
        
        # Check that customer credit was updated
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.credit, initial_credit + Decimal('150.00'))
        
        # Check profit calculation
        self.assertEqual(self.invoice.get_total_average_cost(), Decimal('100.00'))
        self.assertEqual(self.invoice.get_profit(), Decimal('50.00'))

    def test_create_sales_invoice_item_with_discount_amount(self):
        """Test creating a sales invoice item with amount discount."""
        # Create a sales invoice item with discount amount
        item = SalesInvoiceItem.objects.create(
            sales_invoice=self.invoice,
            product=self.product1,
            quantity=10,
            price=Decimal('15.00'),
            average_cost=Decimal('10.00'),
            discount_method='amount',
            discount_amount=Decimal('2.00')  # $2 discount per unit
        )
        
        # Check that invoice total reflects the discount
        self.invoice.refresh_from_db()
        # 10 * (15 - 2) = 10 * 13 = 130
        self.assertEqual(self.invoice.total_amount, Decimal('130.00'))
        
        # Check profit calculation with discount
        self.assertEqual(self.invoice.get_total_average_cost(), Decimal('100.00'))
        self.assertEqual(self.invoice.get_profit(), Decimal('30.00'))
    
    def test_create_sales_invoice_item_with_discount_percentage(self):
        """Test creating a sales invoice item with percentage discount."""
        # Create a sales invoice item with percentage discount
        item = SalesInvoiceItem.objects.create(
            sales_invoice=self.invoice,
            product=self.product1,
            quantity=10,
            price=Decimal('15.00'),
            average_cost=Decimal('10.00'),
            discount_method='percentage',
            discount_amount=Decimal('20.00')  # 20% discount per unit
        )
        
        # Check that invoice total reflects the discount
        self.invoice.refresh_from_db()
        # 10 * (15 - (15 * 0.2)) = 10 * (15 - 3) = 10 * 12 = 120
        self.assertEqual(self.invoice.total_amount, Decimal('120.00'))
        
        # Check profit calculation with discount
        self.assertEqual(self.invoice.get_total_average_cost(), Decimal('100.00'))
        self.assertEqual(self.invoice.get_profit(), Decimal('20.00'))

    def test_update_sales_invoice_item_increase_quantity(self):
        """Test updating a sales invoice item to increase quantity."""
        # Create an initial sales invoice item
        item = SalesInvoiceItem.objects.create(
            sales_invoice=self.invoice,
            product=self.product1,
            quantity=10,
            price=Decimal('15.00'),
            average_cost=Decimal('10.00'),
            discount_method='amount',
            discount_amount=Decimal('0.00')
        )
        
        # Get current stock and credit
        stock_after_creation = Stock.objects.get(shop=self.shop, product=self.product1).quantity
        customer_credit_after_creation = Customer.objects.get(pk=self.customer.pk).credit
        
        # Update the item to increase quantity
        item.quantity = 15  # Increase by 5
        item.save()
        
        # Check that only the additional quantity was deducted from stock
        updated_stock = Stock.objects.get(shop=self.shop, product=self.product1).quantity
        self.assertEqual(updated_stock, stock_after_creation - 5)
        
        # Check that invoice total was updated correctly
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.total_amount, Decimal('225.00'))
        
        # Check that customer credit was updated correctly
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.credit, customer_credit_after_creation + Decimal('75.00'))
        
        # Check profit calculation after update
        self.assertEqual(self.invoice.get_total_average_cost(), Decimal('150.00'))
        self.assertEqual(self.invoice.get_profit(), Decimal('75.00'))

    def test_update_sales_invoice_item_decrease_quantity(self):
        """Test updating a sales invoice item to decrease quantity."""
        # Create an initial sales invoice item
        item = SalesInvoiceItem.objects.create(
            sales_invoice=self.invoice,
            product=self.product1,
            quantity=20,
            price=Decimal('15.00'),
            average_cost=Decimal('10.00'),
            discount_method='amount',
            discount_amount=Decimal('0.00')
        )
        
        # Get current stock and credit
        stock_after_creation = Stock.objects.get(shop=self.shop, product=self.product1).quantity
        customer_credit_after_creation = Customer.objects.get(pk=self.customer.pk).credit
        
        # Update the item to decrease quantity
        item.quantity = 12  # Decrease by 8
        item.save()
        
        # Check that the returned quantity was added back to stock
        updated_stock = Stock.objects.get(shop=self.shop, product=self.product1).quantity
        self.assertEqual(updated_stock, stock_after_creation + 8)
        
        # Check that invoice total was updated correctly
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.total_amount, Decimal('180.00'))
        
        # Check that customer credit was updated correctly
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.credit, customer_credit_after_creation - Decimal('120.00'))
        
        # Check profit calculation after update
        self.assertEqual(self.invoice.get_total_average_cost(), Decimal('120.00'))
        self.assertEqual(self.invoice.get_profit(), Decimal('60.00'))

    def test_update_sales_invoice_item_change_product(self):
        """Test updating a sales invoice item to change the product."""
        # Create an initial sales invoice item
        item = SalesInvoiceItem.objects.create(
            sales_invoice=self.invoice,
            product=self.product1,
            quantity=10,
            price=Decimal('15.00'),
            average_cost=Decimal('10.00'),
            discount_method='amount',
            discount_amount=Decimal('0.00')
        )
        
        # Get current stock levels
        stock1_after_creation = Stock.objects.get(shop=self.shop, product=self.product1).quantity
        stock2_after_creation = Stock.objects.get(shop=self.shop, product=self.product2).quantity
        
        # Update the item to change product
        item.product = self.product2
        item.price = Decimal('30.00')  # New product has different price
        item.average_cost = Decimal('20.00')  # New product has different cost
        item.save()
        
        # Check that the original product's stock was returned
        updated_stock1 = Stock.objects.get(shop=self.shop, product=self.product1).quantity
        self.assertEqual(updated_stock1, stock1_after_creation + 10)
        
        # Check that the new product's stock was reduced
        updated_stock2 = Stock.objects.get(shop=self.shop, product=self.product2).quantity
        self.assertEqual(updated_stock2, stock2_after_creation - 10)
        
        # Check that invoice total was updated correctly
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.total_amount, Decimal('300.00'))
        
        # Check profit calculation after product change
        self.assertEqual(self.invoice.get_total_average_cost(), Decimal('200.00'))
        self.assertEqual(self.invoice.get_profit(), Decimal('100.00'))

    def test_update_sales_invoice_item_change_discount(self):
        """Test updating a sales invoice item to change discount."""
        # Create an initial sales invoice item
        item = SalesInvoiceItem.objects.create(
            sales_invoice=self.invoice,
            product=self.product1,
            quantity=10,
            price=Decimal('15.00'),
            average_cost=Decimal('10.00'),
            discount_method='amount',
            discount_amount=Decimal('0.00')
        )
        
        # Get customer credit after initial item creation
        initial_invoice_total = self.invoice.total_amount
        initial_customer_credit = self.customer.credit
        
        # Update the item to apply a discount
        item.discount_method = 'percentage'
        item.discount_amount = Decimal('10.00')  # 10% discount
        item.save()
        
        # Check that invoice total was updated correctly with discount
        self.invoice.refresh_from_db()
        # 10 * (15 - (15 * 0.1)) = 10 * (15 - 1.5) = 10 * 13.5 = 135
        updated_invoice_total = Decimal('135.00')
        self.assertEqual(self.invoice.total_amount, updated_invoice_total)
        
        # Check that customer credit was adjusted based on invoice total change
        self.customer.refresh_from_db()
        expected_credit_change = updated_invoice_total - initial_invoice_total
        expected_customer_credit = initial_customer_credit + expected_credit_change
        self.assertEqual(self.customer.credit, expected_customer_credit)
        
        # Check that discount affects profit calculation
        self.assertEqual(self.invoice.get_total_average_cost(), Decimal('100.00'))
        self.assertEqual(self.invoice.get_profit(), Decimal('35.00'))

    def test_delete_sales_invoice_item(self):
        """Test deleting a sales invoice item."""
        # Create an initial sales invoice item
        item = SalesInvoiceItem.objects.create(
            sales_invoice=self.invoice,
            product=self.product1,
            quantity=10,
            price=Decimal('15.00'),
            average_cost=Decimal('10.00'),
            discount_method='amount',
            discount_amount=Decimal('0.00')
        )
        
        # Get current stock and credit after item creation
        stock_after_creation = Stock.objects.get(shop=self.shop, product=self.product1).quantity
        customer_credit_after_creation = Customer.objects.get(pk=self.customer.pk).credit
        
        # Delete the item
        item_id = item.id
        item.delete()
        
        # Check that stock was returned
        updated_stock = Stock.objects.get(shop=self.shop, product=self.product1).quantity
        self.assertEqual(updated_stock, stock_after_creation + 10)
        
        # Check that invoice total was updated
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.total_amount, Decimal('0.00'))
        
        # Check that customer credit was updated
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.credit, customer_credit_after_creation - Decimal('150.00'))

    def test_multiple_items_invoice_total(self):
        """Test that invoice total is correct with multiple items."""
        # Create two sales invoice items
        item1 = SalesInvoiceItem.objects.create(
            sales_invoice=self.invoice,
            product=self.product1,
            quantity=5,
            price=Decimal('15.00'),
            average_cost=Decimal('10.00'),
            discount_method='amount',
            discount_amount=Decimal('1.00')
        )
        
        item2 = SalesInvoiceItem.objects.create(
            sales_invoice=self.invoice,
            product=self.product2,
            quantity=3,
            price=Decimal('30.00'),
            average_cost=Decimal('20.00'),
            discount_method='percentage',
            discount_amount=Decimal('5.00')
        )
        
        # Check that invoice total is correct
        self.invoice.refresh_from_db()
        # Item 1: 5 * (15 - 1) = 5 * 14 = 70
        # Item 2: 3 * (30 - (30 * 0.05)) = 3 * (30 - 1.5) = 3 * 28.5 = 85.5
        # Total: 70 + 85.5 = 155.5
        self.assertEqual(self.invoice.total_amount, Decimal('155.50'))
        
        # Check profit calculation with multiple items
        # Item 1 cost: 5 * 10 = 50
        # Item 2 cost: 3 * 20 = 60
        # Total cost: 50 + 60 = 110
        # Profit: 155.5 - 110 = 45.5
        self.assertEqual(self.invoice.get_total_average_cost(), Decimal('110.00'))
        self.assertEqual(self.invoice.get_profit(), Decimal('45.50'))

    def test_insufficient_stock_validation(self):
        """Test validation when there's insufficient stock."""
        # Set up a stock with low quantity
        self.stock1.quantity = 5
        self.stock1.save()
        
        # Try to create a form with quantity higher than available
        form_data = {
            'sales_invoice': self.invoice.id,
            'product': self.product1.id,
            'quantity': 10,
            'price': Decimal('15.00'),
            'average_cost': Decimal('10.00'),
            'discount_method': 'amount',
            'discount_amount': Decimal('0.00')
        }
        
        form = SalesInvoiceItemForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('quantity', form.errors)

    def test_edit_validation_increase_quantity(self):
        """Test validation when editing to increase quantity."""
        # Set up a stock with limited quantity
        self.stock1.quantity = 15
        self.stock1.save()
        
        # Create an initial sales invoice item
        item = SalesInvoiceItem.objects.create(
            sales_invoice=self.invoice,
            product=self.product1,
            quantity=10,
            price=Decimal('15.00'),
            average_cost=Decimal('10.00'),
            discount_method='amount',
            discount_amount=Decimal('0.00')
        )
        
        # Stock should now be 5
        self.stock1.refresh_from_db()
        self.assertEqual(self.stock1.quantity, 5)
        
        # Try to update with more than available stock
        form_data = {
            'sales_invoice': self.invoice.id,
            'product': self.product1.id,
            'quantity': 18,  # Trying to add 8 more, but only 5 available
            'price': Decimal('15.00'),
            'average_cost': Decimal('10.00'),
            'discount_method': 'amount',
            'discount_amount': Decimal('0.00')
        }
        
        form = SalesInvoiceItemForm(data=form_data, instance=item)
        self.assertFalse(form.is_valid())
        self.assertIn('quantity', form.errors)
        
        # Try with a valid increase
        form_data['quantity'] = 15  # Increase by 5, which is available
        form = SalesInvoiceItemForm(data=form_data, instance=item)
        self.assertTrue(form.is_valid())

    def test_edit_validation_decrease_quantity(self):
        """Test validation when editing to decrease quantity."""
        # Create an initial sales invoice item
        item = SalesInvoiceItem.objects.create(
            sales_invoice=self.invoice,
            product=self.product1,
            quantity=10,
            price=Decimal('15.00'),
            average_cost=Decimal('10.00'),
            discount_method='amount',
            discount_amount=Decimal('0.00')
        )
        
        # Try to update with less quantity
        form_data = {
            'sales_invoice': self.invoice.id,
            'product': self.product1.id,
            'quantity': 5,  # Decrease by 5
            'price': Decimal('15.00'),
            'average_cost': Decimal('10.00'),
            'discount_method': 'amount',
            'discount_amount': Decimal('0.00')
        }
        
        form = SalesInvoiceItemForm(data=form_data, instance=item)
        # Should always be valid when decreasing
        self.assertTrue(form.is_valid())

    def test_invoice_payment_status(self):
        """Test the payment status method of the invoice."""
        # Create a sales invoice item
        item = SalesInvoiceItem.objects.create(
            sales_invoice=self.invoice,
            product=self.product1,
            quantity=10,
            price=Decimal('15.00'),
            average_cost=Decimal('10.00'),
            discount_method='amount',
            discount_amount=Decimal('0.00')
        )
        
        # Initially unpaid
        self.assertEqual(self.invoice.get_due_amount(), Decimal('150.00'))
        self.assertTrue('Unpaid' in self.invoice.payment_status())
        
        # Partially paid
        self.invoice.paid_amount = Decimal('75.00')
        self.invoice.save()
        self.assertEqual(self.invoice.get_due_amount(), Decimal('75.00'))
        self.assertTrue('Partially Paid' in self.invoice.payment_status())
        
        # Fully paid
        self.invoice.paid_amount = Decimal('150.00')
        self.invoice.save()
        self.assertEqual(self.invoice.get_due_amount(), Decimal('0.00'))
        self.assertTrue('Paid' in self.invoice.payment_status())
        
        # Overdue
        self.invoice.paid_amount = Decimal('75.00')
        self.invoice.due_date = timezone.now().date() - datetime.timedelta(days=1)
        self.invoice.save()
        self.assertTrue('Overdue' in self.invoice.payment_status())

    def test_customer_credit_status(self):
        """Test the credit status method of the customer."""
        # Create a large sales invoice item that will push customer near credit limit
        item = SalesInvoiceItem.objects.create(
            sales_invoice=self.invoice,
            product=self.product1,
            quantity=50,
            price=Decimal('15.00'),
            average_cost=Decimal('10.00'),
            discount_method='amount',
            discount_amount=Decimal('0.00')
        )
        
        # Check customer credit status
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.credit, Decimal('750.00'))
        self.assertTrue('Near Limit' in self.customer.credit_status())
        
        # Push over limit
        item2 = SalesInvoiceItem.objects.create(
            sales_invoice=self.invoice,
            product=self.product2,
            quantity=10,
            price=Decimal('30.00'),
            average_cost=Decimal('20.00'),
            discount_method='amount',
            discount_amount=Decimal('0.00')
        )
        
        # Check customer credit status again
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.credit, Decimal('1050.00'))
        self.assertTrue('Over Limit' in self.customer.credit_status())
        
    def test_invoice_total_change_affects_customer_credit(self):
        """Test that changes to invoice total properly update customer credit."""
        # Initial state - create a sales invoice item
        initial_customer_credit = self.customer.credit
        
        item = SalesInvoiceItem.objects.create(
            sales_invoice=self.invoice,
            product=self.product1,
            quantity=10,
            price=Decimal('15.00'),
            average_cost=Decimal('10.00'),
            discount_method='amount',
            discount_amount=Decimal('0.00')
        )
        
        # Check initial credit update
        self.customer.refresh_from_db()
        expected_credit_after_creation = initial_customer_credit + Decimal('150.00')
        self.assertEqual(self.customer.credit, expected_credit_after_creation)
        
        # Test 1: Change price
        item.price = Decimal('20.00')  # Increase from 15 to 20
        item.save()
        
        # Check customer credit updated with price change
        self.customer.refresh_from_db()
        self.invoice.refresh_from_db()
        expected_credit_after_price_change = expected_credit_after_creation + Decimal('50.00')  # 10 units × $5 increase
        self.assertEqual(self.customer.credit, expected_credit_after_price_change)
        self.assertEqual(self.invoice.total_amount, Decimal('200.00'))
        
        # Test 2: Apply discount
        item.discount_method = 'percentage'
        item.discount_amount = Decimal('25.00')  # 25% discount
        item.save()
        
        # Check customer credit updated with discount
        self.customer.refresh_from_db()
        self.invoice.refresh_from_db()
        # New total: 10 × (20 - (20 × 0.25)) = 10 × 15 = 150
        # Change: 150 - 200 = -50
        expected_credit_after_discount = expected_credit_after_price_change - Decimal('50.00')
        self.assertEqual(self.customer.credit, expected_credit_after_discount)
        self.assertEqual(self.invoice.total_amount, Decimal('150.00'))
        
        # Test 3: Add another item
        item2 = SalesInvoiceItem.objects.create(
            sales_invoice=self.invoice,
            product=self.product2,
            quantity=5,
            price=Decimal('30.00'),
            average_cost=Decimal('20.00'),
            discount_method='amount',
            discount_amount=Decimal('0.00')
        )
        
        # Check customer credit updated with new item
        self.customer.refresh_from_db()
        self.invoice.refresh_from_db()
        # Additional amount: 5 × 30 = 150
        expected_credit_after_new_item = expected_credit_after_discount + Decimal('150.00')
        self.assertEqual(self.customer.credit, expected_credit_after_new_item)
        self.assertEqual(self.invoice.total_amount, Decimal('300.00'))
        
        # Test 4: Delete an item
        item.delete()
        
        # Check customer credit updated after item deletion
        self.customer.refresh_from_db()
        self.invoice.refresh_from_db()
        # Removed amount: 150
        expected_credit_after_deletion = expected_credit_after_new_item - Decimal('150.00')
        self.assertEqual(self.customer.credit, expected_credit_after_deletion)
        self.assertEqual(self.invoice.total_amount, Decimal('150.00'))
    
    def test_invoice_item_price_not_below_selling_price(self):
        """Test that invoice item price cannot be lower than product's selling price."""

        # Test case 1: Price equal to selling price should be valid
        form_data = {
            'sales_invoice': self.invoice.id,
            'product': self.product1.id,
            'quantity': 5,
            'price': Decimal('15.00'),  # Equal to selling price
            'average_cost': Decimal('10.10'),
            'discount_method': 'amount',
            'discount_amount': Decimal('0.00')
        }
        
        form = SalesInvoiceItemForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Test case 2: Price below selling price should be invalid
        form_data['price'] = Decimal('9.00')  # Below selling price
        form = SalesInvoiceItemForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('price', form.errors)
        
        # Test case 3: Price above selling price should be valid
        form_data['price'] = Decimal('16.00')  # Above selling price
        form = SalesInvoiceItemForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Test case 4: Check editing an existing item
        item = SalesInvoiceItem.objects.create(
            sales_invoice=self.invoice,
            product=self.product1,
            quantity=5,
            price=Decimal('15.00'),
            average_cost=Decimal('10.00'),
            discount_method='amount',
            discount_amount=Decimal('0.00')
        )
        
        # Try to update with price below selling price
        form_data = {
            'sales_invoice': self.invoice.id,
            'product': self.product1.id,
            'quantity': 5,
            'price': Decimal('9.00'),  # Below selling price
            'average_cost': Decimal('10.00'),
            'discount_method': 'amount',
            'discount_amount': Decimal('0.00')
        }
        
        form = SalesInvoiceItemForm(data=form_data, instance=item)
        self.assertFalse(form.is_valid())
        self.assertIn('price', form.errors)
    
    def test_invoice_due_date_not_exceed_credit_period(self):
        """Test that invoice due date cannot exceed today plus the customer's credit period."""
        
        # Set up a customer with specific credit period
        self.customer.credit_period = 15  # 15 days credit period
        self.customer.save()
        
        today = timezone.now().date()
        
        # Test case 1: Due date equal to max (today + credit period) should be valid
        max_due_date = today + datetime.timedelta(days=15)
        form_data = {
            'customer': self.customer.id,
            'shop': self.shop.id,
            'due_date': max_due_date,
        }
        
        form = SalesInvoiceForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Test case 2: Due date before max should be valid
        valid_due_date = today + datetime.timedelta(days=10)  # Less than 15 days
        form_data['due_date'] = valid_due_date
        
        form = SalesInvoiceForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Test case 3: Due date after max should be invalid
        invalid_due_date = today + datetime.timedelta(days=20)  # More than 15 days
        form_data['due_date'] = invalid_due_date
        
        form = SalesInvoiceForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('due_date', form.errors)
        
        # Test case 4: Test with different credit period
        self.customer.credit_period = 30  # Change to 30 days
        self.customer.save()
        
        new_max_due_date = today + datetime.timedelta(days=30)
        form_data['due_date'] = new_max_due_date
        
        form = SalesInvoiceForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Test case 5: Check with zero credit period
        self.customer.credit_period = 0
        self.customer.save()
        
        tomorrow = today + datetime.timedelta(days=1)
        form_data['due_date'] = tomorrow
        
        form = SalesInvoiceForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('due_date', form.errors)
        
        # Should only allow same-day due date with zero credit period
        form_data['due_date'] = today
        form = SalesInvoiceForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_blacklisted_customer_cannot_create_invoice(self):
        """Test that blacklisted customers cannot have invoices created for them."""
        
        today = timezone.now().date()
        
        # Test with non-blacklisted customer
        form_data = {
            'customer': self.customer.id,
            'shop': self.shop.id,
            'due_date': today + datetime.timedelta(days=5),
        }
        
        form = SalesInvoiceForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Blacklist the customer
        self.customer.black_list = True
        self.customer.save()
        
        # Test with blacklisted customer
        form = SalesInvoiceForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)  # Check non-field errors instead of 'customer'
        error_message = str(form.errors['__all__'])
        self.assertIn("blacklisted customer", error_message)
            
        # Create a new non-blacklisted customer
        new_customer = Customer.objects.create(
            name="New Customer",
            mobile_number="1234567890",
            address="789 New St",
            email="new@test.com",
            credit=Decimal('0.00'),
            credit_limit=Decimal('500.00'),
            credit_period=15,
            whole_sale=False,
            black_list=False
        )
        
        # Should be able to create invoice for non-blacklisted customer
        form_data['customer'] = new_customer.id
        form = SalesInvoiceForm(data=form_data)
        self.assertTrue(form.is_valid())