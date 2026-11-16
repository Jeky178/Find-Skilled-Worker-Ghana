# Deployment guide

This puts the whole system on one server with HTTPS: PostgreSQL, the API and the website. It uses Docker Compose and Caddy, which obtains and renews HTTPS certificates by itself.

> **Honest note:** the Docker files follow standard, widely used patterns and the settings, migrations and production start-up checks were tested, but I could not run Docker itself in the environment where this was built. Do a first deployment on a cheap test server (or a staging subdomain) before pointing real customers at it.

## What you need

1. **A domain name** (for example `findaskilledworker.com.gh`) and access to its DNS settings.
2. **A server**: a small Linux VPS with 2 GB RAM is enough to start (Ubuntu 22.04 or 24.04). Note its public IP address.
3. **Docker** installed on the server (`curl -fsSL https://get.docker.com | sh`).
4. Later, for payments: a **Paystack** account (see [PAYMENTS.md](PAYMENTS.md)).

## 1. Point your domain at the server

In your domain's DNS settings, add an **A record**: name `www` (and `@` if you want the bare domain), value = your server's IP. Wait until it resolves (check with `ping www.yourdomain.com`). Open ports **80** and **443** in the server's firewall.

## 2. Put the project on the server

Copy the project folder to the server (for example with `git clone` or `scp`), then:

```bash
cd find_skilled_worker
cp .env.production.example .env
nano .env
```

Fill in `.env`:

- `DOMAIN`: your website address, without `https://`.
- `DB_PASSWORD`: a long random password (letters and numbers are safest).
- `SECRET_KEY`: run `python3 -c "import secrets; print(secrets.token_urlsafe(64))"` and paste the result.
- Leave `PAYSTACK_SECRET_KEY` empty for now. Payments stay off until you set it.
- Set your prices, and your contact details if you want them in the footer.

## 3. Start everything

```bash
docker compose up -d --build
docker compose ps                      # all three should be "running"/"healthy"
docker compose logs -f backend         # watch it start; Ctrl+C to leave
```

On start the backend upgrades the database by itself (`alembic upgrade head`), and refuses to run if it cannot. Visit `https://your-domain`. The first visit may take a few seconds while the certificate is issued.

## 4. Create the first administrator and the categories

```bash
docker compose exec backend python seed.py            # creates the 12 service categories (no demo data)
docker compose exec -it backend python create_admin.py
```

Log in with that admin account. Do **not** run `seed.py --demo` on a live site.

## 5. Check it works

- `https://your-domain/api/health/ready` should show `{"status":"ready"}`.
- Register a test customer and artisan, send a request, and walk through the user guide.
- `https://your-domain/docs` should show nothing: the API docs are off in production.

## Updating

```bash
cd find_skilled_worker
git pull                               # or copy the new files over
docker compose up -d --build           # migrations run automatically
```

To undo a bad database change: `docker compose exec backend alembic downgrade -1`, then redeploy the previous version.

## Backups (do this before launch)

Two things hold your data. Back up **both**:

1. **The database:**
   ```bash
   docker compose exec -T db pg_dump -U skilled_user find_skilled_worker | gzip > backup_$(date +%F).sql.gz
   ```
   Schedule it daily with `crontab -e`, and copy the files off the server.
2. **Uploaded files**, including **private ID documents**: the Docker volume `uploads`. For example:
   ```bash
   docker run --rm -v find_skilled_worker_uploads:/data -v $(pwd):/backup alpine tar czf /backup/uploads_$(date +%F).tar.gz -C /data .
   ```
   (The volume name starts with your folder name; check with `docker volume ls`.)

Test restoring a backup at least once. Keep ID-document backups encrypted and private.

To restore the database: `gunzip -c backup.sql.gz | docker compose exec -T db psql -U skilled_user find_skilled_worker` into a fresh database.

## Production settings the app enforces

With `ENVIRONMENT=production` (set by the compose file) the API **refuses to start** if: the database is SQLite, the secret key looks like a placeholder, `CORS_ORIGINS` or `FRONTEND_URL` are not `https://`, or the database has not been migrated. It also switches off `/docs`, adds the HSTS header, and stops creating tables automatically.

## Running without Docker (advanced)

1. Install Python 3.12, PostgreSQL 14+ and Node 20+ on the server.
2. In `backend/`: create a virtual environment, `pip install -r requirements.txt`, create `.env` with `ENVIRONMENT=production` and your real values, then `alembic upgrade head`.
3. Run the API under a process manager such as systemd: `uvicorn main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips='*' --workers 2`.
4. In `frontend/`: `VITE_API_URL= npm run build`, and serve the `dist` folder with Caddy or nginx. Forward `/api/*` and `/uploads/*` to `127.0.0.1:8000`, send every other path to `index.html`, and enable HTTPS (Let's Encrypt).
5. `--forwarded-allow-ips='*'` is only safe when the web server in front is the **only** way to reach the API, so keep port 8000 closed to the internet.

## Scaling notes

- **Rate limits** (login, contact form) are kept in each API process's memory. With more than one server, move them to Redis, or the limits apply per server.
- **Uploads** live on the server's disk. For several servers, switch to S3-compatible storage.
- **Email and SMS** notifications are not built. Add a provider (for example for password reset) before a large launch.
- **Premium expiry** runs every 15 minutes inside the API. You can also run `python jobs.py expire-subscriptions` from a scheduler.

## Go-live checklist

- [ ] Domain works over HTTPS, `/api/health/ready` is ready.
- [ ] Strong `DB_PASSWORD` and `SECRET_KEY`; `.env` is not in version control and is backed up safely.
- [ ] Admin account created with a strong password; demo data **not** loaded.
- [ ] Backups of the database and `uploads` volume run on a schedule and a restore has been tested.
- [ ] Prices set to your real numbers.
- [ ] Contact details filled in, and About and Terms wording reviewed. **Get a Ghana lawyer to review your terms of service and privacy policy**, especially because you store ID documents.
- [ ] If you take payments: tested with Paystack test keys, webhook URL set, then `sk_live_` key added. See [PAYMENTS.md](PAYMENTS.md).
- [ ] You have registered the business and understand your tax obligations for the revenue.
