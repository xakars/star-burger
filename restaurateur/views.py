from django import forms
from django.shortcuts import redirect, render
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test
from ya_geocoder.geocoder import fetch_coordinates, GeoSaveError
from geopy import distance
from django.conf import settings

from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views

from foodcartapp.models import Product, Restaurant
from foodcartapp.models import Order
from ya_geocoder.models import Place


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


def serialize_order(order, places):
    restaurant = None
    restaurants = None
    order_coords = None

    if order.restaurant_cook:
        restaurant = order.restaurant_cook
    else:
        for place in places:
            if order.address == place.address:
                order_coords = place.lat, place.lon
                break
        if not order_coords:
            try:
                order_coords = fetch_coordinates(settings.YA_API_KEY, order.address)
                place = Place.objects.create(address=order.address, lat=order_coords[0], lon=order_coords[1])
                place.save()
            except GeoSaveError:
                order_coords = None

        restaurants = []
        restaurants_with_distance = {}
        for item in order.details.all():
            for restaurant_menu_item in item.product.menu_items.all():
                restaurants.append(restaurant_menu_item.restaurant.address)
        rest_coords = None
        for rest_address in set(restaurants):
            for place in places:
                if place.address == rest_address:
                    rest_coords = place.lat, place.lon
                    restaurants_with_distance[rest_address] = round(distance.distance(rest_coords, order_coords).km, 3)
            if not rest_coords:
                try:
                    rest_coord = fetch_coordinates(settings.YA_API_KEY, rest_address)
                    place = Place.objects.create(address=rest_address, lat=rest_coord[0], lon=rest_coord[1])
                    place.save()
                    restaurants_with_distance[rest_address] = round(distance.distance(rest_coords, order_coords).km, 3)
                except GeoSaveError:
                    restaurants = None

        order_can_be_prepare_in = sorted(restaurants_with_distance.items(), key=lambda item: item[1])
        restaurants = order_can_be_prepare_in

    return {
        'id': order.id,
        'status': order.get_status_display(),
        'total_price': order.total,
        'customer': f'{order.firstname} {order.lastname}',
        'phonenumber': order.phonenumber,
        'address': order.address,
        'comment': order.comment,
        'payment_method': order.get_payment_method_display(),
        'restaurant':  restaurant,
        'restaurants': restaurants,
    }


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_orders(request):
    orders = Order.objects.get_total_price()\
                          .get_unprocessed_orders()\
                          .prefetch_related('details__product__menu_items__restaurant')

    orders_addresses = [order.address for order in orders]
    restaurants = Restaurant.objects.all()
    restaurants_addresses = [restaurant.address for restaurant in restaurants]

    address = orders_addresses + restaurants_addresses
    places = Place.objects.filter(address__in=address)

    context = {
        'order_items': [serialize_order(order, places) for order in orders]
    }
    return render(request, template_name='order_items.html', context=context)
