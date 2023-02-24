from django.http import JsonResponse
from django.templatetags.static import static
import phonenumbers
from django.db import transaction
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer
from rest_framework.serializers import ListField, DictField
from rest_framework.serializers import ValidationError

from .models import Product
from .models import Order
from .models import OrderDetail


class OrserSerializer(ModelSerializer):
    products = ListField(child=DictField(), allow_empty=False, write_only=True)
    class Meta:
        model = Order
        fields = ['id', 'firstname', 'lastname', 'address', 'phonenumber', 'products']
        read_only_fields = ['id']

    def validate_phonenumber(self, value):
        phone_number = phonenumbers.parse(value, 'RU')
        if not phonenumbers.is_valid_number(phone_number):
            raise ValidationError(['Phone number field is not valid'])
        return value

    def validate_products(self, value):
        products_id = Product.objects.available().values_list('id', flat=True)
        orders_id = {product['product'] for product in value}
        if not orders_id.issubset(products_id):
            raise ValidationError([f'Недопустимый первичный ключ {orders_id.difference(products_id)}'])
        return value


def banners_list_api(request):
    # FIXME move data to db?
    return JsonResponse([
        {
            'title': 'Burger',
            'src': static('burger.jpg'),
            'text': 'Tasty Burger at your door step',
        },
        {
            'title': 'Spices',
            'src': static('food.jpg'),
            'text': 'All Cuisines',
        },
        {
            'title': 'New York',
            'src': static('tasty.jpg'),
            'text': 'Food is incomplete without a tasty dessert',
        }
    ], safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


def product_list_api(request):
    products = Product.objects.select_related('category').available()

    dumped_products = []
    for product in products:
        dumped_product = {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'special_status': product.special_status,
            'description': product.description,
            'category': {
                'id': product.category.id,
                'name': product.category.name,
            } if product.category else None,
            'image': product.image.url,
            'restaurant': {
                'id': product.id,
                'name': product.name,
            }
        }
        dumped_products.append(dumped_product)
    return JsonResponse(dumped_products, safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


@transaction.atomic
@api_view(['POST'])
def register_order(request):
    client_order = request.data
    serializer = OrserSerializer(data=client_order)
    serializer.is_valid(raise_exception=True)

    order = Order.objects.create(
        address=client_order['address'],
        firstname=client_order['firstname'],
        lastname=client_order['lastname'],
        phonenumber=client_order['phonenumber']
    )

    products = Product.objects.available()
    product_prices = {}
    for product in products:
        product_prices[product.id] = product.price
    product_card = [OrderDetail(
        order=order,
        product_id=product['product'],
        amount=product['quantity'],
        position_price=product_prices[product['product']]
        ) for product in client_order['products']]
    OrderDetail.objects.bulk_create(product_card)

    serializer = OrserSerializer(order)
    return Response(serializer.data)
