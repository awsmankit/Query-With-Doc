# Query-With-Doc

Query-With-Doc is a small Flask-based service that lets you upload PDF or text documents, process them into embeddings (via Azure OpenAI embeddings), store a local vectorstore (FAISS), and ask natural-language questions against the processed documents. It also supports extracting questions from a document and basic per-user cache management.

This README explains how the project is structured, which environment variables are required, how to run the service locally, the available HTTP endpoints, and implementation notes.

## Repository layout

- `app.py` - Flask application entrypoint. Registers routes and cache.
- `controller/controller.py` - Flask blueprint that defines the HTTP endpoints and wires services.
- `service/` - Business logic services:
	- `upload_service.py` - Handles file uploads, decryption, text extraction and splitting.
	- `pdf_processing_service.py` - Builds FAISS vectorstore from split text and saves it to disk.
	- `question_answering_service.py` - Loads the vectorstore and runs retrieval + LLM to answer user queries.
	- `question_retrieval_service.py` - Uses a retriever + LLM to generate a list of relevant questions from a document.
	- `utility_service.py` - Helpers for allowed file checks, local OCR extraction, and cache clearing.
- `utility/` - Low level utilities:
	- `security.py` - AES encryption/decryption helpers and local key handling.
	- `encryption_key.key` - (binary) symmetric key used by `security.py` (already committed in repo).

## Features

- Upload PDF or text files per user. Files are stored under `./uploads/{userId}`.
- Decrypts uploaded files using AES-GCM and a local key from `utility/encryption_key.key`.
- Extracts text using `pdfminer` for text-based PDFs and `pytesseract` OCR for scanned PDFs.
- Splits documents into chunks and persists them (pickled) locally.
- Builds a FAISS vectorstore using Azure embeddings and saves the vectorstore to `./vectorstores/vectorstore_{userId}.pkl`.
- Answer open-ended questions using Azure OpenAI chat models + RetrievalQA.
- Generate a list of relevant questions from a document snippet.
- Simple in-memory cache (Flask-Caching 'simple') to hold splits and retrievers.

## Requirements

- Python 3.10+ (recommended)
- The code uses these noteworthy Python packages (non-exhaustive):
	- Flask
	- Flask-Caching
	- python-dotenv
	- langchain (and langchain-openai Azure wrappers used here)
	- langchain_community (FAISS wrapper)
	- faiss or faiss-cpu
	- pdfminer.six
	- pytesseract
	- pdf2image
	- pycryptodome

Create a virtual environment and install dependencies. Example (Mac / zsh):

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# Install the packages your project needs (create requirements.txt as desired)
pip install flask flask-caching python-dotenv langchain langchain-openai langchain-community faiss-cpu pdfminer.six pytesseract pdf2image pycryptodome
```

Notes:
- `pdf2image` requires `poppler` on macOS: `brew install poppler`.
- `pytesseract` requires Tesseract OCR: `brew install tesseract`.
- Use `faiss-cpu` on machines without GPU support.

## Environment variables

Create a `.env` file in the project root with the following variables (examples):

- `OPENAI_API_KEY` - (optional) if the langchain Azure wrappers in your environment require it.
- Any Azure-specific configuration is currently hard-coded in `controller/controller.py` for `AzureOpenAIEmbeddings` and `AzureChatOpenAI` (endpoints and deployments). Update those in code or move them to env vars as needed.

Example `.env`:

```
OPENAI_API_KEY=sk-XXXXX
# You may add other Azure/OpenAI keys or endpoints if you refactor the controller to read them from env
```

## How to run

Start the Flask server (from the project root):

```bash
source .venv/bin/activate
python app.py
```

The app listens on port 9069 by default and will be reachable at http://0.0.0.0:9069

## HTTP API Endpoints

All endpoints expect a `userId` header in requests (used to separate user uploads, caches and vectorstores).

- POST /upload
	- Description: Upload a file (PDF or text). The service will save the file, decrypt it using `utility/security.py`, extract text, split into chunks, and store the splits in cache and a pickled file under `./uploads/{userId}`.
	- Headers: `userId` (required)
	- Body: multipart/form-data with a `file` field
	- Responses:
		- 200: { "message": "File uploaded & Text Extracted" }
		- 400/500: JSON error message

- POST /process_pdf
	- Description: Processes previously saved split content into a FAISS vectorstore using Azure embeddings and saves it to `./vectorstores/vectorstore_{userId}.pkl`.
	- Headers: `userId` (required)
	- Body: none
	- Responses: 200 with { "message": "File has been processed successfully" } or an error message

- POST /ask
	- Description: Ask a natural-language question about a user's uploaded documents. The service loads `vectorstore_{userId}.pkl`, creates a retriever, and runs RetrievalQA with the configured Azure chat model.
	- Headers: `userId` (required)
	- Body (JSON): { "question": "Your question here" }
	- Responses:
		- 200: { "answer": "..." }
		- 400/500: JSON error message

- POST /get-questions
	- Description: Generate several relevant questions from a provided document text snippet.
	- Headers: `userId` (required)
	- Body (JSON): { "document_text": "...", "num_questions": 5 }
	- Responses:
		- 200: { "status": "success", "questions": [ ... ] }
		- 500: { "status": "error", "message": "..." }

- POST /flush
	- Description: Clears cached entries for the user (splits, retriever) and any local uploads. Intended to flush user data.
	- Headers: `userId` (required)
	- Responses: 200 on success, 500 on failure

## Example usage (curl)

Upload a file:

```bash
curl -X POST "http://localhost:9069/upload" \
	-H "userId: user123" \
	-F "file=@/path/to/your/document.pdf"
```

Ask a question:

```bash
curl -X POST "http://localhost:9069/ask" \
	-H "Content-Type: application/json" \
	-H "userId: user123" \
	-d '{"question":"What is the main purpose of the document?"}'
```

Generate questions from text:

```bash
curl -X POST "http://localhost:9069/get-questions" \
	-H "Content-Type: application/json" \
	-H "userId: user123" \
	-d '{"document_text":"<paste a short document snippet>", "num_questions": 5}'
```

Flush user data:

```bash
curl -X POST "http://localhost:9069/flush" -H "userId: user123"
```

## Implementation notes and caveats

- Hard-coded Azure endpoints and deployment names: `controller/controller.py` creates `AzureOpenAIEmbeddings` and `AzureChatOpenAI` with hard-coded endpoints and deployment names. For production, move these values to environment variables or a configuration file.
- Security: The repo includes `utility/encryption_key.key` and `utility/security.py` which reads/writes the key from disk. For a production system, do NOT store secrets in the repo; use a secure keystore or environment-based secret store.
- Vectorstore persistence: Vectorstores are saved to `./vectorstores`. Ensure proper backups or move to blob storage if needed.
- Concurrency: The server uses Flask's default development server in `app.py`. For production use a WSGI server like Gunicorn or Uvicorn (if converting to ASGI).
- Large PDFs and OCR: OCR conversion requires external binaries and enough memory/disk space; monitor resource usage for large files.

## Next steps / improvements

- Make Azure endpoints and deployment names configurable via environment variables.
- Add authentication and authorization; `userId` header is currently trusted.
- Move vectorstore and uploaded files to cloud storage (e.g., Azure Blob Storage).
- Add unit/integration tests and CI.

## License

This project does not include a license file. Add an appropriate license if you plan to share or open-source the code.

## Contact

If you need help running or extending this code, provide details on the issue and attach logs where appropriate.
