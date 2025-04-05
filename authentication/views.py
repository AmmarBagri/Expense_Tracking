from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.models import User
import json
from django.http import JsonResponse
from validate_email import validate_email
from django.contrib import messages
from django.core.mail import EmailMessage
from django.utils.encoding import force_bytes, force_str, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from .utils import account_activation_token
from django.db import transaction
from django.contrib import auth
from django.contrib.auth.decorators import login_required
# Create your views here.


class EmailValidationView(View):
    def post(self, request):
        data = json.loads(request.body)
        email = data['email']
        if not validate_email(email):
            return JsonResponse({'emailerror': 'Email is invalid'}, status=400)
        if User.objects.filter(email=email).exists():
            return JsonResponse({'emailerror': 'sorry email in use, choose another one'}, status=409)
        return JsonResponse({'email_valid': True})


class UsernameValidationView(View):
    def post(self, request):
        data = json.loads(request.body)
        username = data['username']
        if not str(username).isalnum():
            return JsonResponse({'usernameerror': 'username should only contain alphanumeric characters'}, status=400)
        if User.objects.filter(username=username).exists():
            return JsonResponse({'usernameerror': 'sorry username in use, choose another one'}, status=409)
        return JsonResponse({'username_valid': True})


class RegistrationView(View):
    def get(self, request):
        return render(request, 'authentication/register.html')

    def post(self, request):
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        context = {
            'fieldValues': request.POST
        }

        if not username or not email or not password:
            messages.error(request, 'Please fill all fields')
            return render(request, 'authentication/register.html', context)

        try:
            with transaction.atomic():
                if User.objects.filter(username=username).exists():
                    messages.error(request, 'Username already exists')
                    return render(request, 'authentication/register.html', context)
                
                if User.objects.filter(email=email).exists():
                    messages.error(request, 'Email already exists')
                    return render(request, 'authentication/register.html', context)
                
                if len(password) < 8:
                    messages.error(request, 'Password must be at least 8 characters long')
                    return render(request, 'authentication/register.html', context)
                
                if not any(char.isdigit() for char in password):
                    messages.error(request, 'Password must contain at least one number')
                    return render(request, 'authentication/register.html', context)
                
                if not any(char.isupper() for char in password):
                    messages.error(request, 'Password must contain at least one uppercase letter')
                    return render(request, 'authentication/register.html', context)

                user = User.objects.create_user(username=username, email=email, password=password)
                user.is_active = False
                user.save()

                # Send activation email
                email_subject = "Activate Your Account - Expense Tracker"
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                domain = get_current_site(request).domain
                link = reverse('activate', kwargs={
                    'uidb64': uidb64, 
                    'token': account_activation_token.make_token(user)
                })
                activate_url = 'http://'+domain+link
                email_body = f'''
                Hi {user.username},
                
                Thank you for registering with Expense Tracker. Please click the link below to verify your account:
                
                {activate_url}
                
                If you didn't register for an account, please ignore this email.
                
                Best regards,
                Expense Tracker Team
                '''
                
                from django.conf import settings
                email = EmailMessage(
                    email_subject,
                    email_body,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                )
                email.send(fail_silently=False)
                messages.success(request, 'Account created successfully. Please check your email to activate your account.')
                return redirect('login')

        except Exception as e:
            messages.error(request, f"Registration error: {str(e)}")
            return render(request, 'authentication/register.html', context)


class LoginView(View):
    def get(self, request):
        return render(request, 'authentication/login.html')

    def post(self, request):
        username = request.POST['username']
        password = request.POST['password']

        if not username or not password:
            messages.error(request, "Please fill all fields")
            return render(request, "authentication/login.html")

        try:
            # First check if the username exists
            if not User.objects.filter(username=username).exists():
                messages.error(request, "Username does not exist")
                return render(request, "authentication/login.html")

            user = auth.authenticate(username=username, password=password)
            if user is None:
                messages.error(request, "Invalid password")
                return render(request, "authentication/login.html")
            
            if not user.is_active:
                messages.error(request, 'Account is not active. Please check your email for the activation link.')
                return render(request, 'authentication/login.html')
            
            auth.login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('expenses')

        except Exception as e:
            messages.error(request, f"Login error: {str(e)}")
            return render(request, "authentication/login.html")


class VerificationView(View):
    def get(self, request, uidb64, token):
        try:
            id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=id)

            if user.is_active:
                messages.info(request, 'Account is already activated')
                return redirect('login')

            if account_activation_token.check_token(user, token):
                user.is_active = True
                user.save()
                messages.success(request, 'Account activated successfully. You can now login.')
                return redirect('login')
            else:
                messages.error(request, 'Invalid activation link')
                return redirect('login')
        except Exception as e:
            messages.error(request, 'Something went wrong during activation')
            return redirect('login')


class LogoutView(View):
    def get(self, request):
        if request.user.is_authenticated:
            auth.logout(request)
            messages.success(request, "You have been logged out")
            return redirect('login')
        else:
            return redirect('login')
