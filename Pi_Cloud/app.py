from flask import Flask, render_template, request, jsonify, send_file
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename
import mimetypes

app = Flask(__name__)

UPLOAD_FOLDER = ''
MAX_FILE_SIZE = 2048 * 1024 *1024
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'jpg', 'jpeg', 'gif', 'mp4', 'mp3', 'doc', 'docx', 'zip', '7z', 'heic'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

CUSTOM_MIME_TYPES = {
    '.heic': 'image/heic',
    ' docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.7z': 'application/x-7z-compressed'
}

def get_mime_type(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    return CUSTOM_MIME_TYPES.get(ext, mimetypes.guess_type(filepath)[0] or 'unknown')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_info(filepath):
    stat = os.stat(filepath)
    return {
        'name': os.path.basename(filepath),
        'filesize': stat.st_size,
        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
        'type': mimetypes.guess_type(filepath)
    }

@app.errorhandler(413)
def file_too_big(error):
    return jsonify({'success': False, 'error': 'File too big'}), 413

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
        original_filepath = filepath
        counter = 1
        
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
            if allowed_file(filename):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if os.path.isfile(filepath):
                    files.append(get_file_info(filepath))

        files.sort(key=lambda x: x['modified'], reverse=True)

        return jsonify({'files': files})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/download/<filename>')
def download_file(filename):
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))

        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(filepath, as_attachment=True)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))

        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        os.remove(filepath)
        return jsonify({'success': True, 'message': 'File deleted successfully'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/health')
def health_check():
    disk_usage = os.statvfs(app.config['UPLOAD_FOLDER'])
    free_space = disk_usage.f_frsize * disk_usage.f_bavail

    return jsonify({
        'status': 'healthy',
        'free_space_gb': round(free_space / (1024**3), 2),
        'upload_folder': app.config['UPLOAD_FOLDER']
    })    


if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    print(f"Access via: http://pi-ip:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)