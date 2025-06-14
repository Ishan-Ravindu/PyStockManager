# Generated by Django 5.2 on 2025-04-25 05:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("expense", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="expense",
            name="paid_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name="historicalexpense",
            name="paid_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
