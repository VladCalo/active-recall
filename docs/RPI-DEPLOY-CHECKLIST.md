# RPi5 deploy checklist – make sure it works

Run these on the Pi (SSH or local). Paths assume `update-rpi.sh` layout: app in `/mnt/ssd/github/active-recall`, env in `/mnt/ssd/apps/active-recall/data/.env`.

---

## 1. Create env dir and .env (first time only)

```bash
sudo mkdir -p /mnt/ssd/apps/active-recall/data
sudo chown "$USER:$USER" /mnt/ssd/apps/active-recall/data
```

Create `/mnt/ssd/apps/active-recall/data/.env` with at least:

```bash
# Required – generate with: python3 -c "import secrets; print(secrets.token_urlsafe(64))"
JWT_SECRET_KEY=<paste-64-char-secret>
CSRF_SECRET_KEY=<paste-32-char-secret>

# Admin – either allow defaults (quick) or set your own
ADMIN_ALLOW_DEFAULT=true
# Or: ADMIN_EMAIL=youradmin  and  ADMIN_PASSWORD=your-secure-password

# If you access the app by IP (e.g. http://192.168.1.50), set CORS so login works:
# CORS_ORIGINS=["http://rpi5.local","http://192.168.1.50"]
# Default in prod is ["http://rpi5.local","http://rpi5"].
```

Generate secrets on the Pi:

```bash
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(64))"
python3 -c "import secrets; print('CSRF_SECRET_KEY=' + secrets.token_urlsafe(32))"
```

---

## 2. Update app and start

From your repo (e.g. after `git pull` on your machine and push, then on Pi):

```bash
cd /mnt/ssd/github/active-recall
./update-rpi.sh
```

Or manually:

```bash
cd /mnt/ssd/github/active-recall
export ENV_FILE="/mnt/ssd/apps/active-recall/data/.env"

git pull
cp docker-compose.prod.yml docker-compose.yml
docker compose --env-file "$ENV_FILE" down
docker compose --env-file "$ENV_FILE" build --no-cache
docker compose --env-file "$ENV_FILE" up -d
```

---

## 3. Verify 100%

**a) Containers running (all “healthy” or “running”)**

```bash
docker compose --env-file /mnt/ssd/apps/active-recall/data/.env ps
```

You want: `redis` healthy, `backend` healthy, `frontend` running.

**b) Backend logs – no crash**

```bash
docker compose --env-file /mnt/ssd/apps/active-recall/data/.env logs backend --tail 50
```

- Good: lines like `application_startup`, `migrations_complete`, `admin_user_seeded` or `admin_user_exists`.
- Bad: `SECURITY ERROR: Default admin credentials` or any traceback → fix `.env` (step 1) and restart.

**c) Backend health**

```bash
curl -s http://localhost:7070/api/health
```

Expected: `{"ok":true}`

**d) Frontend**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:80
```

Expected: `200`

**e) Login**

Open in browser: `http://<rpi-ip>` or `http://rpi5.local`.  
Log in with your admin user (or `adminvladcalo` / `Adminvladcalo123!` if you set `ADMIN_ALLOW_DEFAULT=true`).

---

## 4. If backend stays unhealthy

1. Check logs: `docker compose --env-file /mnt/ssd/apps/active-recall/data/.env logs backend`
2. If you see “Default admin credentials” → add `ADMIN_ALLOW_DEFAULT=true` (or set `ADMIN_EMAIL` / `ADMIN_PASSWORD`) in `/mnt/ssd/apps/active-recall/data/.env`, then:
   ```bash
   docker compose --env-file /mnt/ssd/apps/active-recall/data/.env up -d
   ```
3. If you see DB/volume errors → ensure `/mnt/ssd/apps/active-recall/data/db` exists and is writable:
   ```bash
   mkdir -p /mnt/ssd/apps/active-recall/data/db
   chown -R 1000:1000 /mnt/ssd/apps/active-recall/data
   ```
4. **"An unexpected error occurred" on login** – backend is returning 500. After trying to log in, run:
   ```bash
   docker compose --env-file "$ENV_FILE" logs backend --tail 100
   ```
   Look for `unhandled_exception` and the `traceback` line to see the real error (e.g. missing column, JWT issue).
5. **Bad migration state** (repeated "Running upgrade -> 001" in logs) – pull latest code (stamp + resilient startup), rebuild, restart. If it still loops, reset DB (deletes all data):
   ```bash
   docker compose --env-file "$ENV_FILE" down
   rm -f /mnt/ssd/apps/active-recall/data/db/active-recall.db
   docker compose --env-file "$ENV_FILE" up -d
   ```

---

## Quick one-liner (after .env is set)

```bash
cd /mnt/ssd/github/active-recall && ./update-rpi.sh && sleep 5 && docker compose --env-file /mnt/ssd/apps/active-recall/data/.env logs backend --tail 20 && curl -s http://localhost:7070/api/health && echo "" && curl -s -o /dev/null -w "Frontend HTTP %{http_code}\n" http://localhost:80
```

If that shows `{"ok":true}` and `Frontend HTTP 200`, you’re good.
