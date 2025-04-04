from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class Account(models.Model):
    name = models.CharField(max_length=100)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"Account {self.name}"

    def update_balance(self, amount, related_obj=None, transaction_type=None, action_type=None, description=''):
        """
        Update account balance and record the transaction history.
        
        Args:
            amount: Decimal amount to change the balance by (positive or negative)
            related_obj: The related object that triggered this update (e.g., Withdraw, AccountTransfer)
            transaction_type: Type of transaction from AccountTransactionHistory.TRANSACTION_TYPES
            action_type: Type of action from AccountTransactionHistory.ACTION_TYPES
            description: Optional description of the transaction
        """
        previous_balance = self.balance
        
        # Set flag to avoid double history entries with direct balance changes
        self._skip_balance_history = True
        
        self.balance += amount
        self.save(update_fields=['balance'])
        
        # Remove flag
        self._skip_balance_history = False
        
        # Create transaction history record if transaction_type is provided
        if transaction_type:
            from django.contrib.contenttypes.models import ContentType
            from .models import AccountTransactionHistory
            
            history = AccountTransactionHistory(
                account=self,
                amount=amount,
                previous_balance=previous_balance,
                new_balance=self.balance,
                transaction_type=transaction_type,
                action_type=action_type or 'CREATE',
                description=description
            )
            
            # Set the related object if provided
            if related_obj:
                history.content_type = ContentType.objects.get_for_model(related_obj)
                history.object_id = related_obj.pk
                
            history.save()
    
    def adjust_balance(self, amount, description='Manual adjustment', performed_by=None):
        """
        Make a manual adjustment to the account balance and record it in history.
        
        Args:
            amount: Amount to adjust (positive or negative)
            description: Description of the adjustment
            performed_by: User who performed the adjustment (optional)
        """
        user_info = f" by {performed_by}" if performed_by else ""
        adjustment_desc = f"{description}{user_info}"
        
        # Use update_balance to handle the history recording
        self.update_balance(
            amount=amount,
            transaction_type='ADJUSTMENT',
            action_type='CREATE',
            description=adjustment_desc
        )
        
        return True

class Withdraw(models.Model):
    account = models.ForeignKey(Account, related_name='withdrawals', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    withdrawn_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Withdraw {self.amount} from {self.account}"

    def clean(self):
        """Validate that the withdrawal amount doesn't exceed the account's balance."""
        if self.amount > self.account.balance:
            raise ValidationError('Insufficient balance for the withdrawal.')
        super().clean()

    def save(self, *args, **kwargs):
        """Save the withdrawal without updating the balance (signals will handle it)."""
        self.full_clean()
        super().save(*args, **kwargs)


class AccountTransfer(models.Model):
    from_account = models.ForeignKey(Account, related_name='outgoing_transfers', on_delete=models.CASCADE)
    to_account = models.ForeignKey(Account, related_name='incoming_transfers', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transferred_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transfer {self.amount} from {self.from_account} to {self.to_account}"

    def clean(self):
        """Validate that the transfer amount doesn't exceed the balance of the from_account."""
        if self.amount > self.from_account.balance:
            raise ValidationError('Insufficient balance in the source account for the transfer.')
        if self.from_account == self.to_account:
            raise ValidationError('Cannot transfer to the same account.')
        super().clean()

    def save(self, *args, **kwargs):
        """Save the transfer without updating balances (signals will handle it)."""
        self.full_clean()
        super().save(*args, **kwargs)


class AccountTransactionHistory(models.Model):
    TRANSACTION_TYPES = (
        ('WITHDRAW', 'Withdrawal'),
        ('DEPOSIT', 'Deposit'),
        ('TRANSFER_OUT', 'Transfer Out'),
        ('TRANSFER_IN', 'Transfer In'),
        ('ADJUSTMENT', 'Manual Adjustment'),
    )

    ACTION_TYPES = (
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
    )

    account = models.ForeignKey(Account, related_name='transaction_history', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text='Amount changed (positive or negative)')
    previous_balance = models.DecimalField(max_digits=12, decimal_places=2)
    new_balance = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    action_type = models.CharField(max_length=10, choices=ACTION_TYPES)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    description = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Account histories'
    
    def __str__(self):
        return f"{self.account} {self.transaction_type} of {self.amount} on {self.timestamp}"