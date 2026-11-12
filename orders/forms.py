import re
from django import forms
from django.core.exceptions import ValidationError
from orders.models import CustomerAddress
from store.validators import normalize_phone_number


class CheckoutForm(forms.ModelForm):
    # Optional fields for Buy Now direct flow & Idempotency
    product_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    quantity = forms.IntegerField(required=False, min_value=1, max_value=50, initial=1, widget=forms.HiddenInput())
    size = forms.CharField(required=False, max_length=64, widget=forms.HiddenInput())
    colour = forms.CharField(required=False, max_length=64, widget=forms.HiddenInput())
    order_source = forms.CharField(required=False, max_length=20, initial='CART', widget=forms.HiddenInput())
    checkout_token = forms.CharField(required=False, max_length=64, widget=forms.HiddenInput())

    class Meta:
        model = CustomerAddress
        fields = [
            'full_name',
            'mobile_number',
            'house_name_number',
            'street_location',
            'city',
            'district',
            'state',
            'pin_code',
            'delivery_instructions',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your full name',
                'required': 'required',
                'autocomplete': 'name',
            }),
            'mobile_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '10-digit WhatsApp mobile number',
                'required': 'required',
                'pattern': r'^(?:\+91[\-\s]?)?[6-9][0-9]{9}$',
                'title': 'Please enter a valid 10-digit Indian WhatsApp mobile number',
                'autocomplete': 'tel',
            }),
            'house_name_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'House Name / Villa No. / Flat No. / Building',
                'required': 'required',
                'autocomplete': 'address-line1',
            }),
            'street_location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Street, Area, Landmark',
                'required': 'required',
                'autocomplete': 'address-line2',
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City / Town',
                'required': 'required',
                'autocomplete': 'address-level2',
            }),
            'district': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'District',
                'required': 'required',
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'State',
                'value': 'Kerala',
                'required': 'required',
                'autocomplete': 'address-level1',
            }),
            'pin_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '6-digit PIN Code',
                'required': 'required',
                'pattern': r'^[1-9][0-9]{5}$',
                'title': 'Please enter a valid 6-digit Indian postal PIN code',
                'autocomplete': 'postal-code',
            }),
            'delivery_instructions': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Call before delivery, landmark near temple/church/school',
                'rows': 2,
                'maxlength': '500',
            }),
        }

    def _clean_text(self, field_name, min_len=2):
        val = re.sub(r'\s+', ' ', (self.cleaned_data.get(field_name) or '')).strip()
        if len(val) < min_len:
            raise ValidationError(f"Please enter at least {min_len} characters.")
        return val

    def clean_full_name(self):
        return self._clean_text('full_name', 2)

    def clean_mobile_number(self):
        return normalize_phone_number(self.cleaned_data.get('mobile_number'))

    def clean_house_name_number(self):
        return self._clean_text('house_name_number', 2)

    def clean_street_location(self):
        return self._clean_text('street_location', 3)

    def clean_city(self):
        return self._clean_text('city', 2)

    def clean_district(self):
        return self._clean_text('district', 2)

    def clean_state(self):
        return self._clean_text('state', 2)

    def clean_pin_code(self):
        pin = re.sub(r'\s+', '', (self.cleaned_data.get('pin_code') or ''))
        if not re.match(r'^[1-9][0-9]{5}$', pin):
            raise ValidationError("Please enter a valid 6-digit Indian PIN code (cannot start with 0).")
        return pin

    def clean_delivery_instructions(self):
        notes = (self.cleaned_data.get('delivery_instructions') or '').strip()
        return notes[:500]
