from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Agent


class AgentRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=15)
    location = forms.CharField(max_length=150)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2", "phone_number", "location")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (css + ' form-control').strip()


class EcashAvailabilityForm(forms.ModelForm):
    class Meta:
        model = Agent
        fields = ("ecash_min", "ecash_max")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (css + ' form-control').strip()

    def clean(self):
        cleaned = super().clean()
        ecash_min = cleaned.get('ecash_min')
        ecash_max = cleaned.get('ecash_max')

        if ecash_min is None or ecash_max is None:
            raise forms.ValidationError('Please set both minimum and maximum E-cash limits.')

        if ecash_min < 100 or ecash_max > 10000:
            raise forms.ValidationError('E-cash limits must be within 100 to 10000 GHS.')

        if ecash_min > ecash_max:
            raise forms.ValidationError('Minimum limit cannot be greater than maximum limit.')

        return cleaned


class AgentProfileForm(forms.ModelForm):
    class Meta:
        model = Agent
        fields = ("phone_number", "location", "vendor_number", "business_name")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (css + ' form-control').strip()


class UserDisplayNameForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (css + ' form-control').strip()
