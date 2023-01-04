from django.http import JsonResponse
from django.templatetags.static import static
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import phonenumbers


from .models import Product
from .models import Order
from .models import OrderDetail


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


@api_view(['POST'])
def register_order(request):
    client_order = request.data
    print(client_order)
    keys = {'products', 'firstname', 'lastname', 'phonenumber', 'address'}
    if not keys <= client_order.keys():
        content = {'error': '"products", "firstname", "lastname", "phonenumber", "address" are required parameters'}
        return Response(content, status=400)
    if not isinstance(client_order['products'], list):
        content = {'error': f'expected list instead of {type(client_order["products"])}'}
        return Response(content, status=400)
    if not client_order['products']:
        content = {'error': 'product list is empty'}
        return Response(content, status=400)

    if not (client_order['firstname'] and client_order['lastname'] and client_order['phonenumber'] and client_order['address']):
        content = {'error': '"firstname", "lastname", "phonenumber", "address" must not be empty'}
        return Response(content, status=400)

    phone_number = phonenumbers.parse(client_order['phonenumber'], 'RU')
    if not phonenumbers.is_valid_number(phone_number):
        content = {'error': 'phone_number is not valid'}
        return Response(content, status=400)

    products_id = Product.objects.available().values_list('id', flat=True)
    orders_id = {product['product'] for product in client_order['products']}
    if not orders_id.issubset(products_id):
        content = {'error': 'no such product'}
        return Response(content, status=400)

    if not isinstance(client_order['firstname'], str):
        content = {'error': 'first name must be string'}
        return Response(content, status=400)

    order = Order.objects.create(
        address=client_order['address'],
        first_name=client_order['firstname'],
        last_name=client_order['lastname'],
        phone_number=client_order['phonenumber']
    )

    product_card = []
    for product in client_order['products']:
        product_card.append(OrderDetail(
            order=order,
            product_id=product['product'],
            amount=product['quantity'])
        )
    OrderDetail.objects.bulk_create(product_card)

    return Response({})
