# Generated by Django 5.2 on 2025-04-12 20:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0002_historicalshop"),
    ]

    operations = [
        migrations.AlterField(
            model_name="historicalshop",
            name="location",
            field=models.TextField(null=True),
        ),
        migrations.AlterField(
            model_name="shop",
            name="location",
            field=models.TextField(null=True),
        ),
    ]
