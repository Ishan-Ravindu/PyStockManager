from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from simple_history.models import HistoricalRecords

class Account(models.Model):
    name = models.CharField(max_length=100, unique=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    history = HistoricalRecords()

    def __str__(self):
        return f"Account {self.name}"

    def update_balance(self, amount, related_obj=None, transaction_type=None, action_type=None, description=''):
        """
        Update account balance without transaction history recording.
        
        Args:
            amount: Decimal amount to change the balance by (positive or negative)
        """
        self.balance += amount
        self.save(update_fields=['balance'])
    
    def adjust_balance(self, amount, description='Manual adjustment', performed_by=None):
        """
        Make a manual adjustment to the account balance.
        
        Args:
            amount: Amount to adjust (positive or negative)
            description: Description of the adjustment (unused)
            performed_by: User who performed the adjustment (unused)
        """
        # Directly update balance
        self.balance += amount
        self.save(update_fields=['balance'])
        
        return True

class Withdraw(models.Model):
    account = models.ForeignKey(Account, related_name='withdrawals', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    withdrawn_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

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
    history = HistoricalRecords()

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