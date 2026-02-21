from django import forms

from .models import FloatRequest


class FloatRequestCreateForm(forms.ModelForm):
    class Meta:
        model = FloatRequest
        fields = ("request_type", "amount", "requester_latitude", "requester_longitude")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['requester_latitude'].required = False
        self.fields['requester_longitude'].required = False
        self.fields['requester_latitude'].widget = forms.HiddenInput()
        self.fields['requester_longitude'].widget = forms.HiddenInput()

        for name, field in self.fields.items():
            css = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (css + ' form-control').strip()
