# Minoire

A full-stack AI-powered virtual closet application. Upload your wardrobe, get outfit suggestions built on color theory and ML, track what you wear, and find patterns in your own style over time.

Detailed build logs, training results, architecture decisions, and every error along the way are documented at [faridasabra.github.io](https://faridasabra.github.io)

---

## What it does

- Upload clothing photos, get automatic background removal, classification, and color extraction
- Get outfit suggestions ranked by color harmony, formality compatibility, and season
- Find visually similar items in your wardrobe via CLIP embedding cosine similarity
- Track wear history and build analytics around your actual dressing habits
- Community feed of verified-real outfits from real wardrobes (coming)

---

## Architecture

minoire-app/
├── app/
│ ├── main.py — entry point, router registration
│ ├── config.py — environment variable loading
│ ├── database.py — SQLAlchemy engine and session
│ ├── dependencies.py — JWT auth guard
│ ├── models/ — SQLAlchemy ORM table definitions
│ ├── schemas/ — Pydantic request/response models
│ ├── routers/ — FastAPI route handlers
│ └── services/
│ ├── auth.py — password hashing, JWT
│ ├── s3.py — Cloudflare R2 upload/delete
│ ├── cv.py — CV pipeline (rembg, CLIP, EfficientNet, K-means)
│ └── outfit_scorer.py — color harmony and formality scoring
├── models/ — trained model weights and label encoders
├── config/
│ └── color_lookup.json — 949 XKCD colors with Lab values
└── scripts/
└── generate_color_lookup.py

---

## CV pipeline

Every clothing photo goes through a four-step pipeline on upload:

1. **Background removal:** rembg (U2-Net) produces a transparent-background PNG
2. **Semantic embedding:** CLIP ViT-B/32 generates a 512-dimensional L2-normalized vector stored in pgvector
3. **Classification:** EfficientNet-B3 fine-tuned on Fashion Product Images dataset predicts category and formality (99.5% validation accuracy on category)
4. **Color extraction:** K-means clustering (k=5) in Lab color space extracts primary, secondary, and tertiary colors matched against 949 XKCD named colors

---

## Outfit scoring

Outfits are ranked by a composite score:

S = 0.40 · Charmony + 0.40 · Fmatch + 0.20 · Sseason

- **Charmony:** color harmony score computed from dominant hex values using HSL math (monochromatic, analogous, complementary, triadic detection)
- **Fmatch:** formality compatibility (same tier = 1.0, one tier apart = 0.7, two tiers = 0.2)
- **Sseason:** season compatibility based on item season tags

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10, FastAPI, SQLAlchemy 2.0, Alembic |
| Database | PostgreSQL 16 (Docker) + pgvector |
| CV / ML | PyTorch, EfficientNet-B3, CLIP ViT-B/32, rembg, open-clip, scikit-learn |
| Storage | Cloudflare R2 (S3-compatible) |
| Auth | JWT via python-jose + passlib |
| Frontend (planned) | Next.js 14, TailwindCSS, React Three Fiber |

---

## Setup

**Prerequisites:** Python 3.10, Docker Desktop with WSL2

**1. Clone and create virtual environment**
```bash
git clone https://github.com/faridasabra/minoire-app.git
cd minoire-app
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

**2. Start the database**
```bash
docker run -d --name minoire-db \
  -e POSTGRES_PASSWORD=yourpassword \
  -e POSTGRES_DB=minoire \
  -p 5433:5432 \
  pgvector/pgvector:pg16
```

Then enable the pgvector extension:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

**3. Configure environment**

Create a `.env` file at the project root:
```env
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5433/minoire
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
AWS_ACCESS_KEY_ID=your-r2-access-key
AWS_SECRET_ACCESS_KEY=your-r2-secret-key
AWS_REGION=auto
S3_BUCKET_NAME=your-bucket-name
R2_ACCOUNT_ID=your-cloudflare-account-id
```

**4. Add model weights**

Place the following files in the `models/` directory:
- `minoire_fashion_classifier.pth`
- `category_encoder.pkl`
- `formality_encoder.pkl`
- `color_encoder.pkl`

Training notebook available on request.

**5. Run**
```bash
uvicorn app.main:app --reload
```

API docs available at `http://127.0.0.1:8000/docs`

---

## API overview

| Method | Path | Description |
|---|---|---|
| POST | /auth/register | Create account |
| POST | /auth/login | Login, returns JWT |
| GET | /clothing/ | List wardrobe items |
| POST | /clothing/ | Create clothing item |
| POST | /clothing/{id}/upload-image | Upload image, triggers CV pipeline |
| GET | /clothing/{id}/similar | Find similar items by CLIP cosine distance |
| POST | /outfits/generate | Generate ranked outfit suggestions |
| POST | /outfits/{id}/score | Score a manually built outfit |
| GET | /wear-logs/ | Wear history |
| POST | /wear-logs/ | Log a wear event |

---

## Build status

| Phase | Status |
|---|---|
| 1. Core backend | Complete |
| 2. CV pipeline | Complete |
| 3. Outfit generator | In Progress |
| 4. Recommendation engine | Planned |
| 5. Wardrobe analytics | Planned |
| 6. Frontend | Planned |
| 7. Real-time features | Planned |
| 8. Cloud deployment | Planned |

---

## Author

Farida Sabra — [faridasabra.github.io](https://faridasabra.github.io) · [LinkedIn](https://www.linkedin.com/in/farida-sabra/)
