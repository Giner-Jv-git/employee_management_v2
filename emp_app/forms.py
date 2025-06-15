from django import forms
from .models import EmployeeData

class EmployeeForm(forms.ModelForm):
    username = forms.CharField(max_length=150, help_text="Username for employee login")
    password = forms.CharField(
        widget=forms.PasswordInput, 
        help_text="Password for employee (min 8 characters)",
        min_length=8
    )

    class Meta:
        model = EmployeeData
        fields = ['name', 'profile_picture', 'employee_id', 'phone_number', 
                 'age', 'salary', 'address', 'status', 'position']
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'placeholder': '09XXXXXXXXX',
                'pattern': '09\d{9}',
                'title': '11 digits starting with 09'
            }),
            'age': forms.NumberInput(attrs={'min': 18}),
            'salary': forms.NumberInput(attrs={'step': '0.01'}),
            'address': forms.Textarea(attrs={'rows': 3}),
            'profile_picture': forms.FileInput(attrs={
                'accept': 'image/*',
                'class': 'hidden'
            })
        }


class EditEmployeeForm(forms.ModelForm):
    class Meta:
        model = EmployeeData
        fields = ['name', 'profile_picture', 'employee_id', 'phone_number', 
                 'age', 'salary', 'address', 'status', 'position']
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'placeholder': '09XXXXXXXXX',
                'pattern': '09\d{9}',
                'title': '11 digits starting with 09'
            }),
            'age': forms.NumberInput(attrs={'min': 18}),
            'salary': forms.NumberInput(attrs={'step': '0.01'}),
            'address': forms.Textarea(attrs={'rows': 3}),
            'profile_picture': forms.FileInput(attrs={
                'accept': 'image/*',
                'class': 'hidden'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make profile picture optional for editing
        self.fields['profile_picture'].required = False