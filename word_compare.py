from flask import Flask, request, jsonify
from docx import Document
import difflib
from io import BytesIO

app = Flask(__name__)

def extract_text_from_docx(file_bytes):
    """Extract text from a .docx file"""
    doc = Document(BytesIO(file_bytes))
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

def generate_email_friendly_diff(original_text, final_text):
    """Generate email-friendly inline diff (single column, easy to read)"""
    original_lines = original_text.splitlines()
    final_lines = final_text.splitlines()

    # Use unified diff to get changes
    diff = difflib.unified_diff(
        original_lines,
        final_lines,
        lineterm='',
        n=2  # context lines
    )

    html_parts = []
    html_parts.append('<div style="font-family:Arial,sans-serif;font-size:14px;line-height:1.8;max-width:100%;overflow-x:auto;">')

    change_count = 0
    for line in diff:
        if line.startswith('---') or line.startswith('+++') or line.startswith('@@'):
            continue  # Skip diff headers

        if line.startswith('-'):
            # Deleted line
            change_count += 1
            html_parts.append(f'<div style="background:#ffcccc;padding:10px;margin:5px 0;border-left:4px solid #cc0000;word-wrap:break-word;"><strong>REMOVED:</strong> {line[1:]}</div>')
        elif line.startswith('+'):
            # Added line
            change_count += 1
            html_parts.append(f'<div style="background:#ccffcc;padding:10px;margin:5px 0;border-left:4px solid #00cc00;word-wrap:break-word;"><strong>ADDED:</strong> {line[1:]}</div>')
        elif line.startswith(' '):
            # Unchanged context line
            html_parts.append(f'<div style="color:#666;padding:5px 10px;word-wrap:break-word;">{line[1:]}</div>')

    if change_count == 0:
        html_parts.append('<p style="color:#666;font-style:italic;">No text changes detected between versions.</p>')

    html_parts.append('</div>')

    return '\n'.join(html_parts)

def generate_html_diff(original_text, final_text):
    """Generate HTML showing differences"""
    # Use the email-friendly version instead
    return generate_email_friendly_diff(original_text, final_text)

@app.route('/compare', methods=['POST'])
def compare_documents():
    """Compare two Word documents and return HTML diff"""
    try:
        # Get files from request
        if 'original' not in request.files or 'final' not in request.files:
            return jsonify({'error': 'Both original and final files required'}), 400

        original_file = request.files['original']
        final_file = request.files['final']

        # Extract text from both documents
        original_text = extract_text_from_docx(original_file.read())
        final_text = extract_text_from_docx(final_file.read())

        # Generate HTML diff
        html_diff = generate_html_diff(original_text, final_text)

        # Count changes
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

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
