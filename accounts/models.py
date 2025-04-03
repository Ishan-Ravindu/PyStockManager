from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

class Account(models.Model):
    name = models.CharField(max_length=100)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"Account {self.name}"

    def update_balance(self, amount):
        self.balance += amount
        self.save(update_fields=['balance'])

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
        """Perform the withdrawal."""
        self.full_clean()
        super().save(*args, **kwargs)
        self.account.update_balance(-self.amount)

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
        super().clean()

    def save(self, *args, **kwargs):
        """Perform the transfer between accounts."""
        self.full_clean()
        super().save(*args, **kwargs)
        self.from_account.update_balance(-self.amount)
        self.to_account.update_balance(self.amount)