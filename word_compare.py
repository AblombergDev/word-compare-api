from flask import Flask, request, jsonify
from docx import Document
from pypdf import PdfReader
import difflib
from io import BytesIO

app = Flask(__name__)

def extract_text_from_docx(file_bytes):
    """Extract text from a .docx file"""
    doc = Document(BytesIO(file_bytes))
    full_text = [p.text for p in doc.paragraphs]
    return '\n'.join(full_text)

def extract_text_from_pdf(file_bytes):
    """Extract text from a PDF file"""
    pdf = PdfReader(BytesIO(file_bytes))
    text = []
    for page in pdf.pages:
        text.append(page.extract_text() or "")
    return "\n".join(text)

def extract_text(file_storage):
    """Auto-detect file type and extract text accordingly"""
    filename = (file_storage.filename or "").lower()
    content_type = (file_storage.content_type or "").lower()
    file_bytes = file_storage.read()

    if filename.endswith(".docx") or "wordprocessingml.document" in content_type:
        return extract_text_from_docx(file_bytes)
    elif filename.endswith(".pdf") or "pdf" in content_type:
        return extract_text_from_pdf(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {filename or content_type}")

def generate_email_friendly_diff(original_text, final_text):
    """Generate email-friendly inline diff (single column, easy to read)"""
    original_lines = original_text.splitlines()
    final_lines = final_text.splitlines()

    diff = difflib.unified_diff(
        original_lines,
        final_lines,
        lineterm='',
        n=2  # context lines
    )

    html_parts = [
        '<div style="font-family:Arial,sans-serif;font-size:14px;line-height:1.8;max-width:100%;overflow-x:auto;">'
    ]

    change_count = 0
    for line in diff:
        if line.startswith(('---', '+++', '@@')):
            continue

        if line.startswith('-'):
            change_count += 1
            html_parts.append(
                f'<div style="background:#ffcccc;padding:10px;margin:5px 0;border-left:4px solid #cc0000;word-wrap:break-word;"><strong>REMOVED:</strong> {line[1:]}</div>'
            )
        elif line.startswith('+'):
            change_count += 1
            html_parts.append(
                f'<div style="background:#ccffcc;padding:10px;margin:5px 0;border-left:4px solid #00cc00;word-wrap:break-word;"><strong>ADDED:</strong> {line[1:]}</div>'
            )
        elif line.startswith(' '):
            html_parts.append(
                f'<div style="color:#666;padding:5px 10px;word-wrap:break-word;">{line[1:]}</div>'
            )

    if change_count == 0:
        html_parts.append('<p style="color:#666;font-style:italic;">No text changes detected between versions.</p>')

    html_parts.append('</div>')
    return '\n'.join(html_parts)

@app.route('/compare', methods=['POST'])
def compare_documents():
    """Compare two documents (Word or PDF) and return HTML diff"""
    try:
        if 'original' not in request.files or 'final' not in request.files:
            return jsonify({'error': 'Both original and final files required'}), 400

        original_file = request.files['original']
        final_file = request.files['final']

        original_text = extract_text(original_file)
        final_text = extract_text(final_file)

        html_diff = generate_email_friendly_diff(original_text, final_text)

        original_words = len(original_text.split())
        final_words = len(final_text.split())
        word_diff = final_words - original_words

        return jsonify({
            'success': True,
            'html_diff': html_diff,
            'stats': {
                'original_words': original_words,
                'final_words': final_words,
                'word_difference': word_diff
            }
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

@app.route('/', methods=['GET'])
def upload_ui():
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Compare Documents</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 40px; }
    .container { max-width: 640px; margin: 0 auto; }
    label { display: block; margin-top: 16px; font-weight: bold; }
    input[type="file"] { display: block; margin-top: 8px; }
    button { margin-top: 24px; padding: 10px 18px; font-size: 15px; }
    #result { margin-top: 32px; border: 1px solid #ccc; padding: 16px; border-radius: 6px; background: #fafafa; }
  </style>
</head>
<body>
  <div class="container">
    <h2>Ad-hoc Document Compare</h2>
    <p>Upload two files (DOCX or PDF). Results will appear below.</p>
    <form id="compareForm">
      <label for="originalFile">Original document</label>
      <input id="originalFile" name="original" type="file" accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/pdf" required />

      <label for="finalFile">Final document</label>
      <input id="finalFile" name="final" type="file" accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/pdf" required />

      <button type="submit">Compare</button>
    </form>
    <div id="result"></div>
  </div>

  <script>
    const form = document.getElementById('compareForm');
    const resultDiv = document.getElementById('result');

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      resultDiv.innerHTML = '<p>Comparing…</p>';

      const formData = new FormData(form);

      try {
        const response = await fetch('/compare', {
          method: 'POST',
          body: formData
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || 'Compare failed');
        }

        const stats = data.stats || {};
        const meta = `
          <p><strong>Original words:</strong> ${stats.original_words ?? '–'}</p>
          <p><strong>Final words:</strong> ${stats.final_words ?? '–'}</p>
          <p><strong>Difference:</strong> ${stats.word_difference ?? '–'}</p>
        `;

        resultDiv.innerHTML = meta + (data.html_diff || '<p>No diff output.</p>');

      } catch (err) {
        resultDiv.innerHTML = `<p style="color:#b00020;">${err.message}</p>`;
      }
    });
  </script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
