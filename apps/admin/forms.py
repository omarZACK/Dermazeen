from django import forms
from apps.accounts.models import User

class AdminProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'phone',
            'birth_date',
            'gender',
            'profile_image',
        ]
