from django.shortcuts import render,redirect,get_object_or_404
from django.http import HttpResponse
from .models import Product,Customer,Category
from django import forms
from django.contrib.auth.models import User,auth
from django.contrib.auth.views import LoginView,LogoutView
from django.contrib.auth import login,authenticate,logout
from .models import SessionCart,ItemCart,Product
import stripe
from django.conf import settings

def index(request):
    product = Product.get_products()

    return render(request, 'index.html', {'products': product})


def cart_page(request):
    user = request.user
    total = 0

    items = ItemCart.objects.filter(user = request.user)
    for item in items:
        total += item.total_cart_value



    return render(request, 'cart_page.html',{'items':items,'total':total})


class NewForm(forms.Form):
    name = forms.CharField(min_length=4,max_length=40,widget=forms.TextInput(attrs={'name':'name','type':"text" ,'class':"form-control",'id':"inputName4"}))
    password = forms.CharField(min_length=4,max_length=12,widget=forms.TextInput(attrs={'name':'password','type':"password",'class':"form-control",'id':"inputPassword4"}))
    email = forms.CharField(max_length=40,widget=forms.TextInput(attrs={'type':"email",'class':"form-control",'id':"inputEmail4"}))
    address = forms.CharField(max_length=300,widget=forms.TextInput(attrs={'type':"text",'class':"form-control",'id':"inputAddress",'placeholder':"1234 Main St"}))
    city = forms.CharField(max_length=30,widget=forms.TextInput(attrs={'type':"text",'class':"form-control",'id':"inputCity"}))
    zip = forms.IntegerField(widget=forms.TextInput(attrs={'type':"number",'class':"form-control",'id':"inputZip"}))


def sign_up(request):
    if request.method == 'POST':
        form = NewForm(request.POST)
        print(form.is_valid())
        form.is_valid()
        customer = User.objects.create_user(username=form.cleaned_data['name'],
                                            email=form.cleaned_data['email'],
                                            password=form.cleaned_data['password'])
        customer.save()
        customer = Customer(name=form.cleaned_data['name'],
                            email=form.cleaned_data['email'],
                            address=form.cleaned_data['address'],
                            city=form.cleaned_data['city'],
                            zip=form.cleaned_data['zip'])
        customer.save()

        return redirect('index')

    return render(request,'signup_form.html',{'form':NewForm})

class LoginUse(LoginView):
    def __init__(self):
        self.form = NewForm()

    def get(self,request):
        return render(request,'login.html',{'form':self.form})

    def post(self,request):
        form = NewForm(request.POST)
        form.is_valid()
        username = form.cleaned_data['name']
        password = form.cleaned_data['password']
        user = auth.authenticate(username=username,password=password)
        if user is not None:
            login(request,user)
            return redirect('index')
        else:
            return render(request,'login.html',{'form':self.form})




class LogOut(LogoutView):
    next_page = 'index'


def _cart_id(request):
    cart = request.session.session_key
    try:
        session = SessionCart.objects.get(user = request.user)
        return session.spc_id
    except SessionCart.DoesNotExist:
        cart = request.session.create()
        session = SessionCart(spc_id=request.session.session_key,user=request.user)
        session.save()

        return session.spc_id

def add_to_cart(request,product):
    product = Product.objects.get(slug=product)
    user = request.user.get_username()
    try:
        cart = SessionCart.objects.get(spc_id=_cart_id(request))
    except SessionCart.DoesNotExist:
        cart = SessionCart.objects.create(
            spc_id=_cart_id(request),user=user)
        cart.save()
    try:
        cart_items = ItemCart.objects.get(slug=product.slug,product=str(product),
                                          cart=cart,user=user)
        cart_items.product_quantity += 1
        cart_items.total_cart_value += product.price
        cart_items.save()
        print(request.path)
        if request.path == f'/cart/add/{product.slug}':
            return redirect('cart')


        return redirect('index')
    except ItemCart.DoesNotExist:
        cart_items = ItemCart.objects.create(slug=product.slug,user=user,
                                             active=True,product=str(product),
                                             cart=cart,product_quantity=1,
                                             product_price=product.price,
                                             product_image=product.product_image,
                                             total_cart_value=product.price)
        cart_items.save()

        return redirect('index')




def payment_with_stripe(request):
    stripe.api_key = settings.STRIPE_SEC_KEY
    li = []
    items = ItemCart.objects.filter(user = request.user).values()
    for item in items.values():
        new_data = {
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': item.get('product'),
                },
                'unit_amount': item.get('product_price') * 100,
            },
            'quantity': item.get('product_quantity'),}

        li.append(new_data)


    session = stripe.checkout.Session.create(
        line_items=[*li],
        mode='payment',
        success_url='http://localhost:8000/payment/success',
        cancel_url='http://localhost:8000/payment_fail/cancel',
    )

    return redirect(session.url, code=303)

def success(request):
    session = SessionCart.objects.filter(user=request.user)
    session.delete()

    return render(request,'success.html')


def remove_cart_obj(request,product):
    cart = SessionCart.objects.get(spc_id=_cart_id(request),user=request.user)
    product = get_object_or_404(Product,slug=product)
    cart_item = ItemCart.objects.get(product=product,cart=cart)
    if cart_item.product_quantity > 1:
        cart_item.product_quantity -= 1
        cart_item.total_cart_value -= cart_item.product_price
        cart_item.save()
        return redirect('cart')
    else:
        cart_item.delete()
        return redirect('cart')



def search(request):
    try:
        products = Product.objects.filter(slug__contains=request.GET.get('name'))
        if products:
            return render(request,'index.html',{'products':products})

        category = Category.objects.filter(slug__contains=request.GET.get('name'))[0]
        if category:
            products = Product.objects.filter(category__slug=category)
            return render(request,'index.html',{'products':products})
    except:
        return render(request,'index.html',{'products':None})