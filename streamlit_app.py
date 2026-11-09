
import streamlit as st
import fitz
from PIL import Image, ImageChops, ImageEnhance
import io, re, hashlib, json, csv
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

st.set_page_config(page_title="DOCUSHIELD AI | HACKNCODE", page_icon="🛡️", layout="wide")

# ---------- Helpers ----------
def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()

def extract_pdf_text(data):
    doc = fitz.open(stream=data, filetype="pdf")
    pages = []
    for i, page in enumerate(doc):
        pages.append({"page": i+1, "text": page.get_text("text")})
    return pages

def extract_image_text(data):
    try:
        import pytesseract
        img = Image.open(io.BytesIO(data)).convert("RGB")
        return pytesseract.image_to_string(img), "Tesseract OCR"
    except Exception:
        return "", "OCR engine unavailable (install Tesseract + pytesseract)"

def fields_from_text(text):
    patterns = {
        "name": r"(?:name|applicant)\s*[:\-]\s*([A-Za-z][A-Za-z .'-]{1,60})",
        "date_of_birth": r"(?:dob|date of birth)\s*[:\-]\s*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})",
        "document_id": r"(?:id|document id|application id|aadhaar)\s*[:\-]\s*([A-Z0-9\-]{4,24})",
        "address": r"(?:address)\s*[:\-]\s*([^\n]{4,100})",
        "amount": r"(?:amount|salary|income)\s*[:\-]\s*(?:INR|Rs\.?|₹)?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
        "email": r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b"
    }
    out = {}
    for key, pattern in patterns.items():
        m = re.search(pattern, text, re.I)
        if m:
            out[key] = m.group(1).strip()
    return out

def visual_checks(data, filename):
    findings = []
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
        findings.append({"title":"Image dimensions", "detail":f"{img.width} × {img.height} pixels", "status":"Observed"})
        findings.append({"title":"Image format", "detail":f"{Image.open(io.BytesIO(data)).format}", "status":"Observed"})
        # JPEG ELA is only a screening heuristic, not proof of manipulation.
        if filename.lower().endswith((".jpg",".jpeg")):
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=90)
            recompressed = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
            diff = ImageChops.difference(img, recompressed)
            extrema = diff.getextrema()
            mean_diff = sum((lo+hi)/2 for lo,hi in extrema)/3
            findings.append({"title":"JPEG recompression difference (ELA-style screening)", "detail":f"Mean channel range midpoint: {mean_diff:.2f}", "status":"Heuristic only"})
    except Exception as e:
        findings.append({"title":"Visual inspection", "detail":f"Could not process image: {e}", "status":"Unavailable"})
    return findings

def compare_docs(docs):
    discrepancies = []
    keys = ["name","date_of_birth","document_id","address","amount","email"]
    for key in keys:
        vals = [(d["name"], d["fields"].get(key)) for d in docs if d["fields"].get(key)]
        if len(vals) > 1:
            normalized = {v.lower().strip() for _,v in vals}
            if len(normalized) > 1:
                discrepancies.append({"field":key, "values":vals, "severity":"Review required",
                                       "explanation":f"The extracted {key.replace('_',' ')} differs across submitted files."})
    return discrepancies

def make_report_payload(docs, discrepancies):
    return {
        "product":"DOCUSHIELD AI",
        "team":"HACKNCODE",
        "generated_at":datetime.now().isoformat(timespec="seconds"),
        "notice":"Synthetic/demo analysis. Findings are indicators for human review, not proof of fraud.",
        "documents":[{"name":d["name"],"sha256":d["hash"],"fields":d["fields"],"pages":len(d["pages"])} for d in docs],
        "discrepancies":discrepancies
    }

# ---------- Styling ----------
st.markdown("""
<style>
.stApp {background: linear-gradient(135deg,#071426 0%,#0b1d33 55%,#101d35 100%); color:#edf4ff;}
.block-container {padding-top:1.5rem; max-width:1450px;}
h1,h2,h3 {color:#f5f8ff !important;}
div[data-testid="stMetric"] {background:#102844;border:1px solid #244768;padding:16px;border-radius:14px;}
div[data-testid="stFileUploader"] {background:#10233b;border:1px dashed #3973a5;border-radius:14px;padding:10px;}
.card {background:#10243c;border:1px solid #244563;border-radius:16px;padding:18px;margin:8px 0;}
.small {color:#a9bfd7;font-size:0.9rem;}
</style>
""", unsafe_allow_html=True)

if "results" not in st.session_state:
    st.session_state.results = []

st.markdown("## 🛡️ DOCUSHIELD AI")
st.caption("AI-Powered Document Forensics & Contextual Intelligence | HACKNCODE")
st.markdown('<div class="card"><b>Investigate beyond OCR.</b><br><span class="small">Extract structured data, compare related records, inspect visual indicators, and preserve traceable evidence for human review.</span></div>', unsafe_allow_html=True)

with st.sidebar:
    st.title("HACKNCODE")
    st.caption("DataOps Innovation Hackathon 2026")
    st.markdown("---")
    st.markdown("**Investigation controls**")
    st.info("Use only synthetic or explicitly authorized documents.")
    st.markdown("**Analysis status**")
    st.write("🟢 Local processing")
    st.write("🟡 Findings require human review")
    st.markdown("---")
    st.caption("Prototype build · v1.0")

tab1, tab2, tab3, tab4 = st.tabs(["📂 New Investigation","🔎 Findings & Correlation","📑 Investigation Dossier","ℹ️ Methodology & Limits"])

with tab1:
    st.subheader("1. Submit documents")
    files = st.file_uploader("Upload PDF, PNG or JPG documents", type=["pdf","png","jpg","jpeg"], accept_multiple_files=True)
    if st.button("Analyze submitted documents", type="primary", disabled=not files):
        new_docs = []
        for f in files:
            data = f.getvalue()
            item = {"name":f.name,"hash":sha256_bytes(data),"fields":{},"pages":[],"visual":[],"text":""}
            if f.name.lower().endswith(".pdf"):
                item["pages"] = extract_pdf_text(data)
                item["text"] = "\n".join(p["text"] for p in item["pages"])
                item["source"] = "Embedded PDF text extraction (PyMuPDF)"
            else:
                txt, engine = extract_image_text(data)
                item["text"] = txt
                item["pages"] = [{"page":1,"text":txt}]
                item["source"] = engine
                item["visual"] = visual_checks(data, f.name)
            item["fields"] = fields_from_text(item["text"])
            new_docs.append(item)
        st.session_state.results = new_docs
        st.success(f"Processed {len(new_docs)} document(s). Review extracted values and limitations below.")
    if st.session_state.results:
        for d in st.session_state.results:
            with st.expander(f"📄 {d['name']}"):
                st.caption(f"SHA-256: {d['hash']}")
                st.write("Extraction method:", d.get("source","PDF text layer"))
                st.json(d["fields"] if d["fields"] else {"notice":"No supported fields detected. OCR may be required for scanned PDFs."})
                if d["visual"]:
                    st.write("Visual screening")
                    st.json(d["visual"])
                st.text_area("Extracted text preview", d["text"][:5000], height=130, key="txt_"+d["hash"])

with tab2:
    st.subheader("2. Contextual analysis & cross-document correlation")
    docs = st.session_state.results
    if not docs:
        st.info("Upload and analyze at least two related documents to see cross-document comparisons.")
    else:
        a,b,c = st.columns(3)
        a.metric("Documents analyzed",len(docs))
        b.metric("Fields extracted",sum(len(d["fields"]) for d in docs))
        discrepancies = compare_docs(docs)
        c.metric("Discrepancies flagged",len(discrepancies))
        if discrepancies:
            for x in discrepancies:
                st.warning(f"**{x['field'].replace('_',' ').title()}** — {x['explanation']}")
                for fn,val in x["values"]:
                    st.write(f"• {fn}: `{val}`")
                st.caption("Status: Review required · Not a fraud determination")
        else:
            st.success("No cross-document conflicts were found among the supported extracted fields. This does not establish authenticity.")
        st.markdown("#### Evidence register")
        for d in docs:
            st.markdown(f"- **{d['name']}** · SHA-256 `{d['hash'][:16]}…` · {len(d['pages'])} page(s)")
        st.markdown("#### Next investigation steps")
        st.write("1. Verify flagged values against original issuing sources.")
        st.write("2. Inspect the original page/region; OCR output may contain errors.")
        st.write("3. Record analyst decision and supporting evidence before any consequential action.")

with tab3:
    st.subheader("3. Generate investigation dossier")
    docs = st.session_state.results
    if not docs:
        st.info("Analyze documents first.")
    else:
        discrepancies = compare_docs(docs)
        payload = make_report_payload(docs, discrepancies)
        st.json(payload)
        st.download_button("⬇️ Download dossier JSON", json.dumps(payload,indent=2), "docushield_investigation_dossier.json", "application/json")
        report_text = ["DOCUSHIELD AI — INVESTIGATION DOSSIER","Team: HACKNCODE",f"Generated: {payload['generated_at']}","",
                       "IMPORTANT: Indicators for human review only. Not a finding of fraud.","",
                       "DOCUMENTS"]
        for d in docs:
            report_text += [f"- {d['name']} | SHA-256: {d['hash']}",f"  Extracted fields: {json.dumps(d['fields'],ensure_ascii=False)}"]
        report_text += ["","CROSS-DOCUMENT DISCREPANCIES"]
        if discrepancies:
            for x in discrepancies:
                report_text.append(f"- {x['field']}: "+ "; ".join(f"{n}={v}" for n,v in x["values"]))
        else:
            report_text.append("- No supported-field discrepancy detected.")
        report_text += ["","LIMITATIONS","- OCR and pattern extraction may be incomplete or inaccurate.",
                        "- Visual screening is heuristic and cannot prove tampering.",
                        "- A human analyst must verify original evidence and context."]
        st.download_button("⬇️ Download readable dossier (TXT)", "\n".join(report_text), "docushield_investigation_dossier.txt", "text/plain")

with tab4:
    st.subheader("Methodology, safety & limitations")
    st.markdown("""
**Pipeline**
1. Document ingestion and hashing.
2. PDF text extraction; optional OCR for image uploads when Tesseract is installed.
3. Supported-field extraction into a structured schema.
4. Cross-document comparison of extracted values.
5. Basic image metadata/dimensions and JPEG recompression screening.
6. Evidence register and downloadable dossier.

**Safety boundary**
- Use only synthetic or explicitly authorized documents.
- The system does not decide that a document is fraudulent.
- Active or consequential decisions require qualified human review.
- Hashes provide integrity identifiers for the uploaded bytes; they do not establish document authenticity.

**Known prototype limitations**
- OCR for scanned PDFs is not enabled in this build; convert pages to images or use image uploads with Tesseract installed.
- Field extraction uses transparent regular expressions, not a trained document-understanding model.
- Visual checks are screening heuristics, not definitive image-forensics tests.
- Signature authenticity, issuer verification, and cryptographic document validation are not implemented.
- The app runs locally and does not send documents to a cloud AI provider.
""")
    st.caption("Standards referenced for design context: ISO/IEC 27037, ISO/IEC 27042, NIST SP 800-86. This prototype does not claim formal compliance.")
