from decimal import Decimal
from django.test import TestCase

from shop.models import Shop
from product.models import Product
from supplier.models import Supplier
from purchase_invoice.models import PurchaseInvoice, PurchaseInvoiceItem


class SupplierPayableTestCase(TestCase):
    """
    Test cases for supplier payable functionality related to purchase invoices.
    
    Tests focus on how supplier payable is affected by:
    1. Invoice creation
    2. Supplier changes
    3. Invoice deletion
    4. Invoice total amount changes
    """

    def setUp(self):
        """Set up test data."""
        # Create shops
        self.shop = Shop.objects.create(
            name="Test Shop",
            code="TST"
        )

        # Create suppliers
        self.supplier1 = Supplier.objects.create(
            name="Supplier One",
            mobile_number="1234567890",
            payable=Decimal('0.00')
        )
        
        self.supplier2 = Supplier.objects.create(
            name="Supplier Two",
            mobile_number="0987654321",
            payable=Decimal('0.00')
        )

        # Create product
        self.product = Product.objects.create(
            name="Test Product",
            profit_margin=20
        )

    def test_invoice_creation_updates_supplier_payable(self):
        """Test that creating an invoice updates the supplier's payable amount."""
        # Initial check
        self.assertEqual(self.supplier1.payable, Decimal('0.00'))
        
        # Create invoice
        invoice = PurchaseInvoice.objects.create(
            supplier=self.supplier1,
            shop=self.shop
        )
        
        # Add items to invoice
        PurchaseInvoiceItem.objects.create(
            purchase_invoice=invoice,
            product=self.product,
            quantity=10,
            price=Decimal('100.00')
        )
        
        # Refresh supplier from database
        self.supplier1.refresh_from_db()
        
        # Check supplier payable is increased
        self.assertEqual(self.supplier1.payable, Decimal('1000.00'))  # 10 * 100

    def test_supplier_change_updates_payable(self):
        """Test that changing the supplier of an invoice updates both suppliers' payable amounts."""
        # Create invoice with supplier1
        invoice = PurchaseInvoice.objects.create(
            supplier=self.supplier1,
            shop=self.shop
        )
        
        # Add items to invoice
        PurchaseInvoiceItem.objects.create(
            purchase_invoice=invoice,
            product=self.product,
            quantity=5,
            price=Decimal('200.00')
        )
        
        # Verify supplier1's payable is updated
        self.supplier1.refresh_from_db()
        self.assertEqual(self.supplier1.payable, Decimal('1000.00'))  # 5 * 200
        
        # Verify supplier2's payable is still zero
        self.supplier2.refresh_from_db()
        self.assertEqual(self.supplier2.payable, Decimal('0.00'))
        
        # Change the invoice's supplier to supplier2
        invoice.supplier = self.supplier2
        invoice.save()
        
        # Refresh both suppliers
        self.supplier1.refresh_from_db()
        self.supplier2.refresh_from_db()
        
        # Supplier1's payable should be reduced to zero
        self.assertEqual(self.supplier1.payable, Decimal('0.00'))
        
        # Supplier2's payable should be increased
        self.assertEqual(self.supplier2.payable, Decimal('1000.00'))

    def test_invoice_deletion_reduces_supplier_payable(self):
        """Test that deleting an invoice reduces the supplier's payable amount."""
        # Create invoice
        invoice = PurchaseInvoice.objects.create(
            supplier=self.supplier1,
            shop=self.shop
        )
        
        # Add items to invoice
        PurchaseInvoiceItem.objects.create(
            purchase_invoice=invoice,
            product=self.product,
            quantity=10,
            price=Decimal('100.00')
        )
        
        # Verify supplier payable is updated
        self.supplier1.refresh_from_db()
        self.assertEqual(self.supplier1.payable, Decimal('1000.00'))
        
        # Delete the invoice
        invoice.delete()
        
        # Refresh supplier
        self.supplier1.refresh_from_db()
        
        # Check supplier payable is back to zero
        self.assertEqual(self.supplier1.payable, Decimal('0.00'))

    def test_invoice_total_change_updates_supplier_payable(self):
        """Test that changing an invoice's total amount updates the supplier's payable amount."""
        # Create invoice
        invoice = PurchaseInvoice.objects.create(
            supplier=self.supplier1,
            shop=self.shop
        )
        
        # Add item to invoice
        item = PurchaseInvoiceItem.objects.create(
            purchase_invoice=invoice,
            product=self.product,
            quantity=5,
            price=Decimal('100.00')
        )
        
        # Verify initial supplier payable
        self.supplier1.refresh_from_db()
        self.assertEqual(self.supplier1.payable, Decimal('500.00'))  # 5 * 100
        
        # Change the item quantity to increase the total
        item.quantity = 10  # from 5 to 10
        item.save()
        
        # Refresh supplier
        self.supplier1.refresh_from_db()
        
        # Check supplier payable is increased
        self.assertEqual(self.supplier1.payable, Decimal('1000.00'))  # 10 * 100
        
        # Change the item price to increase the total further
        item.price = Decimal('150.00')  # from 100 to 150
        item.save()
        
        # Refresh supplier
        self.supplier1.refresh_from_db()
        
        # Check supplier payable is increased again
        self.assertEqual(self.supplier1.payable, Decimal('1500.00'))  # 10 * 150

    def test_invoice_item_deletion_updates_supplier_payable(self):
        """Test that deleting an invoice item updates the supplier's payable amount."""
        # Create invoice with two items
        invoice = PurchaseInvoice.objects.create(
            supplier=self.supplier1,
            shop=self.shop
        )
        
        # Add first item
        item1 = PurchaseInvoiceItem.objects.create(
            purchase_invoice=invoice,
            product=self.product,
            quantity=5,
            price=Decimal('100.00')
        )
        
        # Add second item
        item2 = PurchaseInvoiceItem.objects.create(
            purchase_invoice=invoice,
            product=self.product,
            quantity=3,
            price=Decimal('200.00')
        )
        
        # Verify initial supplier payable: 5*100 + 3*200 = 500 + 600 = 1100
        self.supplier1.refresh_from_db()
        self.assertEqual(self.supplier1.payable, Decimal('1100.00'))
        
        # Delete first item
        item1.delete()
        
        # Refresh supplier
        self.supplier1.refresh_from_db()
        
        # Check supplier payable is reduced to second item only: 3*200 = 600
        self.assertEqual(self.supplier1.payable, Decimal('600.00'))
        
        # Delete second item
        item2.delete()
        
        # Refresh supplier
        self.supplier1.refresh_from_db()
        
        # Check supplier payable is now zero
        self.assertEqual(self.supplier1.payable, Decimal('0.00'))

    def test_multiple_supplier_invoice_independence(self):
        """Test that invoices for different suppliers update payable amounts independently."""
        # Create invoice for supplier1
        invoice1 = PurchaseInvoice.objects.create(
            supplier=self.supplier1,
            shop=self.shop
        )
        
        # Add item to first invoice
        PurchaseInvoiceItem.objects.create(
            purchase_invoice=invoice1,
            product=self.product,
            quantity=5,
            price=Decimal('100.00')
        )
        
        # Create invoice for supplier2
        invoice2 = PurchaseInvoice.objects.create(
            supplier=self.supplier2,
            shop=self.shop
        )
        
        # Add item to second invoice
        PurchaseInvoiceItem.objects.create(
            purchase_invoice=invoice2,
            product=self.product,
            quantity=3,
            price=Decimal('200.00')
        )
        
        # Refresh suppliers
        self.supplier1.refresh_from_db()
        self.supplier2.refresh_from_db()
        
        # Check each supplier's payable is updated correctly
        self.assertEqual(self.supplier1.payable, Decimal('500.00'))  # 5 * 100
        self.assertEqual(self.supplier2.payable, Decimal('600.00'))  # 3 * 200
        
        # Delete supplier1's invoice
        invoice1.delete()
        
        # Refresh suppliers
        self.supplier1.refresh_from_db()
        self.supplier2.refresh_from_db()
        
        # Check supplier1's payable is zero but supplier2's is unchanged
        self.assertEqual(self.supplier1.payable, Decimal('0.00'))
        self.assertEqual(self.supplier2.payable, Decimal('600.00'))