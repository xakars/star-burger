# Generated by Django 3.2.15 on 2023-02-02 19:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0062_auto_20230202_1829'),
    ]

    operations = [
        migrations.RenameField(
            model_name='order',
            old_name='cook_restaurant',
            new_name='restaurant_cook',
        ),
    ]
