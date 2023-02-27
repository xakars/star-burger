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


def serialize_order(order):
    place, created = Place.objects.get_or_create(
        address=order.address,
        defaults={
            'lat': None,
            'lon': None
        }
    )
    if created:
        try:
            order_coords = fetch_coordinates(settings.YA_API_KEY, order.address)
            place.lat, place.lon = order_coords
            place.save()
        except GeoSaveError:
            order_coords = None

    order_coords = place.lat, place.lon
    restaurant = None
    restaurants = None
    if order.restaurant_cook:
        restaurant = order.restaurant_cook
    elif not order_coords or order_coords == (0.0, 0.0):
        pass
    else:
        restaurants = []
        restaurants_with_distance = {}
        for item in order.details.all():
            for restaurant_menu_item in item.product.menu_items.all():
                restaurants.append(restaurant_menu_item.restaurant.address)
        for address in set(restaurants):
            place, created = Place.objects.get_or_create(
                            address=address,
                            defaults={
                                'lat': None,
                                'lon': None
                            }
            )
            if created:
                try:
                    rest_coord = fetch_coordinates(settings.YA_API_KEY, restaurant)
                    place.lat, place.lon = rest_coord
                    place.save()
                except GeoSaveError:
                    restaurants = None
                    continue
            rest_coord = place.lat, place.lon
            restaurants_with_distance[address] = round(distance.distance(rest_coord, order_coords).km, 3)
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

    context = {
        'order_items': [serialize_order(order) for order in orders]
    }
    return render(request, template_name='order_items.html', context=context)
