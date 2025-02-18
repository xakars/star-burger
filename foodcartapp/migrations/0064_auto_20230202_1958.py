# Generated by Django 3.2.15 on 2023-02-02 19:58

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0063_rename_cook_restaurant_order_restaurant_cook'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='called_at',
            field=models.DateTimeField(db_index=True, null=True, verbose_name='дата звонка'),
        ),
        migrations.AlterField(
            model_name='order',
            name='delivered_at',
            field=models.DateTimeField(db_index=True, null=True, verbose_name='дата доставки'),
        ),
        migrations.AlterField(
            model_name='order',
            name='registrated_at',
            field=models.DateTimeField(db_index=True, default=django.utils.timezone.now, null=True, verbose_name='дата регистрации'),
        ),
    ]
