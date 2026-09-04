# Cornell Rugby Website

A Flask-based website for Cornell Rugby, with separate Men's and Women's sections, a browser-based admin panel for managing players, coaches, and schedule — all backed by JSON files on disk.

---

## Local Development (Running on Your Own Computer)

### 1. Prerequisites
- Python 3.10 or higher
- `pip` (comes with Python)

### 2. Clone the Repository
```bash
git clone https://github.com/<your-org>/cornell-rugby.git
cd cornell-rugby
```

### 3. Create a Virtual Environment and Install Dependencies
```bash
python3 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Run the Development Server
```bash
python app.py
```

Open your browser to: **http://127.0.0.1:5000**

Admin panel: **http://127.0.0.1:5000/admin/**

---

## Deploying to a Linux VPS (Production)

### 1. Provision the Server
- Ubuntu 22.04 LTS or RHEL 9 recommended
- Create a non-root user (example below uses `cornellrugby`)

```bash
adduser cornellrugby
usermod -aG sudo cornellrugby
```

### 2. Install System Dependencies
```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx git
```

### 3. Clone Repo and Set Up App
```bash
su - cornellrugby
git clone https://github.com/<your-org>/cornell-rugby.git
cd cornell-rugby
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Generate a Secret Key
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```
Copy the output — you'll use it in the next step.

### 5. Configure the Systemd Service
```bash
# Copy and edit the service file
sudo cp deploy/gunicorn.service /etc/systemd/system/cornellrugby.service
sudo nano /etc/systemd/system/cornellrugby.service
```
Edit the following placeholders:
- `cornellrugby` → your system username
- `/home/cornellrugby/cornell-rugby` → actual repo path
- `replace-with-a-long-random-secret` → the key you generated above

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable cornellrugby
sudo systemctl start cornellrugby
sudo systemctl status cornellrugby   # should show "active (running)"
```

### 6. Configure Nginx
```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/cornellrugby
# Edit domain name and static path
sudo nano /etc/nginx/sites-available/cornellrugby
sudo ln -s /etc/nginx/sites-available/cornellrugby /etc/nginx/sites-enabled/
sudo nginx -t          # test config
sudo systemctl reload nginx
```

### 7. Get a Free HTTPS Certificate (Let's Encrypt)
```bash
sudo certbot --nginx -d cornellrugby.com -d www.cornellrugby.com
```
Follow the prompts. Certbot will automatically update your Nginx config with the certificate paths.

### 8. Test
Visit `https://cornellrugby.com` in your browser.

---

## Project Structure

```
cornell-rugby/
├── app.py                    # Flask routes
├── helpers.py                # JSON load/save helpers
├── requirements.txt
├── data/
│   ├── men/                  # players.json, coaches.json, schedule.json
│   └── women/
├── static/
│   ├── css/style.css         # all styles (edit colors here)
│   ├── js/main.js            # navigation + bio panel JS
│   └── images/               # logo.png + team photos
│       ├── men/
│       └── women/
├── templates/
│   ├── base.html             # shared nav / footer
│   ├── home.html
│   ├── team/                 # players, coaches, schedule, recruit, fan
│   └── admin/                # admin panel templates
├── deploy/
│   ├── nginx.conf
│   └── gunicorn.service
├── README.md
└── CUSTOMIZING.md            # non-developer guide
```

---

## Updating the Site After Changes

```bash
cd cornell-rugby
git pull
sudo systemctl restart cornellrugby
```
