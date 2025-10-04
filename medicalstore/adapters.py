from django.contrib import messages
from django.shortcuts import redirect
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from .models import User_detail



class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        If the social account email matches an existing user, link it and log in.
        """

        email = sociallogin.account.extra_data.get('email')
        name = sociallogin.account.extra_data.get('name')


        if not email:
            messages.error(request, "We couldn't get your email from the social provider. Please sign up manually.")
            return redirect('user_register')  # or wherever you want to send them
        

        if sociallogin.is_existing:
            return  # Already linked

        else:
            try:
                user = User_detail.objects.get(email=email)
                sociallogin.connect(request, user)  # Link to existing account
                
            except User_detail.DoesNotExist:
                # Auto-create user without going to signup
                user = User_detail.objects.create(
                    email=email,
                    name=name,
                )
                user.set_unusable_password()
                user.save()
                sociallogin.connect(request, user)