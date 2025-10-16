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

def generate_html_diff(original_text, final_text):
    """Generate HTML showing differences"""
    diff = difflib.HtmlDiff()
    html_diff = diff.make_file(
        original_text.splitlines(),
        final_text.splitlines(),
        fromdesc='Original Version',
        todesc='Final Version',
        context=True,
        numlines=3
    )
    return html_diff

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
