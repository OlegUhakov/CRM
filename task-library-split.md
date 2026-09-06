# Задание: разделить Library на 3 отдельных Django-приложения

## Контекст

Сейчас в CRM есть раздел **Library**, где страница "All Documents" смешивает статьи и файлы через переключатель **Articles / Files / All**. Это неудобно — нужно разделить на независимые разделы.

Также в сайдбаре уже существуют пункты **Photo Gallery** и **Files Catalog** — они частично дублируют функционал и должны быть объединены с новой структурой.

## Цель

Разбить единый раздел Library на 3 отдельных Django-приложения без общего переключателя-табов:

1. **library_articles** — статьи (бывший "All Documents" в режиме Articles)
2. **library_gallery** — фотогалерея (объединить с текущим Photo Gallery)
3. **library_files** — файлы (объединить с текущим Files Catalog)

Каждое приложение — самостоятельный раздел со своей страницей, без переключателя между типами контента.

## Структура приложений

```
library_articles/
    models.py       # Article, Category (если категории нужны только статьям)
    views.py        # ArticleListView, ArticleDetailView, ArticleCreateView, ArticleUpdateView
    urls.py         # префикс /library/articles/
    templates/library_articles/
        list.html   # страница списка со своей верхней панелью

library_gallery/
    models.py       # Photo, Album (перенести данные из текущего Photo Gallery)
    views.py        # GalleryListView, PhotoDetailView, PhotoUploadView
    urls.py         # префикс /library/gallery/
    templates/library_gallery/
        list.html

library_files/
    models.py       # FileDocument (перенести данные из текущего Files Catalog)
    views.py        # FileListView, FileDetailView, FileUploadView
    urls.py         # префикс /library/files/
    templates/library_files/
        list.html
```

Если Category/Type-фильтры общие для нескольких приложений — вынести общие модели/миксины в `library_core` (без флексибельности сверх необходимого, минимум boilerplate).

## Требования к каждой странице (верхняя панель)

Каждая страница получает свою верхнюю панель вместо общего таб-переключателя:

- **library_articles page**: заголовок "Articles", кнопка "New Article", строка поиска, фильтры Category / Type / Date / Favorites, переключатель list/grid
- **library_gallery page**: заголовок "Gallery", кнопка "Upload Photo", фильтры по альбому / дате, переключатель list/grid
- **library_files page**: заголовок "Files", кнопка "Upload File", фильтры по типу файла / дате, переключатель list/grid

Убрать полностью: сегмент-контрол "Articles / Files / All" и общую страницу "All Documents".

## Роутинг

В корневом `urls.py` проекта:

```python
path('library/articles/', include('library_articles.urls')),
path('library/gallery/', include('library_gallery.urls')),
path('library/files/', include('library_files.urls')),
```

## Сайдбар

Убрать текущий пункт "Library" и связанные с ним "All Documents", "New Document", "Photo Gallery", "Files Catalog". Добавить три новых пункта верхнего уровня:

- **Articles** → /library/articles/
- **Gallery** → /library/gallery/
- **Files** → /library/files/

## Миграция данных

- Если у текущего Photo Gallery и Files Catalog уже есть модели с данными — написать миграции для переноса данных в новые модели `library_gallery.Photo` и `library_files.FileDocument` (или переиспользовать существующие модели, просто переместив их в новые apps, если структура не меняется).
- Существующие статьи из "All Documents" (режим Articles) перенести в `library_articles.Article`.

## Ограничения

- Минимум boilerplate, простая архитектура — не переусложнять генерик-вьюхами там, где хватит прямого CRUD.
- Не менять стек: Django 6.0.7 + Tailwind CSS 4 + Alpine.js + HTMX.
- Существующий функционал поиска (DuckDuckGo, анонимный) в library_articles не трогать.
