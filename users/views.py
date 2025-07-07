from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm # Formulario de creación de usuario de Django
from django.contrib import messages # Para mostrar mensajes

def register(request):
    """
    Vista para el registro de nuevos usuarios.
    """
    if request.method == 'POST':
        form = UserCreationForm(request.POST) # Crea una instancia del formulario con los datos enviados
        if form.is_valid(): # Valida los datos
            form.save() # Guarda el nuevo usuario en la base de datos
            username = form.cleaned_data.get('username')
            messages.success(request, f'¡Cuenta creada para {username}! Ahora puedes iniciar sesión.')
            return redirect('login') # Redirige a la página de inicio de sesión
    else:
        form = UserCreationForm() # Si es una solicitud GET, muestra un formulario vacío
    return render(request, 'registration/register.html', {'form': form})
