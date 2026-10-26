# Putting Servana online

Two parts: (A) put the code on GitHub, (B) run it on PythonAnywhere (free for a student project).
Replace `YOURUSERNAME` with your own names. Do the parts in order.

---

## A. Put the project on GitHub

1. Make a free account at **github.com**.
2. Install **Git for Windows** from git-scm.com (accept the default options). Close and reopen VS Code afterwards.
3. On GitHub click **New repository**.
   - Name: `MultiServiceMarketplace`
   - Choose **Public**
   - Do **not** tick "Add a README" (you already have one)
   - Click **Create repository**
4. In VS Code, open the terminal (Ctrl + `) in the folder that contains `manage.py`.
5. Tell Git who you are (once only):
   ```
   git config --global user.name "Your Name"
   git config --global user.email "you@example.com"
   ```
6. Send the project to GitHub:
   ```
   git init
   git add .
   git commit -m "Servana final project"
   git branch -M main
   git remote add origin https://github.com/YOURUSERNAME/MultiServiceMarketplace.git
   git push -u origin main
   ```
   A browser window opens to sign in to GitHub the first time.
7. Refresh your GitHub page. You should see `manage.py`, `README.md`, `accounts/`, and so on.
   You should **not** see `db.sqlite3`, `venv/` or `media/` (the `.gitignore` file hides them).
8. Copy the repository address. This is your **GitHub link**.

To send later changes:
```
git add .
git commit -m "Describe what you changed"
git push
```

---

## B. Deploy on PythonAnywhere

### 1. Make an account
Go to **pythonanywhere.com** and create a free **Beginner** account.
Your site address will be `https://YOURUSERNAME.pythonanywhere.com`.

### 2. Get the code and install it
1. Open the **Consoles** tab and start a **Bash** console.
2. Download your code:
   ```
   git clone https://github.com/YOURUSERNAME/MultiServiceMarketplace.git
   cd MultiServiceMarketplace
   ```
3. Django 6 needs Python 3.12 or newer. See what is available:
   ```
   ls /usr/bin/python3*
   ```
   Use the newest one that is 3.12 or higher in the next command (3.12 is shown as an example):
   ```
   mkvirtualenv --python=/usr/bin/python3.12 venv
   pip install -r requirements.txt
   ```
   If nothing 3.12 or newer is offered, tell your tutor or ask for help. Django 5.2 works on older Python versions.
4. Create the database, demo data and static files:
   ```
   python manage.py migrate
   python manage.py seed_demo
   python manage.py collectstatic --noinput
   mkdir -p media
   ```
5. Make a secret key and copy the result for step 4 below:
   ```
   python -c "import secrets; print(secrets.token_urlsafe(50))"
   ```

### 3. Create the web app
1. Open the **Web** tab and click **Add a new web app**.
2. Choose **Manual configuration** (not "Django"), then the same Python version as above.
3. On the Web tab fill in:
   - **Virtualenv:** `/home/YOURUSERNAME/.virtualenvs/venv`
   - **Source code:** `/home/YOURUSERNAME/MultiServiceMarketplace`
   - **Working directory:** `/home/YOURUSERNAME/MultiServiceMarketplace`
4. Under **Static files** add two rows:

   | URL | Directory |
   |---|---|
   | `/static/` | `/home/YOURUSERNAME/MultiServiceMarketplace/staticfiles` |
   | `/media/` | `/home/YOURUSERNAME/MultiServiceMarketplace/media` |

5. Click the link to the **WSGI configuration file**. Delete everything in it and paste this
   (change `YOURUSERNAME` in four places and paste your secret key):
   ```python
   import os
   import sys

   path = '/home/YOURUSERNAME/MultiServiceMarketplace'
   if path not in sys.path:
       sys.path.insert(0, path)

   os.environ['DJANGO_SETTINGS_MODULE'] = 'MultiServiceMarketplace.settings'
   os.environ['SECRET_KEY'] = 'PASTE-YOUR-LONG-SECRET-KEY-HERE'
   os.environ['DEBUG'] = 'False'
   os.environ['ALLOWED_HOSTS'] = 'YOURUSERNAME.pythonanywhere.com'
   os.environ['CSRF_TRUSTED_ORIGINS'] = 'https://YOURUSERNAME.pythonanywhere.com'

   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```
   Save the file.
6. Turn on **Force HTTPS** on the Web tab (optional but recommended).
7. Click the green **Reload** button, then open your site address.

### 4. Check it
- The home page opens with colours and images.
- Log in with the demo accounts from the README (admin / provider / customer / business).
- Book a service, upload a photo, and open the admin dashboard.

### 5. Finish
1. Paste the site address and the GitHub address into `README.md`.
2. Send the change to GitHub (`git add .`, `git commit -m "Add links"`, `git push`).
3. Submit both links.

### Updating the live site later
In a PythonAnywhere Bash console:
```
cd MultiServiceMarketplace
git pull
python manage.py migrate
python manage.py collectstatic --noinput
```
Then press **Reload** on the Web tab.

### Good to know
- Free PythonAnywhere sites switch off after three months unless you press the
  **Run until 3 months from today** button on the Web tab. Do this before your marking date.
- Uploaded images and the database stay on the PythonAnywhere server. They are not on GitHub.
- If you see "Something went wrong", open the **error log** link on the Web tab. The last lines
  tell you what is wrong. Paste them here for help.
