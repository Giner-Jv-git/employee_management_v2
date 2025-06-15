from django import forms
from .models import EmployeeData,LeaveRequest
from django.utils import timezone

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


class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason']
        widgets = {
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'min': timezone.now().date().isoformat(),
                'class': 'bg-gradient-to-r from-cyan-50 to-teal-50 border-2 border-teal-200 text-teal-900 rounded-2xl w-full p-4 focus:ring-4 focus:ring-cyan-200 focus:border-cyan-400 outline-none'
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date',
                'min': timezone.now().date().isoformat(),
                'class': 'bg-gradient-to-r from-cyan-50 to-teal-50 border-2 border-teal-200 text-teal-900 rounded-2xl w-full p-4 focus:ring-4 focus:ring-cyan-200 focus:border-cyan-400 outline-none'
            }),
            'leave_type': forms.Select(attrs={
                'class': 'bg-gradient-to-r from-cyan-50 to-teal-50 border-2 border-teal-200 text-teal-900 rounded-2xl w-full p-4 focus:ring-4 focus:ring-cyan-200 focus:border-cyan-400 outline-none'
            }),
            'reason': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Please provide details for your leave request...',
                'class': 'bg-gradient-to-r from-cyan-50 to-teal-50 border-2 border-teal-200 text-teal-900 rounded-2xl w-full p-4 focus:ring-4 focus:ring-cyan-200 focus:border-cyan-400 outline-none'
            })
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise forms.ValidationError("End date must be after start date.")
            if start_date < timezone.now().date():
                raise forms.ValidationError("Start date cannot be in the past.")
        
        return cleaned_data
    
class AdminLeaveAssignForm(forms.ModelForm):
    employee = forms.ModelChoiceField(
        queryset=EmployeeData.objects.filter(status='active'),
        empty_label="Select Employee",
        widget=forms.Select(attrs={
            'class': 'bg-gradient-to-r from-cyan-50 to-teal-50 border-2 border-teal-200 text-teal-900 rounded-2xl w-full p-4 focus:ring-4 focus:ring-cyan-200 focus:border-cyan-400 outline-none'
        })
    )
    
    class Meta:
        model = LeaveRequest
        fields = ['employee', 'leave_type', 'start_date', 'end_date', 'reason', 'comments']
        widgets = {
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'bg-gradient-to-r from-cyan-50 to-teal-50 border-2 border-teal-200 text-teal-900 rounded-2xl w-full p-4 focus:ring-4 focus:ring-cyan-200 focus:border-cyan-400 outline-none'
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'bg-gradient-to-r from-cyan-50 to-teal-50 border-2 border-teal-200 text-teal-900 rounded-2xl w-full p-4 focus:ring-4 focus:ring-cyan-200 focus:border-cyan-400 outline-none'
            }),
            'leave_type': forms.Select(attrs={
                'class': 'bg-gradient-to-r from-cyan-50 to-teal-50 border-2 border-teal-200 text-teal-900 rounded-2xl w-full p-4 focus:ring-4 focus:ring-cyan-200 focus:border-cyan-400 outline-none'
            }),
            'reason': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Reason for leave assignment...',
                'class': 'bg-gradient-to-r from-cyan-50 to-teal-50 border-2 border-teal-200 text-teal-900 rounded-2xl w-full p-4 focus:ring-4 focus:ring-cyan-200 focus:border-cyan-400 outline-none'
            }),
            'comments': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Admin comments (optional)...',
                'class': 'bg-gradient-to-r from-cyan-50 to-teal-50 border-2 border-teal-200 text-teal-900 rounded-2xl w-full p-4 focus:ring-4 focus:ring-cyan-200 focus:border-cyan-400 outline-none'
            })
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise forms.ValidationError("End date must be after start date.")
        
        return cleaned_data