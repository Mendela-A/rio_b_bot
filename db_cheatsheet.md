# Шпаргалка: додавання даних до БД

pgAdmin → Tools → Query Tool

---

## Категорії (довідник)

| id | name | type |
|----|------|------|
| 1 | Додаткові послуги | venue |
| 2 | Аніматор на виїзд | offsite |
| 3 | Програми та аніматори | program |

---

## Послуги

### Проста послуга
```sql
INSERT INTO services (category_id, name, price, description, is_active, sort_order)
VALUES (1, 'Назва послуги', 500, 'Опис послуги', true, 1);
```

### Послуга з підкатегоріями (батько + діти одним запитом)
```sql
WITH parent AS (
    INSERT INTO services (category_id, name, price, description, is_active, sort_order)
    VALUES (3, 'Назва батька', 1300, 'Опис батька', true, 1)
    RETURNING id
)
INSERT INTO services (category_id, name, price, description, is_active, sort_order, parent_id)
SELECT 3, name, 1300, 'Опис дитини', true, sort_order, parent.id
FROM parent, (VALUES
    ('Варіант 1', 1),
    ('Варіант 2', 2),
    ('Варіант 3', 3)
) AS children(name, sort_order);
```

### Додати дитину до існуючого батька
```sql
-- Спочатку дізнатись id батька
SELECT id, name FROM services WHERE name = 'Назва батька';

-- Додати дитину
INSERT INTO services (category_id, name, price, description, is_active, sort_order, parent_id)
VALUES (3, 'Новий варіант', 1300, 'Опис', true, 4, [ID_БАТЬКА]);
```

### Редагувати послугу
```sql
UPDATE services SET price = 1500, description = 'Новий опис' WHERE id = 10;
```

### Приховати послугу (не видаляти)
```sql
UPDATE services SET is_active = false WHERE id = 10;
```

### Видалити послугу
```sql
DELETE FROM services WHERE id = 10;
-- Увага: видалення батька видалить і всіх дітей (CASCADE)
```

---

## Інформація про заклад

### Додати сторінку
```sql
INSERT INTO info_pages (title, content, sort_order)
VALUES ('Заголовок', 'Текст сторінки', 5);
```

### Редагувати сторінку
```sql
UPDATE info_pages SET content = 'Новий текст' WHERE title = 'Заголовок';
```

### Видалити сторінку
```sql
DELETE FROM info_pages WHERE id = 3;
```

---

## Перегляд даних

```sql
-- Всі категорії
SELECT * FROM categories;

-- Всі активні послуги
SELECT * FROM services WHERE is_active = true ORDER BY category_id, sort_order;

-- Послуги з підкатегоріями
SELECT p.name as батько, c.name as дитина, c.price
FROM services p
JOIN services c ON c.parent_id = p.id
ORDER BY p.name, c.sort_order;

-- Всі сторінки інфо
SELECT * FROM info_pages ORDER BY sort_order;
```

---

## Корисні поля

| Поле | Тип | Опис |
|------|-----|------|
| `category_id` | int | 1=venue, 2=offsite, 3=program |
| `parent_id` | int | NULL = звичайна, число = підкатегорія |
| `is_active` | bool | true = видно, false = приховано |
| `sort_order` | int | порядок відображення (менше = вище) |
