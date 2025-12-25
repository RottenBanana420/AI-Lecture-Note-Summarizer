# Troubleshooting Guide

This guide helps you diagnose and resolve common issues when working with the PDF processing API.

## Table of Contents

- [Upload Errors](#upload-errors)
- [PDF Compatibility Issues](#pdf-compatibility-issues)
- [Performance Problems](#performance-problems)
- [Debugging Steps](#debugging-steps)
- [Common Pitfalls](#common-pitfalls)
- [Log Locations](#log-locations)

## Upload Errors

### Error: "Invalid file type"

**Symptom:**

```json
{
  "detail": "Invalid file type. Allowed types: application/pdf"
}
```

**Causes:**

1. File is not a PDF
2. File extension is `.pdf` but content is not PDF
3. MIME type not set correctly in request

**Solutions:**

```bash
# Check actual file type
file document.pdf
# Should output: document.pdf: PDF document, version 1.X

# Verify MIME type in request
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf;type=application/pdf"
```

---

### Error: "File size exceeds maximum allowed size"

**Symptom:**

```json
{
  "detail": "File size exceeds maximum allowed size of 50MB"
}
```

**Solutions:**

1. **Compress the PDF:**

   ```bash
   # Using Ghostscript
   gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 \
      -dPDFSETTINGS=/ebook -dNOPAUSE -dQUIET -dBATCH \
      -sOutputFile=compressed.pdf input.pdf
   ```

2. **Split large PDFs:**

   ```python
   import PyPDF2
   
   def split_pdf(input_path, output_prefix, pages_per_file=50):
       with open(input_path, 'rb') as file:
           pdf = PyPDF2.PdfReader(file)
           total_pages = len(pdf.pages)
           
           for i in range(0, total_pages, pages_per_file):
               writer = PyPDF2.PdfWriter()
               end = min(i + pages_per_file, total_pages)
               
               for page_num in range(i, end):
                   writer.add_page(pdf.pages[page_num])
               
               output_path = f"{output_prefix}_part{i//pages_per_file + 1}.pdf"
               with open(output_path, 'wb') as output_file:
                   writer.write(output_file)
   ```

3. **Increase server limit** (if you control the server):

   ```bash
   # In .env file
   MAX_UPLOAD_SIZE=104857600  # 100MB
   ```

---

### Error: "PDF validation failed: File is encrypted"

**Symptom:**

```json
{
  "detail": "PDF validation failed: File is encrypted and cannot be processed"
}
```

**Solutions:**

1. **Remove encryption using PyPDF2:**

   ```python
   import PyPDF2
   
   def decrypt_pdf(input_path, output_path, password=''):
       with open(input_path, 'rb') as file:
           pdf = PyPDF2.PdfReader(file)
           
           if pdf.is_encrypted:
               pdf.decrypt(password)
           
           writer = PyPDF2.PdfWriter()
           for page in pdf.pages:
               writer.add_page(page)
           
           with open(output_path, 'wb') as output_file:
               writer.write(output_file)
   ```

2. **Use qpdf command-line tool:**

   ```bash
   # Remove password protection
   qpdf --password=PASSWORD --decrypt input.pdf output.pdf
   ```

3. **Use online tools** (for non-sensitive documents):
   - iLovePDF
   - SmallPDF
   - PDF2Go

---

### Error: "PDF validation failed: File is corrupted"

**Symptom:**

```json
{
  "detail": "PDF validation failed: Cannot open PDF file"
}
```

**Solutions:**

1. **Verify file integrity:**

   ```bash
   # Check if file is complete
   pdfinfo document.pdf
   ```

2. **Repair PDF:**

   ```bash
   # Using Ghostscript to repair
   gs -o repaired.pdf -sDEVICE=pdfwrite -dPDFSETTINGS=/prepress input.pdf
   ```

3. **Re-download or re-export:**
   - If downloaded from web, try downloading again
   - If exported from application, try exporting again

---

### Error: "File is empty"

**Symptom:**

```json
{
  "detail": "File is empty"
}
```

**Solutions:**

1. **Check file size:**

   ```bash
   ls -lh document.pdf
   # Should show size > 0
   ```

2. **Verify file content:**

   ```bash
   head -c 100 document.pdf
   # Should start with %PDF-
   ```

3. **Check upload code:**

   ```python
   # Ensure file is opened in binary mode
   with open('document.pdf', 'rb') as f:  # Note: 'rb' not 'r'
       files = {'file': f}
       response = requests.post(url, files=files)
   ```

## PDF Compatibility Issues

### Scanned PDFs (Image-Only)

**Symptom:**

- Upload succeeds but chunks contain no text
- `chunk_count` is 0 or very low

**Detection:**

```python
import PyPDF2

def is_scanned_pdf(file_path):
    with open(file_path, 'rb') as f:
        pdf = PyPDF2.PdfReader(f)
        
        # Check first few pages for text
        for page_num in range(min(3, len(pdf.pages))):
            text = pdf.pages[page_num].extract_text()
            if len(text.strip()) > 100:
                return False  # Has text, not scanned
        
        return True  # Likely scanned
```

**Solutions:**

1. **Use OCR to convert to searchable PDF:**

   ```bash
   # Using ocrmypdf
   ocrmypdf input.pdf output.pdf
   ```

2. **Use online OCR services:**
   - Adobe Acrobat DC
   - ABBYY FineReader
   - Google Drive (upload → Open with Google Docs → Download as PDF)

---

### Multi-Language PDFs

**Symptom:**

- Non-English text appears garbled
- Special characters missing or incorrect

**Solutions:**

1. **Ensure PDF uses Unicode encoding:**
   - Re-export PDF with Unicode font embedding
   - Use "Save As" with "Optimize for compatibility" option

2. **Check SpaCy language model:**

   ```python
   # For non-English text, use appropriate model
   # Current: en_core_web_sm (English only)
   # For other languages, install appropriate model:
   # python -m spacy download de_core_news_sm  # German
   # python -m spacy download fr_core_news_sm  # French
   ```

---

### Complex Layouts

**Symptom:**

- Text extraction order is incorrect
- Multi-column text is jumbled

**Explanation:**

- PyMuPDF extracts text in reading order
- Complex layouts may not extract in expected order

**Workarounds:**

1. **Simplify PDF layout before upload:**
   - Convert multi-column to single column
   - Export as "Simple Layout" if possible

2. **Accept extraction order:**
   - Chunking algorithm handles text as-is
   - Semantic search still works despite order issues

## Performance Problems

### Slow Upload Processing

**Symptom:**

- Upload takes longer than expected
- Timeouts on large files

**Diagnosis:**

```python
import time
import requests

def time_upload(file_path):
    start = time.time()
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(url, files=files)
    
    duration = time.time() - start
    print(f"Upload took {duration:.2f} seconds")
    
    return response
```

**Solutions:**

1. **Increase timeout:**

   ```python
   response = requests.post(url, files=files, timeout=60)  # 60 seconds
   ```

2. **Check file size:**

   ```python
   import os
   size_mb = os.path.getsize(file_path) / (1024 * 1024)
   print(f"File size: {size_mb:.1f} MB")
   # Expect ~1 second per 20 pages, adjust for file size
   ```

3. **Monitor server resources:**

   ```bash
   # Check server CPU and memory
   top
   # Check disk I/O
   iostat -x 1
   ```

---

### High Memory Usage

**Symptom:**

- Server runs out of memory
- OOM (Out of Memory) errors

**Solutions:**

1. **Reduce concurrent uploads:**

   ```python
   # Limit concurrent requests
   with ThreadPoolExecutor(max_workers=5) as executor:  # Reduced from 20
       futures = [executor.submit(upload_pdf, f) for f in files]
   ```

2. **Increase server memory:**
   - Add more RAM to server
   - Use swap space (temporary solution)

3. **Process files sequentially:**

   ```python
   # Instead of concurrent uploads
   for file_path in files:
       upload_pdf(file_path)
       time.sleep(0.5)  # Brief pause between uploads
   ```

---

### Database Connection Errors

**Symptom:**

```
OperationalError: connection pool exhausted
```

**Solutions:**

1. **Reduce concurrent uploads:**
   - Each upload holds a database connection
   - Limit to 10-20 concurrent uploads

2. **Increase connection pool size:**

   ```python
   # In database.py
   engine = create_engine(
       DATABASE_URL,
       pool_size=20,  # Increased from 10
       max_overflow=10
   )
   ```

3. **Check for connection leaks:**

   ```bash
   # Monitor active connections
   psql -U postgres -d lecture_summarizer -c \
     "SELECT count(*) FROM pg_stat_activity;"
   ```

## Debugging Steps

### 1. Enable Debug Logging

```python
import logging

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Make request
response = upload_pdf('document.pdf')
```

### 2. Inspect Request/Response

```python
import requests

response = requests.post(url, files=files, data=data)

print(f"Status Code: {response.status_code}")
print(f"Headers: {response.headers}")
print(f"Response: {response.text}")
```

### 3. Validate PDF Locally

```python
import PyPDF2

def validate_pdf(file_path):
    """Comprehensive PDF validation."""
    try:
        with open(file_path, 'rb') as f:
            # Check magic bytes
            header = f.read(5)
            if header != b'%PDF-':
                print("❌ Not a valid PDF (magic bytes)")
                return False
            
            # Try to open with PyPDF2
            f.seek(0)
            pdf = PyPDF2.PdfReader(f)
            
            # Check encryption
            if pdf.is_encrypted:
                print("❌ PDF is encrypted")
                return False
            
            # Check page count
            page_count = len(pdf.pages)
            print(f"✓ PDF has {page_count} pages")
            
            # Try to extract text from first page
            text = pdf.pages[0].extract_text()
            if len(text.strip()) == 0:
                print("⚠️  Warning: First page has no text (may be scanned)")
            else:
                print(f"✓ First page has {len(text)} characters")
            
            return True
            
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False

# Usage
validate_pdf('document.pdf')
```

### 4. Test with Minimal Example

```python
# Minimal upload test
import requests

url = "http://localhost:8000/api/v1/documents/upload"

# Create a simple test PDF
from reportlab.pdfgen import canvas

def create_test_pdf(filename='test.pdf'):
    c = canvas.Canvas(filename)
    c.drawString(100, 750, "Test PDF Document")
    c.drawString(100, 730, "This is a test.")
    c.save()

create_test_pdf()

# Upload test PDF
with open('test.pdf', 'rb') as f:
    files = {'file': f}
    response = requests.post(url, files=files)
    print(response.json())
```

### 5. Check Server Logs

```bash
# View FastAPI logs
tail -f /var/log/fastapi/app.log

# Or if running with uvicorn
# Logs appear in terminal where uvicorn is running
```

## Common Pitfalls

### 1. File Not Closed After Upload

**Problem:**

```python
# Bad: File handle not closed
f = open('document.pdf', 'rb')
files = {'file': f}
response = requests.post(url, files=files)
# File still open!
```

**Solution:**

```python
# Good: Use context manager
with open('document.pdf', 'rb') as f:
    files = {'file': f}
    response = requests.post(url, files=files)
# File automatically closed
```

---

### 2. Incorrect Content-Type

**Problem:**

```python
# Bad: Wrong content type
headers = {'Content-Type': 'application/json'}  # Wrong!
response = requests.post(url, files=files, headers=headers)
```

**Solution:**

```python
# Good: Let requests set Content-Type automatically
response = requests.post(url, files=files)
# Or explicitly set multipart/form-data (requests does this)
```

---

### 3. Reading File Multiple Times

**Problem:**

```python
# Bad: File pointer at end after first read
content = f.read()
files = {'file': f}  # File pointer at EOF
response = requests.post(url, files=files)  # Uploads empty file!
```

**Solution:**

```python
# Good: Seek back to start or don't read beforehand
f.seek(0)  # Reset file pointer
files = {'file': f}
response = requests.post(url, files=files)
```

---

### 4. Not Handling Errors

**Problem:**

```python
# Bad: No error handling
response = requests.post(url, files=files)
result = response.json()  # May fail if status != 200
```

**Solution:**

```python
# Good: Proper error handling
response = requests.post(url, files=files)
if response.status_code == 201:
    result = response.json()
    print(f"Success: {result['id']}")
else:
    print(f"Error {response.status_code}: {response.text}")
```

---

### 5. Uploading Non-PDF Files

**Problem:**

```python
# Bad: Assuming file is PDF without checking
upload_pdf('document.docx')  # Will fail
```

**Solution:**

```python
# Good: Validate file extension
from pathlib import Path

def upload_if_pdf(file_path):
    if Path(file_path).suffix.lower() != '.pdf':
        raise ValueError(f"Not a PDF file: {file_path}")
    return upload_pdf(file_path)
```

## Log Locations

### Application Logs

**Development (console):**

```bash
# Logs appear in terminal where uvicorn is running
uvicorn app.main:app --reload
```

**Production (file):**

```bash
# Check application log file
tail -f /var/log/fastapi/app.log

# Or systemd journal
journalctl -u fastapi -f
```

### Database Logs

```bash
# PostgreSQL logs
tail -f /var/log/postgresql/postgresql-15-main.log

# Or via Docker
docker logs lecture-summarizer-db -f
```

### Nginx/Reverse Proxy Logs

```bash
# Access logs
tail -f /var/log/nginx/access.log

# Error logs
tail -f /var/log/nginx/error.log
```

### What to Look For in Logs

**Upload Success:**

```
INFO: Processing upload: filename=document.pdf, size=2457600 bytes
INFO: Upload completed successfully: document_id=42
```

**Validation Error:**

```
WARNING: PDF validation error: File is encrypted
```

**Processing Error:**

```
ERROR: PDF processing error: Text extraction failed
ERROR: Unexpected error during upload: ...
```

**Database Error:**

```
ERROR: Upload service error: (psycopg2.errors.ForeignKeyViolation) ...
```

---

## Getting Help

If you've tried the solutions above and still have issues:

1. **Check API Documentation:**
   - Swagger UI: <http://localhost:8000/docs>
   - ReDoc: <http://localhost:8000/redoc>

2. **Review Related Documentation:**
   - [API Usage Guide](API_USAGE.md)
   - [Technical Documentation](PDF_PROCESSING.md)
   - [Performance Benchmarks](PERFORMANCE.md)

3. **Collect Diagnostic Information:**
   - Error message and status code
   - PDF file characteristics (size, pages, version)
   - Server logs around time of error
   - Request/response details

4. **Open an Issue:**
   - Provide diagnostic information
   - Include minimal reproduction example
   - Specify environment (OS, Python version, etc.)

---

## Quick Reference

| Error | Status Code | Common Cause | Quick Fix |
|-------|-------------|--------------|-----------|
| Invalid file type | 400 | Not a PDF | Verify file is actually PDF |
| File too large | 413 | > 50MB | Compress or split PDF |
| File encrypted | 400 | Password protected | Remove encryption |
| File corrupted | 400 | Incomplete download | Re-download or repair |
| Empty file | 400 | 0 bytes | Check file upload code |
| Timeout | 504 | Large file/slow network | Increase timeout |
| Connection pool exhausted | 500 | Too many concurrent requests | Reduce concurrency |
| Foreign key violation | 422 | Invalid user_id | Use valid user ID |
