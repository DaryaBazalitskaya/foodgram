# Описание
Веб-приложение Foodgram https://myfoodgram.sytes.net/ представляет собой проект со следующими функциями:

* Регистрация пользователей (вход по email и возможность изменить пароль);
* Размещение рецептов, их изменение, удаление и просмотр рецептов других юзеров;
* Аутентифицированным пользователям доступна возможность подписки на авторов, опция добавления рецептов
в избранное и в список покупок (для дальнейшего получения списка с ингредиентами понравившихся рецептов);
* Рецепты возможно отсортировать по тегам.

## Инструменты
* Python
* Django
* Django REST Framework
* Docker
* Nginx

## Установка
Клонировать репозиторий и перейти в него в командной строке:
git clone https://github.com/DaryaBazalitskaya/foodgram.git
cd foodgram

## Запуск проекта и перенос данных
Cоздать файлы .env по аналогии с файлом .env.example в корневой папке и директории ./backend/foodgram_backend.

Используя Docker, выполнить следующие команды:
Запустить Docker Compose:
docker compose up

В новом терминале выполнить миграции:
docker compose exec backend python manage.py migrate

Cобрать статику и копировать статику в volume:
docker compose exec backend python manage.py collectstatic
docker compose exec backend cp -r /app/collected_static/. /backend_static/static/

Создать суперпользователя:
docker compose exec backend python manage.py createsuperuser

Перенести данные с ингредиентами из csv-файла в БД:
docker compose exec backend python manage.py csv_import

После выполненных манипуляций при обращении к адресам http://localhost:8000/ и http://localhost:8000/admin/ должны отобразиться главная страница веб-приложения и админка Foodgram соответственно.

## Примеры запросов и ответов
Находясь в папке infra, выполните команду docker compose up, чтобы узнать весь список возможных API запросов. По адресу http://localhost/api/docs/ будет доступна спецификация API.

Варианты некоторых возможных запросов и ответы:
1. Создать пользователя:
POST-запрос на эндпоинт http://127.0.0.1:8000/api/users/
{
    "username": "vasya.ivanov",
    "first_name": "Вася",
    "last_name": "Иванов",
    "email": "vivanov@yandex.ru",
    "id": 484
}
Ответ:
{
    "email": "vivanov@yandex.ru",
    "username": "vasya.ivanov",
    "first_name": "Вася",
    "last_name": "Иванов",
    "password": "MySecretPas$word"
}

2. Получить токен:
GET-запрос на эндпоинт http://127.0.0.1:8000/api/auth/token/login/
{
    "email": "vivanov@yandex.ru",
    "password": "MySecretPas$word"
}
Ответ:
{
    "auth_token": "ece4b19d0a80718aaa7c83e38740dad7bc3234a3"
}

3. Создать рецепт:
Post-запрос на эндпоинт http://127.0.0.1:8000/api/recipes/
{
    "ingredients": [
        {
            "id": 170,
            "amount": 10
        },
        {
            "id": 1195,
            "amount": 20
        }
    ],
    "tags": [
        1,
        2
    ],
    "image": "data:image/png;base64,iVBORw0KG...ggg==",
    "name": "Нечто съедобное (это не точно)",
    "text": "Приготовьте как-нибудь эти ингредиеты",
    "cooking_time": 5
}
Ответ:
{
    "id": 129,
    "author": {
        "id": 485,
        "email": "second_user@email.org",
        "username": "second-user",
        "first_name": "Андрей",
        "last_name": "Макаревский",
        "is_subscribed": false,
        "avatar": null
    },
    "name": "Нечто съедобное (это не точно)",
    "image": "https://myfoodgram.sytes.net/media/recipes/images/temp_01T4vy0.png",
    "text": "Приготовьте как нибудь эти ингредиеты",
    "ingredients": [
        {
            "id": 170,
            "name": "Буррата",
            "measurement_unit": "г",
            "amount": 10
        },
        {
            "id": 1195,
            "name": "Панифарин",
            "measurement_unit": "г",
            "amount": 20
        }
    ],
    "tags": [
        {
            "id": 1,
            "name": "Завтрак",
            "slug": "breakfast"
        },
        {
            "id": 2,
            "name": "Обед",
            "slug": "dinner"
        }
    ],
    "cooking_time": 5,
    "is_favorited": false,
    "is_in_shopping_cart": false
}

4. Добавить подписку:
POST-запрос на эндпоинт http://127.0.0.1:8000/api/users/{id}/subscribe/
Пример ответа:
{
    "id": 486,
    "email": "third-user@user.ru",
    "username": "third-user-username",
    "first_name": "Гордон",
    "last_name": "Рамзиков",
    "is_subscribed": true,
    "avatar": null,
    "recipes": [],
    "recipes_count": 0
}

## Ссылка на проект
https://myfoodgram.sytes.net/

## Автор
Базалицкая Дарья (https://github.com/DaryaBazalitskaya)