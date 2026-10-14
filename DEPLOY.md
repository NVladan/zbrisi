# Deploying zbriši on a Contabo VPS + Namecheap domain

This is the full path from a fresh Contabo VPS to a live, HTTPS `zbrisi.com`.
Stack: **gunicorn** (runs the app) → **nginx** (reverse proxy + TLS) →
**systemd** (keeps it alive) → **Let's Encrypt** (free HTTPS).

Replace `YOUR_SERVER_IP` and the `zbrisi` username/paths with your own.
Config files referenced here live in `deploy/`.

---

## 1. Point the domain at the server (Namecheap)

In Namecheap → **Domain List → Manage → Advanced DNS**:

| Type | Host | Value | TTL |
|------|------|-------|-----|
| A Record | `@` | `YOUR_SERVER_IP` | Automatic |
| A Record | `www` | `YOUR_SERVER_IP` | Automatic |

Delete any default **parking / URL-redirect** records Namecheap added. DNS can
take a few minutes to a couple of hours to propagate. Check with
`ping zbrisi.com` (should resolve to your IP) before running certbot in step 7.

## 2. Log in and create a user (on the Contabo VPS)

```bash
ssh root@YOUR_SERVER_IP                 # Contabo emails you the root password
adduser vladan                          # create a user (prompts for a password)
usermod -aG sudo vladan                 # give it admin (sudo) rights
apt update && apt upgrade -y
```
You can keep working as root for the rest, or reconnect as the new user:
`ssh vladan@YOUR_SERVER_IP`.

## 3. Install what you need

```bash
sudo apt install -y python3 python3-venv python3-pip nginx git
```

## 4. Get the code onto the server

Either `git clone` your repo, or copy it up from your machine with `scp`/`rsync`.
Target a folder like `/home/vladan/zbrisi`:

```bash
# option A — from GitHub
git clone https://github.com/<you>/zbrisi.git /home/vladan/zbrisi
# option B — from your Windows machine (run locally), excludes junk:
# scp -r ./zbrisi vladan@YOUR_SERVER_IP:/home/vladan/zbrisi
cd /home/vladan/zbrisi
```

## 5. Virtualenv + dependencies

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## 6. Create the .env (secrets — never commit it)

```bash
nano .env
```
```ini
# Get the token from travelpayouts.com -> Programs -> Aviasales -> API.
# (It's also in your local .env — copy it from there.)
TRAVELPAYOUTS_TOKEN=your_aviasales_api_token
TRAVELPAYOUTS_MARKER=your_marker_id
FLIGHTS_CURRENCY=eur
FLIGHTS_MARKET=us
FLASK_DEBUG=0
```
(Operator name/country and contact email already have correct defaults in code.)

Quick sanity check before wiring up services:
```bash
.venv/bin/gunicorn app:app --bind 127.0.0.1:8000 &
curl -s localhost:8000/health ; kill %1
# expect: {"status":"ok","provider":"travelpayouts","marker":true,...}
```

## 7. Run it as a service (systemd)

```bash
sudo cp deploy/zbrisi.service /etc/systemd/system/zbrisi.service
# edit the file if your user/paths differ from /home/vladan/zbrisi
sudo systemctl daemon-reload
sudo systemctl enable --now zbrisi
sudo systemctl status zbrisi            # should say "active (running)"
```

## 8. Put nginx in front

```bash
sudo cp deploy/nginx-zbrisi.conf /etc/nginx/sites-available/zbrisi
sudo ln -s /etc/nginx/sites-available/zbrisi /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default      # drop the welcome page
sudo nginx -t && sudo systemctl reload nginx
```
Visit `http://zbrisi.com` — the site should load over plain HTTP.

## 9. Turn on HTTPS (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d zbrisi.com -d www.zbrisi.com
```
Choose **redirect HTTP → HTTPS** when asked. Certbot edits the nginx config to
add the `443` block and auto-renews via a timer. Done — `https://zbrisi.com` is
live, and `ProxyFix` + the forwarded headers make all canonical/sitemap URLs
render as `https://zbrisi.com/...`.

## 10. Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

## 11. Verify

- `https://zbrisi.com/health` → `"marker": true`
- `https://zbrisi.com/sitemap.xml` → URLs are `https://zbrisi.com/...`
- Submit the sitemap to Google Search Console.

## 12. Update Travelpayouts (now that the site is live)

In travelpayouts.com → **Tools → Projects**: change the demo website URL to
`https://zbrisi.com`, then verify ownership (**Drive** tab → meta tag or HTML
file). Your marker stays the same.

---

### Updating later

```bash
cd /home/vladan/zbrisi && git pull          # or re-copy the files
.venv/bin/pip install -r requirements.txt   # if deps changed
sudo systemctl restart zbrisi
```
