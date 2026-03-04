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
