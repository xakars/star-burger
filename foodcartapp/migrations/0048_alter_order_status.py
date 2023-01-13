# Generated by Django 3.2.15 on 2023-01-13 18:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0047_alter_order_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('OPEN', 'Необработанный'), ('PROGRESSING', 'Готовится'), ('Transit', 'В пути'), ('CLOSED', 'Закрыт')], db_index=True, default='OPEN', max_length=20, verbose_name='Статус заказа'),
        ),
    ]
