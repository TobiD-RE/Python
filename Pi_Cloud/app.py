from flask import Flask, render_template, request, jsonify, send_file, render_template_string
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename
import mimetypes
from pathlib import Path

app = Flask(__name__)

UPLOAD_FOLDER = ''
MAX_FILE_SIZE = 2048 * 1024 *1024
ALLOWED_EXTEMSIONS = {'txt', 'pdf', 'jpg', 'jpeg', 'gif', 'mp4', 'mp3', 'doc', 'docx', 'zip', '7z', 'heic'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTEMSIONS

def get_file_info(filepath):
    stat = os.stat(filepath)
    return {
        'name': os.path.basename(filepath),
        'filesize': stat.st_size,
        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
        'type': mimetypes.guess_type(filepath)[0] or 'unknown'
    }

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'Nofile provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'File type not allowed'}), 400
        
        filename = secure_filename(file.filename)

        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        counter = 1
        original_filepath = filepath
        while os.path.exists(filepath):
            name, ext = os.path.splitext(original_filepath)
            filepath = f"{name}_{counter}{ext}"
            counter += 1

        file.save(filepath)

        return jsonify({
            'success': True,
            'message': 'File uploaded successfully',
            'filename': os.path.basename(filepath)
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/files', methods=['GET'])
def list_files():
    try:
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            return jsonify({'files': []})
        
        files = []
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(filepath):
                files.append(get_file_info(filepath))

        files.sort(key=lambda x: x['modified'], reverse=True)

        return jsonify({'files': files})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    print(f"Access via: http://pi-ip:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)