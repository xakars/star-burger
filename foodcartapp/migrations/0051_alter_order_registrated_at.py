# Generated by Django 3.2.15 on 2023-01-13 19:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0050_auto_20230113_1939'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='registrated_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, null=True),
        ),
    ]
