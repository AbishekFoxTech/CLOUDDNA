# CloudDNA

AI-Powered Cloud-Native Digital Asset Intelligence Platform — a final-year engineering project built with Django 5, Bootstrap 5, and Cloudinary.

## Tech Stack

- **Backend:** Python, Django 5, SQLite3
- **Frontend:** Django Templates, HTML5, Bootstrap 5, JavaScript
- **Auth:** Django's built-in authentication system
- **Storage:** Cloudinary (env-configured; falls back to local media storage when no credentials are set)
- **AI pipeline:** pdfplumber + PyMuPDF (PDF text/OCR fallback), python-docx
  (DOCX), pytesseract + Tesseract OCR (images), spaCy + NLTK (keywords/
  language), scikit-learn (TF-IDF summarization & document similarity)

## Project Structure

```
CloudDNA/
├── config/            # Project settings, root urls, context processors
├── accounts/           # Registration, login, logout, profile, settings, password reset
├── dashboard/          # Authenticated dashboard home
├── documents/          # Document upload / list / search / filter / AI-enhanced detail
├── ai_engine/          # AI pipeline: services/ (extraction, keywords, summary,
│                       # categorizer, similarity), signal-triggered on upload,
│                       # AI Insights page, retry-processing endpoint
├── relationships/      # DocumentRelationship model - TF-IDF similarity edges
├── search_engine/      # Reserved for future dedicated search-engine features
├── recommendations/    # Reserved for future recommendation features
├── templates/           # Shared base templates + per-app templates
├── static/              # CSS / JS / images
├── media/               # User uploads (local storage fallback, gitignored)
├── .env                 # Local environment variables (gitignored)
└── manage.py
```

## Getting Started

1. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   source venv/Scripts/activate   # Windows (Git Bash)
   venv\Scripts\activate          # Windows (cmd/PowerShell)
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**

   Copy `.env.example` to `.env` and fill in real values as needed:
   ```bash
   cp .env.example .env
   ```
   Cloudinary credentials can be left blank during development — the project
   automatically falls back to local filesystem storage under `media/` until
   `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET`
   are all set.

   **Cloudinary account setting required for PDFs:** newer Cloudinary
   accounts disable delivery of raw PDF/ZIP files by default (a platform-wide
   anti-abuse default, not something this app can configure via API). If PDF
   uploads fail AI processing with "Could not read the uploaded file: 401",
   enable **Console → Settings (gear icon) → Security → PDF and ZIP files
   delivery**. DOCX/TXT/image uploads are unaffected by this setting.

4. **Set up the AI pipeline dependencies**

   - Install [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (the
     system binary, not just the Python wrapper). On Windows:
     `winget install --id UB-Mannheim.TesseractOCR -e`. If it isn't installed
     at the default path, set `TESSERACT_CMD` in `.env` to the full path of
     `tesseract.exe` / `tesseract`.
   - The spaCy model (`en_core_web_sm`) is pinned in `requirements.txt` as a
     direct wheel URL, so `pip install -r requirements.txt` installs it
     automatically. NLTK's `punkt`, `punkt_tab`, and `stopwords` corpora
     download automatically on first use (or run them ahead of time:
     `python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('stopwords')"`).
   - If either dependency is missing at runtime, the pipeline fails soft: the
     affected document is marked "AI Processing Failed" with a description of
     what went wrong, and can be retried from its detail page once fixed.

5. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create an admin user**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the development server**
   ```bash
   python manage.py runserver
   ```

   Visit http://127.0.0.1:8000/

## Features

- Home, About, 404, and 500 pages
- Full authentication flow: register, login (with "remember me" and basic
  brute-force login protection), logout, forgot/reset password, password
  change
- User profile with avatar, bio, job title, and organization
- Document management: upload (drag & drop, progress bar, Cloudinary
  storage), list/search/filter, favorites, rename, download, delete
- **AI document intelligence** (`ai_engine`), triggered automatically on
  every upload via a `post_save` signal:
  - Text extraction: pdfplumber (PDF, with a PyMuPDF+OCR fallback for
    scanned/image-only PDFs), python-docx (DOCX), pytesseract (images), or a
    direct read (TXT)
  - Auto-generated summary (extractive, TF-IDF sentence ranking), keywords
    (spaCy noun-chunks/entities, with an NLTK fallback), and detected
    category (rule-based keyword classifier)
  - Word count, estimated reading time, language guess, and a SHA-256
    document hash
  - Document similarity via TF-IDF + cosine similarity against the same
    owner's other processed documents, stored as `DocumentRelationship`
    rows and shown as "related documents" with a similarity score
  - Fails soft: extraction errors (missing OCR engine, corrupt file,
    unsupported content) mark the document "AI Processing Failed" with a
    human-readable reason and a retry button, instead of breaking the upload
  - Dedicated AI Insights page per document, plus AI sections on the
    document detail page and AI-specific dashboard widgets (documents
    processed, pending, most common categories, most frequent keywords,
    recent AI activity)
- Dashboard with live document count, storage usage, recent uploads, recent
  activity feed, and a relationship graph placeholder
- Responsive Bootstrap 5 UI with a persistent sidebar, breadcrumb navigation,
  flash messages, and a light/dark theme toggle (persisted in
  `localStorage`)

## Security

- CSRF protection on all forms
- Django's password validators (length, similarity, common password, numeric)
- Environment-based secrets (`SECRET_KEY`, Cloudinary credentials, email
  credentials) — nothing sensitive is hardcoded
- Session cookies configured as `HttpOnly` / `SameSite=Lax`
- Basic login-attempt throttling per username + IP (see `accounts/utils.py`)

## Apps Registered for Future Phases

`search_engine` and `recommendations` are scaffolded and registered in
`INSTALLED_APPS` but intentionally left without business logic — future
entry points for a dedicated search engine and personalized document
recommendations. `ai_engine` and `relationships` are now fully implemented
(see Features above).
