from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect, render

from .forms import (
    CustomAuthenticationForm,
    ProfileUpdateForm,
    RegistrationForm,
    UserUpdateForm,
)
from .utils import get_client_ip, is_locked_out, register_failed_attempt, reset_attempts


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome to CloudDNA, {user.first_name}! Your account has been created.')
            return redirect('dashboard:home')
    else:
        form = RegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


class CustomLoginView(SuccessMessageMixin, LoginView):
    template_name = 'accounts/login.html'
    authentication_form = CustomAuthenticationForm
    redirect_authenticated_user = True
    success_message = 'Welcome back, %(username)s!'

    def dispatch(self, request, *args, **kwargs):
        self.lockout_identifier = None
        if request.method == 'POST':
            username = request.POST.get('username', '').strip().lower()
            ip = get_client_ip(request)
            self.lockout_identifier = f'{username}:{ip}'
            if username and is_locked_out(self.lockout_identifier):
                messages.error(
                    request,
                    'Too many failed login attempts. Please wait a few minutes before trying again.',
                )
                return render(request, self.template_name, {'form': self.get_form_class()()})
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        if self.lockout_identifier:
            reset_attempts(self.lockout_identifier)

        remember_me = form.cleaned_data.get('remember_me')
        if remember_me:
            self.request.session.set_expiry(60 * 60 * 24 * 14)  # 14 days
        else:
            self.request.session.set_expiry(0)  # expires on browser close

        return super().form_valid(form)

    def form_invalid(self, form):
        if self.lockout_identifier:
            register_failed_attempt(self.lockout_identifier)
        return super().form_invalid(form)

    def get_success_message(self, cleaned_data):
        return self.success_message % {'username': self.request.user.first_name or self.request.user.username}


def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
        messages.info(request, 'You have been logged out.')
    return redirect('accounts:login')


@login_required
def profile_view(request):
    profile = request.user.profile

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('accounts:profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=profile)

    return render(request, 'accounts/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile,
    })


@login_required
def settings_view(request):
    if request.method == 'POST':
        password_form = PasswordChangeForm(user=request.user, data=request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password has been changed successfully.')
            return redirect('accounts:settings')
    else:
        password_form = PasswordChangeForm(user=request.user)

    return render(request, 'accounts/settings.html', {'password_form': password_form})
