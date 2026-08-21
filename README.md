# ConsumerSheildAI

ConsumerSheildAI is a modern full-stack AI web application that helps users understand consumer-rights options for refund denial, wrong product delivery, defective products, warranty disputes, and delivery issues.

The app is designed as an evidence-based rights navigator, not a chatbot. It combines FastAPI, Next.js 15, Gemini, Retrieval-Augmented Generation, ChromaDB, OCR, and explainable outputs.

## Architecture

- `frontend/`: Next.js 15, TypeScript, Tailwind CSS, shadcn-style UI primitives.
- `backend/`: FastAPI application, thin API routes, service classes, OCR, SQLite storage.
- `rag/`: document loading, chunking, encapsulated embeddings, ChromaDB seeding, retrieval.
- `knowledge_base/`: sample consumer-rights dataset with law and marketplace policy summaries.
- `database/`: SQLite and ChromaDB persistence location.
- `uploads/`: uploaded OCR files.

## Use of Encapsulation (Data Wrapping)

ConsumerSheildAI hides implementation details behind service classes so routes, controllers, and UI components do not directly access Gemini, ChromaDB, EasyOCR, or SQLite.

- `GeminiService` wraps the Gemini API key, model name, prompt templates, retries, and response parsing. Other modules call public methods such as `classifyComplaint()`, `explainRights()`, and `generateComplaintLetter()`.
- `ChromaService` wraps the ChromaDB client, collections, embedding model, document insertion, vector search, deletion, and collection stats. Retrieval code asks for documents through public methods instead of touching ChromaDB directly.
- `OCRService` wraps upload persistence, image enhancement, EasyOCR initialization, OCR extraction, and cleanup.
- `RAGService` wraps retailer detection, single-retailer policy retrieval, legal retrieval, and Gemini-backed rights-summary generation.
- `ScoringService` wraps deterministic evidence completeness, case strength, verdict, timeline, and negative-reasoning calculations.
- `DatabaseService` wraps SQLite initialization and persistence so business logic does not manage database sessions directly.

This data-wrapping structure improves security, maintainability, testability, and separation of concerns. Public methods expose what the application needs; private members hide API keys, database connections, embedding generation, OCR engines, vector search internals, and scoring helper calculations.

## Features

- Landing page with SaaS-style responsive design.
- Complaint analysis dashboard.
- Complaint text, invoice upload, and screenshot upload.
- EasyOCR extraction with editable extracted text.
- Issue classification into Refund Denial, Wrong Product, Defective Product, Warranty Issue, or Delivery Issue.
- RAG retrieval from ChromaDB.
- Gemini 2.5 Flash response generation with deterministic fallback when no API key is configured.
- Gemini embeddings with local hashing fallback for development.
- Explainable AI panel with reasons, evidence sources, and confidence indicators.
- Responsible AI disclaimer and balanced evaluation of positive and negative factors.
- Recommended action timeline with reason, evidence, and confidence score for each action.
- Email draft and complaint-letter generator with copy controls.

## Backend Setup

From the project root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `CONSUMERSHEILDAI_GEMINI_API_KEY` in `backend/.env` for Gemini-powered generation and embeddings. Without a key, the app uses deterministic fallback generation and local hash embeddings so the workflow still runs.

Seed ChromaDB:

```bash
cd ..
python3 -m rag.seed
```

Run the API:

```bash
uvicorn backend.app.main:app --reload --port 8000
```

Health check:

```bash
curl http://localhost:8000/api/health
```

## Frontend Setup

From the project root:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Deploy on Render

The repository includes `render.yaml` to deploy the full application as two Render web services: a FastAPI API and a Next.js frontend. In Render, create a new Blueprint from this GitHub repository and set `CONSUMERSHEILDAI_GEMINI_API_KEY` in the API service's environment settings if Gemini generation is required. The application still works with its local deterministic fallback when that key is omitted.

## API

`POST /api/ocr/extract`

- Multipart field: `file`
- Returns extracted OCR text.

`POST /api/analyze`

- Multipart field: `complaint_text`
- Optional files: `invoice`, `screenshot`
- Returns category, rights summary, reasons, evidence sources, case scores, recommended actions, email draft, complaint letter, extracted text, and disclaimer.
- Explanation

The module is not an image captioner. It behaves like a product-inspection system and never states that a product is definitely defective, never determines legal liability, and never assumes warranty eligibility. The dashboard states that image analysis is based only on visual observations and does not establish legal liability or manufacturing defects.

Image evidence contributes to case strength but never decides the case alone:

- Severe visible damage: `+20`
- Minor visible damage: `+10`
- Image supports complaint: positive support
- Image contradicts complaint: `-15`
- Missing image: no effect

The final case evaluation still combines complaint text, OCR, policies, legal sources, timeline, retailer detection, and evidence completeness.

## Responsible AI Notes

ConsumerSheildAI displays the disclaimer:

> This platform provides informational guidance and does not constitute legal advice.

Every recommendation includes:

- Reason
- Evidence
- Confidence score

The database stores only anonymous operational metadata:

- Complaint category
- Case strength score
- Evidence score
- Policy matches
- Timestamp
- Anonymous session ID

## Extending The Knowledge Base

Add Markdown files to `knowledge_base/`, then reseed:

```bash
python3 -m rag.seed
```

For production, replace the sample policy summaries with vetted jurisdiction-specific materials and platform policy documents.
