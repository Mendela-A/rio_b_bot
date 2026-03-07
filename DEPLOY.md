# Деплой на VPS (Ubuntu/Debian)

## 1. Підготовка сервера

```bash
# Оновлення системи
apt update && apt upgrade -y

# Встановлення Docker
curl -fsSL https://get.docker.com | sh

# Додати свого юзера в групу docker (опційно, якщо не root)
usermod -aG docker $USER

# Перевірити
docker --version
docker compose version
```

## 2. Firewall

```bash
ufw allow 22/tcp        # SSH
ufw deny 8080/tcp       # Закрити admin назовні (тільки через тунель)
ufw enable
ufw status
```

## 3. Клонування проєкту

```bash
git clone https://github.com/YOUR_REPO/rio_b_bot.git
cd rio_b_bot
```

## 4. Налаштування .env

```bash
cp .env.example .env
nano .env
```

Заповнити:
- `BOT_TOKEN` — взяти з @BotFather
- `ADMIN_CHAT_ID` — ID чату для нотифікацій
- `DB_PASSWORD` — придумати надійний пароль
- `ADMIN_PASSWORD` — пароль для веб-панелі
- `ADMIN_SECRET_KEY` — згенерувати: `openssl rand -hex 32`

## 5. Запуск

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f
```

## 6. Перевірка

```bash
docker compose -f docker-compose.prod.yml ps
# Всі контейнери мають бути: Up (healthy) або Up
```

## 7. Cloudflare Tunnel (доступ до адмін-панелі)

### Встановлення cloudflared

```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb
dpkg -i cloudflared.deb
```

### Авторизація та створення тунелю

```bash
cloudflared tunnel login
cloudflared tunnel create rio-admin
```

### Конфіг тунелю `~/.cloudflared/config.yml`

```yaml
tunnel: <TUNNEL_ID>
credentials-file: /root/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: admin.your-domain.com
    service: http://localhost:8080
  - service: http_status:404
```

### DNS (в Cloudflare dashboard)

Додати CNAME запис:
- Name: `admin`
- Target: `<TUNNEL_ID>.cfargotunnel.com`

### Запуск як systemd service

```bash
cloudflared service install
systemctl enable cloudflared
systemctl start cloudflared
systemctl status cloudflared
```

Після цього адмін-панель доступна на `https://admin.your-domain.com/admin` з SSL від Cloudflare.

## 8. Оновлення (після змін у коді)

```bash
cd rio_b_bot
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

## 9. Відновлення з резервної копії

Завантажте ZIP через адмін-панель ("Експорт БД + фото"), потім:

### Відновлення БД

```bash
# Розпакувати SQL з архіву
unzip rio_YYYYMMDD_HHMMSS.zip "*.sql" -d /tmp/rio_restore/

# Очистити та відновити БД
docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U rio_user -d rio -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U rio_user -d rio < /tmp/rio_restore/rio_YYYYMMDD_HHMMSS.sql
```

### Відновлення фото

```bash
# Розпакувати папку uploads
unzip rio_YYYYMMDD_HHMMSS.zip "uploads/*" -d /tmp/rio_restore/

# Скопіювати у контейнер
docker compose -f docker-compose.prod.yml cp /tmp/rio_restore/uploads/. admin:/app/uploads/
```

Після відновлення перезапустити сервіси:

```bash
docker compose -f docker-compose.prod.yml restart bot admin
```

## 10. Webhook (prod)

Polling — простіше для розробки, але для VPS рекомендовано webhook: Telegram сам надсилає оновлення, менше навантаження.

### Налаштування Cloudflare Tunnel

Додати другий ingress у `~/.cloudflared/config.yml`:

```yaml
ingress:
  - hostname: admin.your-domain.com
    service: http://localhost:8080
  - hostname: bot.your-domain.com
    service: http://localhost:8081
  - service: http_status:404
```

DNS: додати CNAME `bot` → `<TUNNEL_ID>.cfargotunnel.com`

Перезапустити тунель:
```bash
systemctl restart cloudflared
```

### Змінні у `.env`

```env
WEBHOOK_URL=https://bot.your-domain.com
WEBHOOK_SECRET=   # openssl rand -hex 32
```

Перезапустити бота:
```bash
docker compose -f docker-compose.prod.yml up -d --build bot
```

Перевірити реєстрацію:
```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
```

## Корисні команди

```bash
# Логи бота
docker compose -f docker-compose.prod.yml logs -f bot

# Логи адмінки
docker compose -f docker-compose.prod.yml logs -f admin

# Підключитися до БД
docker compose -f docker-compose.prod.yml exec postgres psql -U rio_user -d rio

# Перезапустити один контейнер
docker compose -f docker-compose.prod.yml restart bot
```
