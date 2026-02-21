from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm


User = get_user_model()


class CreateAdminUserForm(UserCreationForm):
    email = forms.EmailField(required=False)
    first_name = forms.CharField(required=False, max_length=150)
    last_name = forms.CharField(required=False, max_length=150)
    make_superuser = forms.BooleanField(required=False, initial=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name", "password1", "password2", "make_superuser")

    def __init__(self, *args, allow_make_superuser: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        if not allow_make_superuser:
            self.fields.pop('make_superuser', None)
        for _name, field in self.fields.items():
            css = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (css + ' form-control').strip()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data.get('email', '')
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.is_staff = True
        if 'make_superuser' in self.cleaned_data and self.cleaned_data.get('make_superuser'):
            user.is_superuser = True
        if commit:
            user.save()
        return user
