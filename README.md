# Описание

Веб-приложение Foodgram https://myfoodgram.sytes.net/ представляет собой проект со следующими функциями:

* Регистрация пользователей (вход по email и возможность изменить пароль);
* Размещение рецептов, их изменение, удаление и просмотр рецептов других юзеров;
* Аутентифицированным пользователям доступна возможность подписки на авторов, опция добавления рецептов
в избранное и в список покупок (для дальнейшего получения списка с ингредиентами понравившихся рецептов);
* Рецепты возможно отсортировать по тегам.
(Находясь в папке infra, выполните команду docker-compose up, чтобы узнать весь список возможных API запросов. По адресу http://localhost/api/docs/ будет доступна спецификация API.)

## Установка
Клонировать репозиторий и перейти в него в командной строке:
git clone https://github.com/DaryaBazalitskaya/foodgram.git
cd foodgram

## Запуск проекта
Cоздать файлы .env по аналогии с файлами .env.example в корневой папке и директории ./backend/foodgram_backend.

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

Перенести данные с ингредиентами и csv-файла в БД:
docker compose exec backend python manage.py csv_import

После выполненных манипуляций при обращении к адресам http://localhost:8000/ и http://localhost:8000/admin/ должны отобразиться главная страница веб-приложения и админка Foodgram соответственно.