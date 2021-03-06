from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import EmailMessage
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic import TemplateView, UpdateView, FormView, DeleteView, DetailView
from rolepermissions.mixins import HasPermissionsMixin
from rolepermissions.roles import assign_role, clear_roles

from CTAFramework import settings
from .forms import UserForm, EditUserForm, RequestAccessForm
from .models import User, Task
from .ibmauth import LDAPBackend

from base64 import b64encode
from django.contrib.auth.tokens import default_token_generator


class UsersView(LoginRequiredMixin, HasPermissionsMixin, TemplateView):
    """Just a template view for render the data tables user list """
    template_name = "users.html"
    required_permission = 'read_users'


class CreateUserView(LoginRequiredMixin, HasPermissionsMixin, FormView):
    model = User
    form_class = UserForm
    template_name = "create-edit-user.html"
    required_permission = "create_users"

    def get_success_url(self):
        return reverse_lazy("users")

    def form_valid(self, form):
        extra_fields = {
            'first_name': form.instance.first_name,
            'last_name': form.instance.last_name
        }
        try:
            user = User.objects.create_user(form.instance.email, form.instance.password, **extra_fields)
            role = form.data.get('role')
            if not role:
                raise Exception('Role is required')
            clear_roles(user)
            assign_role(user, role)
            messages.success(self.request, "User {} created".format(user.email))
        except Exception as error:
            messages.error(self.request, "Failed on create. Error {}".format(error))
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super(CreateUserView, self).get_context_data(**kwargs)
        context['title'] = 'New User'
        return context


class EditUserView(LoginRequiredMixin, HasPermissionsMixin, UpdateView):
    model = User
    form_class = EditUserForm
    template_name = "create-edit-user.html"
    required_permission = 'update_users'

    def form_valid(self, form):
        user = self.object
        role = form.data.get('role')
        if not role:
            raise Exception('Role is required')
        clear_roles(user)
        if form.data.get('is_active'):
            assign_role(user, role)
        return super(EditUserView, self).form_valid(form)

    def get_success_url(self):
        if settings.IBM_CLIENT:
            """The first time active"""
            # TODO: Check why this is not working when "if" contains "not self.object.last_login"
            # Think is that django rolespermissions modify last_login
            if self.object.is_active:
                try:
                    token_generator = default_token_generator
                    pk_decode = b64encode(str(self.object.pk).encode('ascii'))
                    pk_encode = pk_decode.decode('ascii')
                    context_dict = {
                        "name": "{0}, Your access has been authorized or changed".format(self.object.email),
                        "message": "Enter on the follow link to request your password.",
                        "action_url": "{0}/reset/{1}/{2}".format(settings.SITE_DNS, pk_encode.replace("=", ""),
                                                                 token_generator.make_token(self.object)),
                        "action_text": "Request my Password"
                    }
                    email = EmailMessage(
                        subject='Access Authorized or changed',
                        body=render_to_string("email-template.html", context_dict),
                        to=[self.object.email]
                    )
                    email.content_subtype = "html"
                    email.send()
                except Exception as error:
                    messages.error(self.request, "Attention: {0}".format(error))
        messages.success(self.request, "User Updated!")
        return reverse_lazy("users")

    def get_context_data(self, **kwargs):
        context = super(EditUserView, self).get_context_data(**kwargs)
        context['title'] = 'Edit User'
        return context


class DeleteUserView(LoginRequiredMixin, HasPermissionsMixin, DeleteView):
    model = User
    template_name = "delete-user.html"
    required_permission = 'delete_users'

    def get_success_url(self):
        messages.success(self.request, "User deleted")
        return reverse_lazy('users')


class RequestAccessView(FormView):
    form_class = RequestAccessForm
    template_name = "request-access.html"
    success_url = reverse_lazy('login')

    def form_invalid(self, form):
        if not form.instance.email == "":
            user_check = User.objects.get(email=form.instance.email)
            if user_check:
                if not user_check.is_active:
                    messages.warning(self.request, "Error, User Already exist, you don't be activate yet")
                else:
                    token_generator = default_token_generator
                    pk_decode = b64encode(str(user_check.pk).encode('ascii'))
                    pk_encode = pk_decode.decode('ascii')
                    context_dict = {
                        "name": "{0}, your access has been authorized".format(user_check.email),
                        "message": "Enter on the follow link to request your password.",
                        "action_url": "{0}/reset/{1}/{2}".format(settings.SITE_DNS, pk_encode.replace("=", ""),
                                                                 token_generator.make_token(user_check)),
                        "action_text": "Request my Password"
                    }
                    email = EmailMessage(
                        subject='Access Autorized',
                        body=render_to_string("email-template.html", context_dict),
                        to=[user_check.email]
                    )
                    email.content_subtype = "html"
                    email.send()
                    messages.success(self.request, "You are Activate, We will resend you reset password")
                    return HttpResponseRedirect(self.get_success_url())
        return HttpResponseRedirect(self.get_success_url())

    def form_valid(self, form):
        """Check for exist user on BluePages. If exist, we create a user on system with active=False and
        retrieve from  BP the extra information"""
        if settings.IBM_CLIENT:
            user_ibm = LDAPBackend.check_user(self, form.instance.email)
            if not user_ibm[0]:
                messages.error(self.request, "Failure connect to bluepages")
                return HttpResponseRedirect(reverse_lazy('request-access'))

            if user_ibm[1] is None:
                messages.error(self.request, "Not foud email in Bluepages")
                return HttpResponseRedirect(reverse_lazy('request-access'))

            extra_fields = {
                'is_active': False,
                'first_name': user_ibm[1],
                'last_name': user_ibm[2]
            }
        else:
            extra_fields = {
                'is_active': False
            }
        pwd_generic = User.objects.make_random_password(length=6,
                                                        allowed_chars='#%$!abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789')

        try:
            user = User.objects.create_user(form.instance.email, pwd_generic, **extra_fields)
            context_dict = {
                "name": "Admin",
                "message": "The User {0}, request access for CTA System. "
                           "Click on the next button to activate.".format(user.email),
                "action_url": "{0}/users/{1}".format(settings.SITE_DNS, user.pk),
                "action_text": "Activate User"
            }
            email = EmailMessage(
                subject='Access Request from {}'.format(user.email),
                body=render_to_string("email-template.html", context_dict),
                to=settings.ADMIN_MAIL
            )
            email.content_subtype = "html"
            email.send()
            messages.success(self.request, "Request Sent, Please wait for a email response.")
        except Exception as error:
            messages.error(self.request, "Failed on request access. Error {}".format(error))
            return HttpResponseRedirect(reverse_lazy('request-access'))
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super(RequestAccessView, self).get_context_data(**kwargs)
        return context


class ListTasksView(LoginRequiredMixin, TemplateView):
    template_name = "tasks.html"


class DetailTaskView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = "detail-task.html"
