from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from phonenumber_field.modelfields import PhoneNumberField
from django.db.models import Sum, F
from ya_geocoder.models import Place
from geopy import distance
from ya_geocoder.geocoder import fetch_coordinates
from django.conf import settings
from ya_geocoder.geocoder import GeoSaveError


class OrderQuerySet(models.QuerySet):
    def get_total_price(self):
        return self.annotate(total=Sum(F('details__position_price') * F('details__amount')))

    def get_unprocessed_orders(self):
        return self.filter(status='OPEN')

    def get_restaurants(self):
        orders_addresses = [order.address for order in self]
        restaurants = Restaurant.objects.all()
        restaurants_addresses = [restaurant.address for restaurant in restaurants]
        addresses = orders_addresses + restaurants_addresses
        places = Place.objects.filter(address__in=addresses)

        for order in self:
            order_coords = None
            for place in places:
                if order.address == place.address:
                    order_coords = place.lat, place.lon
                    break
            if not order_coords:
                try:
                    order_coords = fetch_coordinates(settings.YA_API_KEY, order.address)
                    lat, lon = order_coords
                    Place.objects.create(address=order.address, lat=lat, lon=lon)
                except GeoSaveError:
                    order.restaurants = None
                    break

            restaurants_addresses = []
            restaurants_with_distance = {}
            for item in order.details.all():
                for restaurant_menu_item in item.product.menu_items.all():
                    restaurants_addresses.append(restaurant_menu_item.restaurant.address)

            for restaurant_address in set(restaurants_addresses):
                rest_coords = None
                for place in places:
                    if place.address == restaurant_address:
                        rest_coords = place.lat, place.lon
                        restaurants_with_distance[restaurant_address] = round(distance.distance(rest_coords, order_coords).km, 3)
                        break
                if not rest_coords:
                    try:
                        rest_coords = fetch_coordinates(settings.YA_API_KEY, restaurant_address)
                        lat, lon = rest_coords
                        Place.objects.create(address=restaurant_address, lat=lat, lon=lon)
                        restaurants_with_distance[restaurant_address] = round(distance.distance(rest_coords, order_coords).km, 3)
                    except GeoSaveError:
                        order.restaurants = None

            order_can_be_prepare_in = sorted(restaurants_with_distance.items(), key=lambda item: item[1])
            order.restaurants = order_can_be_prepare_in
        return self


class Restaurant(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    address = models.CharField(
        'адрес',
        max_length=100,
        blank=True,
    )
    contact_phone = models.CharField(
        'контактный телефон',
        max_length=50,
        blank=True,
    )

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        products = (
            RestaurantMenuItem.objects
            .filter(availability=True)
            .values_list('product')
        )
        return self.filter(pk__in=products)


class ProductCategory(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    category = models.ForeignKey(
        ProductCategory,
        verbose_name='категория',
        related_name='products',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    image = models.ImageField(
        'картинка'
    )
    special_status = models.BooleanField(
        'спец.предложение',
        default=False,
        db_index=True,
    )
    description = models.TextField(
        'описание',
        max_length=200,
        blank=True,
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'

    def __str__(self):
        return self.name


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name='menu_items',
        verbose_name="ресторан",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='menu_items',
        verbose_name='продукт',
    )
    availability = models.BooleanField(
        'в продаже',
        default=True,
        db_index=True
    )

    class Meta:
        verbose_name = 'пункт меню ресторана'
        verbose_name_plural = 'пункты меню ресторана'
        unique_together = [
            ['restaurant', 'product']
        ]

    def __str__(self):
        return f"{self.restaurant.name} - {self.product.name}"


class Order(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('CARD', 'Электронно'),
        ('CASH', 'Наличными')
    ]
    STATUS_CHOICES = [
        ('OPEN', 'Необработанный'),
        ('PROGRESSING', 'Готовится'),
        ('Transit', 'В пути'),
        ('CLOSED', 'Закрыт')
    ]

    payment_method = models.CharField(
        'Способ оплаты',
        db_index=True,
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES
    )
    status = models.CharField(
        'Статус заказа',
        db_index=True,
        max_length=20,
        choices=STATUS_CHOICES,
        default='OPEN'
    )
    address = models.CharField(
        'адрес',
        max_length=50
    )
    firstname = models.CharField(
        'имя',
        max_length=50
    )
    lastname = models.CharField(
        'фамилия',
        max_length=50
    )
    phonenumber = PhoneNumberField(
        'Мобильный номер',
        region='RU'
    )
    comment = models.TextField(
        'Комментарий',
        blank=True
    )
    registrated_at = models.DateTimeField(
        verbose_name='дата регистрации',
        default=timezone.now,
        db_index=True,
        null=True
    )
    called_at = models.DateTimeField(
        verbose_name='дата звонка',
        db_index=True,
        null=True
    )
    delivered_at = models.DateTimeField(
        verbose_name='дата доставки',
        db_index=True,
        null=True
    )
    restaurant_cook = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name='готовит ресторан',
        null=True,
        blank=True
    )
    objects = OrderQuerySet.as_manager()

    class Meta:
        verbose_name='Заказ'
        verbose_name_plural='Заказы'

    def __str__(self):
        return f'{self.firstname} {self.lastname} {self.address}'


class OrderDetail(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='details',
        verbose_name='заказ'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='details',
        verbose_name='товар',
    )
    position_price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    amount = models.PositiveSmallIntegerField(
        'количество',
        validators=[MinValueValidator(1)]
    )

    class Meta:
        verbose_name = 'Элемент заказа'
        verbose_name_plural = 'Элементы заказа'

    def __str__(self):
        return f'{self.product.name} {self.order}'
