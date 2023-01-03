from django.http import JsonResponse
from django.templatetags.static import static
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status


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

    if 'products' not in client_order:
        content = {'error': '"products" is required parameter'}
        return Response(content, status=status.HTTP_400_BAD_REQUEST)
    if not isinstance(client_order['products'], list):
        content = {'error': f'expected list instead of {type(client_order["products"])}'}
        return Response(content, status=status.HTTP_400_BAD_REQUEST)
    if not client_order['products']:
        content = {'error': 'product list is empty'}
        return Response(content, status=status.HTTP_400_BAD_REQUEST)

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
