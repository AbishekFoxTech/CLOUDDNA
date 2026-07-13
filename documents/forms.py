import os

from django import forms

from .models import Document


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['title', 'description', 'category', 'tags', 'file']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Document title',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3, 'placeholder': 'Optional description',
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'tags': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. invoice, 2026, client-a',
            }),
            'file': forms.ClearableFileInput(attrs={
                'class': 'form-control d-none', 'id': 'id_file',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].required = False

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('title'):
            uploaded_file = cleaned_data.get('file')
            if uploaded_file:
                cleaned_data['title'] = os.path.splitext(uploaded_file.name)[0]
        return cleaned_data


class DocumentRenameForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'autofocus': True}),
        }
