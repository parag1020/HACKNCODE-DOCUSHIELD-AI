# DOCUSHIELD AI — Architecture

```text
Analyst
  |
  v
Streamlit User Interface
  |
  v
Document Ingestion & SHA-256 Evidence Identifier
  |
  +--> PDF Text Extraction (PyMuPDF)
  |
  +--> Image OCR Adapter (Tesseract, optional)
  |
  +--> Basic Image Screening (Pillow heuristic)
  |
  v
Structured Field Extraction (transparent regex rules)
  |
  v
Cross-Document Comparison
  |
  v
Discrepancy Register + Human Review
  |
  v
JSON / TXT Investigation Dossier
```

## Data flow
Uploaded bytes are processed locally in the Streamlit session. SHA-256 is computed over the original uploaded bytes. Extracted values retain a document-level reference through filename and hash. The current prototype does not persist files to a database.

## Trust boundaries
- Only authorized or synthetic documents should be uploaded.
- OCR text is unverified data.
- A discrepancy is not proof of fraud.
- Visual screening is heuristic and cannot prove manipulation.
- Human review is required before consequential decisions.
