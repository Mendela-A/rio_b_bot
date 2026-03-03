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

## ✏️ Шаблони — скопіюй і заміни значення

### Проста послуга (без варіантів тем)

```sql
INSERT INTO services (category_id, name, price, description, is_active, sort_order)
VALUES (
    3,          -- категорія: 1=venue, 2=offsite, 3=program
    'НАЗВА',    -- ← назва послуги
    1000,       -- ← ціна (грн)
    'ОПИС',     -- ← опис для клієнта
    true,
    10          -- ← порядок (менше = вище в списку)
);
```

### Послуга з варіантами тем (батько + теми)

```sql
WITH parent AS (
    INSERT INTO services (category_id, name, price, description, is_active, sort_order)
    VALUES (
        3,          -- категорія
        'НАЗВА',    -- ← назва послуги
        1000,       -- ← ціна
        'ОПИС',     -- ← опис
        true,
        10          -- ← порядок
    )
    RETURNING id
)
INSERT INTO services (category_id, name, price, description, is_active, sort_order, parent_id)
SELECT 3, name, 1000, 'ОПИС', true, sort_order, parent.id
FROM parent, (VALUES
    ('Тема 1', 1),  -- ← замінюй теми
    ('Тема 2', 2),
    ('Тема 3', 3)
) AS children(name, sort_order);
```

---

## Інші операції

### Переглянути поточний список послуг (з порядком)

```sql
SELECT id, name, price, sort_order, parent_id
FROM services
WHERE category_id = 3 AND is_active = true
ORDER BY sort_order;
```

### Редагувати послугу

```sql
UPDATE services
SET price = 1500, description = 'Новий опис'
WHERE id = 10;  -- ← id з запиту вище
```

### Приховати послугу (не видаляти)

```sql
UPDATE services SET is_active = false WHERE id = 10;
```

### Видалити послугу

```sql
DELETE FROM services WHERE id = 10;
-- Увага: видалення батька видалить і всі теми (CASCADE)
```

---

## Інформаційні сторінки

### Додати сторінку

```sql
INSERT INTO info_pages (title, content, sort_order)
VALUES (
    'ЗАГОЛОВОК',  -- ← назва
    'ТЕКСТ',      -- ← вміст
    5             -- ← порядок
);
```

### Редагувати сторінку

```sql
UPDATE info_pages SET content = 'Новий текст' WHERE title = 'ЗАГОЛОВОК';
```
