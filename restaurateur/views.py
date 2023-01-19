from django import forms
from django.shortcuts import redirect, render
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test
from itertools import chain


from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views


from foodcartapp.models import Product, Restaurant
from foodcartapp.models import Order


class Login(forms.Form):
    username = forms.CharField(
        label='Логин', max_length=75, required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Укажите имя пользователя'
        })
    )
    password = forms.CharField(
        label='Пароль', max_length=75, required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        })
    )


class LoginView(View):
    def get(self, request, *args, **kwargs):
        form = Login()
        return render(request, "login.html", context={
            'form': form
        })

    def post(self, request):
        form = Login(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.is_staff:  # FIXME replace with specific permission
                    return redirect("restaurateur:RestaurantView")
                return redirect("start_page")

        return render(request, "login.html", context={
            'form': form,
            'ivalid': True,
        })


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('restaurateur:login')


def is_manager(user):
    return user.is_staff  # FIXME replace with specific permission


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_products(request):
    restaurants = list(Restaurant.objects.order_by('name'))
    products = list(Product.objects.prefetch_related('menu_items'))

    products_with_restaurant_availability = []
    for product in products:
        availability = {item.restaurant_id: item.availability for item in product.menu_items.all()}
        ordered_availability = [availability.get(restaurant.id, False) for restaurant in restaurants]

        products_with_restaurant_availability.append(
            (product, ordered_availability)
        )

    return render(request, template_name="products_list.html", context={
        'products_with_restaurant_availability': products_with_restaurant_availability,
        'restaurants': restaurants,
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_restaurants(request):
    return render(request, template_name="restaurants_list.html", context={
        'restaurants': Restaurant.objects.all(),
    })


def serialize_order(order, product_in_restaurants):
    restaurant = []
    for item in order.items.all():
        restaurant.append(product_in_restaurants.get(item.product.id))
    order_can_be_prepare_in = set(chain(*restaurant))

    restaurant_template = ''
    if order.restaurant:
        restaurant_template = f'Готовит {order.restaurant}'
    else:
        restaurant_template = f'Может быть приготовлен ресторанами: {", ".join(order_can_be_prepare_in)}'

    return {
        'id': order.id,
        'status': order.get_status_display(),
        'total_price': order.total,
        'customer': f'{order.firstname} {order.lastname}',
        'phonenumber': order.phonenumber,
        'address': order.address,
        'comment': order.comment,
        'payment_method': order.get_payment_method_display(),
        'restaurants': restaurant_template,
    }


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_orders(request):
    orders = Order.objects.get_total_price()\
                          .get_unprocessed_order()\
                          .prefetch_related('items__product')

    products = Product.objects.prefetch_related('menu_items__restaurant')
    product_in_restaurants = {}
    for product in products:
        availability = {item.restaurant_id: item.restaurant.name for item in product.menu_items.all()}
        product_in_restaurants[product.id] = list(availability.values())

    context = {
        'order_items': [serialize_order(order, product_in_restaurants) for order in orders]
    }
    return render(request, template_name='order_items.html', context=context)
