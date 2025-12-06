"""Forms for the inventory app."""
from django import forms
from django.contrib.auth.models import User
from .models import SparePart, Supplier


class SparePartForm(forms.ModelForm):
    """Form for creating and editing spare parts."""
    # pylint: disable=too-few-public-methods

    class Meta:
        """Metadata for SparePartForm."""
        model = SparePart
        fields = [
            "part_number",
            "part_name",
            "category",
            "quantity",
            "price",
            "minimum_stock",
        ]
        widgets = {
            "part_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Part Number",
                },
            ),
            "part_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Part Name",
                },
            ),
            "category": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Category",
                },
            ),
            "quantity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Quantity",
                },
            ),
            "price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Price",
                },
            ),
            "minimum_stock": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Minimum Stock",
                },
            ),
        }


class SupplierForm(forms.ModelForm):
    """Form for creating and editing suppliers."""
    # pylint: disable=too-few-public-methods

    class Meta:
        """Metadata for SupplierForm."""
        model = Supplier
        fields = ["name", "email", "phone", "address"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Supplier Name"},
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "Email (optional)"},
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Phone (optional)"},
            ),
            "address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Address",
                },
            ),
        }


class EmployeeForm(forms.Form):
    """Form for creating a new employee user with validation."""

    username = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Username",
            },
        ),
    )
    first_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "First Name",
            },
        ),
    )
    last_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Last Name",
            },
        ),
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Email ID",
            },
        ),
    )
    mobile_number = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Mobile Number",
            },
        ),
    )

    def clean_username(self):
        """Ensure username is unique."""
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(
                "Username already exists. Please choose a different username.",
            )
        return username

    def clean_email(self):
        """Ensure email is unique."""
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "Email already exists. Please use a different email.",
            )
        return email
