# MIGRATIONS.md

## Як працює init.sql

- Виконується **тільки один раз** — при першому старті postgres з порожнім volume
- Після цього ніколи не запускається повторно
- Містить повну схему БД (всі `CREATE TABLE`)

## Дані при деплої

| Команда | Що відбувається з даними |
|---|---|
| `docker compose up --build -d` | Дані **зберігаються** (named volume `postgres_data` не чіпається) |
| `docker compose down` | Дані **зберігаються** |
| `docker compose down -v` | Дані **видаляються** — ніколи не виконувати на VPS! |

## Ручні міграції (зміна схеми)

Якщо після першого деплою схема змінилась — запускати вручну після `git pull`:

```bash
# Одна команда
docker compose -f docker-compose.prod.yml exec postgres psql -U rio_user -d rio \
  -c "ALTER TABLE ..."

# Або через файл міграції
docker compose -f docker-compose.prod.yml exec -T postgres psql -U rio_user -d rio \
  < migrations/назва_міграції.sql
```

## Журнал міграцій

| Дата | Файл | Опис | Застосовано на VPS |
|---|---|---|---|
| 2026-03-07 | `migrations/add_photo_to_services.sql` | Додає колонку `photo_url TEXT` до `services` | - |

## Правила

- Нову міграцію зберігати у `migrations/` з префіксом-датою: `2026_03_07_add_photo_url.sql`
- `init.sql` оновлювати разом з міграцією (щоб fresh install також мав актуальну схему)
- Після застосування на VPS — позначати у журналі вище (колонка "Застосовано на VPS")
