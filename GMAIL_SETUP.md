# Connect your real Gmail to Relay

## 1. Google Cloud setup (one time, ~5 min)
1. Go to https://console.cloud.google.com → create a project (e.g. "relay").
2. **APIs & Services → Library** → enable **Gmail API**.
3. **APIs & Services → OAuth consent screen** → User type **External** → fill app name + your email.
   - Scopes: add `gmail.readonly`, `gmail.send`, `userinfo.email`.
   - **Test users → Add your own Gmail address** (required while the app is in "Testing").
4. **Credentials → Create Credentials → OAuth client ID** → type **Web application**.
   - Authorized redirect URI: `http://localhost:8000/auth/google/callback`
   - Copy the Client ID and Client Secret.

## 2. Backend `.env`
```
GOOGLE_CLIENT_ID=...apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
FRONTEND_URL=http://localhost:5173
ALLOWED_ORIGINS=http://localhost:5173
TOKEN_ENCRYPTION_KEY=<generate below>
```
Generate the encryption key:
```
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## 3. Reset the database (schema changed)
Stop uvicorn, then in `backend/`:
```
del relay.db
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --reload
```

## 4. Use it
Frontend → **Email Accounts** → **+ Connect Gmail** → approve on Google
(you'll see an "unverified app" warning — Advanced → Continue, normal in Testing mode)
→ **Sync inbox** → open **Inbox** → click an email → Claude drafts 10 replies
→ **Send this reply** sends a real threaded reply from your Gmail.

Replies are only sent when YOU click Send — nothing is ever sent automatically.
