import re
from django import forms
from django.core.exceptions import ValidationError
from store.models import ContactMessage, NewsletterSubscriber, ProductReview
from store.validators import normalize_phone_number


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'phone', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Full Name',
                'required': 'required',
                'maxlength': '120'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'WhatsApp / Phone Number',
                'required': 'required',
                'maxlength': '20'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email Address (Optional)',
                'maxlength': '254'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Subject / Product Inquiry',
                'required': 'required',
                'maxlength': '200'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'How can we help you?',
                'rows': 4,
                'required': 'required',
                'maxlength': '2000'
            }),
        }

    def clean_name(self):
        name = re.sub(r'\s+', ' ', (self.cleaned_data.get('name') or '')).strip()
        if len(name) < 2:
            raise ValidationError("Please enter your full name.")
        return name

    def clean_phone(self):
        return normalize_phone_number(self.cleaned_data.get('phone'))

    def clean_subject(self):
        subj = re.sub(r'\s+', ' ', (self.cleaned_data.get('subject') or '')).strip()
        if len(subj) < 2:
            raise ValidationError("Please enter a subject.")
        return subj

    def clean_message(self):
        msg = (self.cleaned_data.get('message') or '').strip()
        if len(msg) < 5:
            raise ValidationError("Please share at least a brief message (5+ characters).")
        return msg[:2000]


class NewsletterForm(forms.ModelForm):
    class Meta:
        model = NewsletterSubscriber
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your email address',
                'required': 'required'
            })
        }

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        return email


class ProductReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ['customer_name', 'rating', 'review_text']
        widgets = {
            'customer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Name',
                'required': 'required',
                'maxlength': '120'
            }),
            'rating': forms.Select(
                choices=[
                    (5, '★★★★★ (5/5)'),
                    (4, '★★★★☆ (4/5)'),
                    (3, '★★★☆☆ (3/5)'),
                    (2, '★★☆☆☆ (2/5)'),
                    (1, '★☆☆☆☆ (1/5)'),
                ],
                attrs={'class': 'form-select'}
            ),
            'review_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Write your honest review about this product...',
                'required': 'required',
                'maxlength': '1500'
            }),
        }

    def clean_customer_name(self):
        name = re.sub(r'\s+', ' ', (self.cleaned_data.get('customer_name') or '')).strip()
        if len(name) < 2:
            raise ValidationError("Please enter your name.")
        return name

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating is None or not (1 <= int(rating) <= 5):
            raise ValidationError("Rating must be between 1 and 5 stars.")
        return int(rating)

    def clean_review_text(self):
        text = (self.cleaned_data.get('review_text') or '').strip()
        if len(text) < 5:
            raise ValidationError("Review text must be at least 5 characters.")
        return text[:1500]
