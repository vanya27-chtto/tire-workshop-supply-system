#!/bin/bash
# Скрипт для обновления паролей учетных записей пользователей Django
# Тестовые данные со страницы логин:
# - Администратор: admin / admin123
# - Товаровед: merchandiser_user / password123
# - Сотрудник цеха: workshop_user / password123

cd /workspace

python manage.py shell << 'EOF'
from django.contrib.auth import get_user_model

User = get_user_model()

# Данные пользователей из тестовых данных на странице логин
users_data = [
    {'username': 'admin', 'password': 'admin123'},
    {'username': 'merchandiser_user', 'password': 'password123'},
    {'username': 'workshop_user', 'password': 'password123'},
]

for user_data in users_data:
    try:
        user = User.objects.get(username=user_data['username'])
        user.set_password(user_data['password'])
        user.save()
        print(f"Пароль для пользователя '{user_data['username']}' успешно изменен на '{user_data['password']}'")
    except User.DoesNotExist:
        print(f"Пользователь '{user_data['username']}' не найден!")

print("\nВсе пароли успешно обновлены!")
EOF
