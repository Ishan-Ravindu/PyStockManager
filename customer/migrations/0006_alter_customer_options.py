# Generated by Django 5.2 on 2025-05-07 20:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("customer", "0005_alter_customer_options"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="customer",
            options={
                "permissions": [("can_view_icon_customer", "Can view icon customer")]
            },
        ),
    ]
