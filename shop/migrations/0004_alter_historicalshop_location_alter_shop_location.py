# Generated by Django 5.2 on 2025-04-12 20:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0003_alter_historicalshop_location_alter_shop_location"),
    ]

    operations = [
        migrations.AlterField(
            model_name="historicalshop",
            name="location",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="shop",
            name="location",
            field=models.TextField(blank=True, null=True),
        ),
    ]
