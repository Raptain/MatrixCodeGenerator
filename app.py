from flask import Flask, render_template, request, send_file, jsonify
import segno
import qrcode
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import os
import uuid
import json
from datetime import datetime
import hashlib
from io import BytesIO
import base64
import traceback
import re

app = Flask(__name__)
app.config['OUTPUT_FOLDER'] = 'output'
app.config['HISTORY_FOLDER'] = 'history'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Создаем папки
for folder in [app.config['OUTPUT_FOLDER'], app.config['HISTORY_FOLDER'], 'static/logos', 'static/patterns']:
    os.makedirs(folder, exist_ok=True)

def hex_to_rgb(hex_color):
    """Конвертация HEX в RGB"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def apply_gradient(img, color1, color2, gradient_type='linear'):
    """Применение градиента к изображению"""
    width, height = img.size
    img_array = np.array(img)
    
    if gradient_type == 'linear':
        for y in range(height):
            ratio = y / height
            r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
            g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
            b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
            for x in range(width):
                if img_array[y, x, 0] < 128:
                    img_array[y, x] = [r, g, b]
    elif gradient_type == 'radial':
        center_x, center_y = width // 2, height // 2
        max_dist = ((center_x ** 2 + center_y ** 2) ** 0.5)
        for y in range(height):
            for x in range(width):
                dist = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
                ratio = min(1.0, dist / max_dist)
                r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
                g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
                b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
                if img_array[y, x, 0] < 128:
                    img_array[y, x] = [r, g, b]
    
    return Image.fromarray(img_array)

def apply_texture(img, texture_type='dots'):
    """Применение текстуры"""
    width, height = img.size
    img_array = np.array(img)
    
    if texture_type == 'dots':
        spacing = 4
        for y in range(0, height, spacing):
            for x in range(0, width, spacing):
                if img_array[y, x, 0] < 128:
                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            if 0 <= y+dy < height and 0 <= x+dx < width:
                                img_array[y+dy, x+dx] = [255, 255, 255]
    elif texture_type == 'lines':
        for y in range(0, height, 3):
            for x in range(width):
                if img_array[y, x, 0] < 128:
                    img_array[y, x] = [200, 200, 200]
    
    return Image.fromarray(img_array)

def reshape_code(img, shape='circle'):
    """Изменение формы кода"""
    width, height = img.size
    mask = Image.new('L', (width, height), 0)
    draw = ImageDraw.Draw(mask)
    
    if shape == 'circle':
        draw.ellipse([(0, 0), (width, height)], fill=255)
    elif shape == 'heart':
        points = []
        for t in range(0, 360, 5):
            rad = t * 3.14159 / 180
            x = 16 * np.sin(rad) ** 3
            y = 13 * np.cos(rad) - 5 * np.cos(2*rad) - 2*np.cos(3*rad) - np.cos(4*rad)
            x = (x + 16) * width / 32
            y = (y + 13) * height / 26
            points.append((x, y))
        draw.polygon(points, fill=255)
    elif shape == 'rounded':
        draw.rounded_rectangle([(0, 0), (width, height)], radius=width//4, fill=255)
    else:
        draw.rectangle([(0, 0), (width, height)], fill=255)
    
    output = Image.new('RGB', (width, height), (255, 255, 255))
    output.paste(img, mask=mask)
    return output

def generate_code_internal(params):
    """Внутренняя функция генерации кода"""
    try:
        code_type = params.get('code_type', 'qr')
        data = params.get('data', '')
        size = int(params.get('size', 10))
        border = int(params.get('border', 1))
        foreground = params.get('foreground', '#000000')
        background = params.get('background', '#ffffff')
        
        # Генерация базового кода
        if code_type == 'qr':
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=size,
                border=border,
            )
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color=foreground, back_color=background).convert('RGB')
        else:
            # Для Data Matrix, Aztec используем segno
            segno_code = segno.make(data, error='h')
            img = segno_code.to_pil(scale=size, border=border).convert('RGB')
            # Замена цветов
            fg_rgb = hex_to_rgb(foreground)
            bg_rgb = hex_to_rgb(background)
            pixels = img.load()
            for y in range(img.height):
                for x in range(img.width):
                    r, g, b = pixels[x, y]
                    if (r + g + b) < 384:
                        pixels[x, y] = fg_rgb
                    else:
                        pixels[x, y] = bg_rgb
        
        # Применение градиента
        if params.get('gradient_type') != 'none':
            gradient_type = params.get('gradient_type', 'linear')
            gradient_color2 = params.get('gradient_color2', '#667eea')
            fg_rgb = hex_to_rgb(foreground)
            grad2_rgb = hex_to_rgb(gradient_color2)
            img = apply_gradient(img, fg_rgb, grad2_rgb, gradient_type)
        
        # Применение текстуры
        if params.get('texture_type') != 'none':
            img = apply_texture(img, params.get('texture_type'))
        
        # Изменение формы
        if params.get('code_shape') != 'square':
            img = reshape_code(img, params.get('code_shape'))
        
        # Добавление логотипа
        if params.get('add_logo') and os.path.exists('static/logos/default.png'):
            logo = Image.open('static/logos/default.png')
            logo_size = int(params.get('logo_size', 20))
            logo = logo.resize((logo_size, logo_size))
            img_width, img_height = img.size
            pos_x = (img_width - logo_size) // 2
            pos_y = (img_height - logo_size) // 2
            img.paste(logo, (pos_x, pos_y), logo if logo.mode == 'RGBA' else None)
        
        # Сохранение
        filename = f"{uuid.uuid4().hex}.png"
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        img.save(filepath, 'PNG')
        
        return {
            'success': True,
            'filename': filename,
            'image_url': f'/output/{filename}',
            'download_url': f'/download/{filename}'
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def process_data_input(data_type, data_value):
    """Обработка различных типов данных"""
    if data_type == 'url':
        return data_value
    elif data_type == 'contact':
        return f"BEGIN:VCARD\nVERSION:3.0\nFN:{data_value.get('name', '')}\nTEL:{data_value.get('phone', '')}\nEMAIL:{data_value.get('email', '')}\nEND:VCARD"
    elif data_type == 'sms':
        return f"SMSTO:{data_value.get('number', '')}:{data_value.get('message', '')}"
    elif data_type == 'email':
        return f"mailto:{data_value.get('email', '')}?subject={data_value.get('subject', '')}&body={data_value.get('body', '')}"
    elif data_type == 'wifi':
        return f"WIFI:T:{data_value.get('encryption', 'WPA')};S:{data_value.get('ssid', '')};P:{data_value.get('password', '')};;"
    else:
        return data_value

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        code_type = request.form.get('code_type', 'qr')
        data_type = request.form.get('data_type', 'text')
        
        # Сбор данных в зависимости от типа
        if data_type == 'contact':
            data_params = {
                'name': request.form.get('contact_name', ''),
                'phone': request.form.get('contact_phone', ''),
                'email': request.form.get('contact_email', '')
            }
            data = process_data_input(data_type, data_params)
        elif data_type == 'sms':
            data_params = {
                'number': request.form.get('sms_number', ''),
                'message': request.form.get('sms_message', '')
            }
            data = process_data_input(data_type, data_params)
        elif data_type == 'email':
            data_params = {
                'email': request.form.get('email_address', ''),
                'subject': request.form.get('email_subject', ''),
                'body': request.form.get('email_body', '')
            }
            data = process_data_input(data_type, data_params)
        elif data_type == 'wifi':
            data_params = {
                'ssid': request.form.get('wifi_ssid', ''),
                'password': request.form.get('wifi_password', ''),
                'encryption': request.form.get('wifi_encryption', 'WPA')
            }
            data = process_data_input(data_type, data_params)
        else:
            data = request.form.get('data_text', '')
        
        if not data:
            return jsonify({'error': 'Введите данные для кодирования'}), 400
        
        params = {
            'code_type': code_type,
            'data': data,
            'size': int(request.form.get('size', 10)),
            'border': int(request.form.get('border', 1)),
            'foreground': request.form.get('foreground', '#000000'),
            'background': request.form.get('background', '#ffffff'),
            'eye_style': request.form.get('eye_style', 'square'),
            'gradient_type': request.form.get('gradient_type', 'none'),
            'gradient_color2': request.form.get('gradient_color2', '#667eea'),
            'texture_type': request.form.get('texture_type', 'none'),
            'code_shape': request.form.get('code_shape', 'square'),
            'add_logo': request.form.get('add_logo') == 'true',
            'logo_size': int(request.form.get('logo_size', 20)),
            'logo_position': request.form.get('logo_position', 'center')
        }
        
        result = generate_code_internal(params)
        
        if result['success']:
            # Сохранение в историю
            history_id = hashlib.md5(f"{data}{datetime.now()}".encode()).hexdigest()
            history_entry = {
                'id': history_id,
                'type': code_type,
                'data_type': data_type,
                'data': data[:100],
                'filename': result['filename'],
                'created_at': datetime.now().isoformat(),
                'tags': request.form.get('tags', '').split(',')
            }
            with open(os.path.join(app.config['HISTORY_FOLDER'], f"{history_id}.json"), 'w') as f:
                json.dump(history_entry, f)
            
            return jsonify({
                'success': True,
                'filename': result['filename'],
                'image_url': result['image_url'],
                'history_id': history_id
            })
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/export/<filename>.<format>')
def export_code(filename, format):
    """Экспорт в различные форматы"""
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    
    if format.lower() == 'png':
        return send_file(filepath, mimetype='image/png')
    elif format.lower() == 'svg':
        svg_path = filepath.replace('.png', '.svg')
        from svgwrite import Drawing
        img = Image.open(filepath)
        dwg = Drawing(svg_path, size=(img.width, img.height))
        dwg.add(dwg.image(href=filepath, insert=(0, 0), size=(img.width, img.height)))
        dwg.save()
        return send_file(svg_path, mimetype='image/svg+xml')
    elif format.lower() == 'pdf':
        from reportlab.pdfgen import canvas
        pdf_path = filepath.replace('.png', '.pdf')
        c = canvas.Canvas(pdf_path, pagesize=(img.width, img.height))
        c.drawImage(filepath, 0, 0, width=img.width, height=img.height)
        c.save()
        return send_file(pdf_path, mimetype='application/pdf')
    
    return jsonify({'error': 'Unsupported format'}), 400

@app.route('/history')
def get_history():
    """Получение истории кодов"""
    history_list = []
    for file in os.listdir(app.config['HISTORY_FOLDER']):
        if file.endswith('.json'):
            with open(os.path.join(app.config['HISTORY_FOLDER'], file), 'r') as f:
                history_list.append(json.load(f))
    return jsonify(sorted(history_list, key=lambda x: x['created_at'], reverse=True))

@app.route('/output/<filename>')
def output_file(filename):
    return send_file(os.path.join(app.config['OUTPUT_FOLDER'], filename))

@app.route('/download/<filename>')
def download(filename):
    return send_file(
        os.path.join(app.config['OUTPUT_FOLDER'], filename),
        as_attachment=True,
        download_name='matrix_code.png'
    )

@app.route('/iframe')
def iframe_embed():
    return render_template('iframe.html')

@app.route('/api/generate', methods=['POST'])
def api_generate():
    """API endpoint для встраивания"""
    try:
        data = request.json
        params = {
            'code_type': data.get('code_type', 'qr'),
            'data': data.get('data', ''),
            'size': data.get('size', 10),
            'border': data.get('border', 1),
            'foreground': data.get('foreground', '#000000'),
            'background': data.get('background', '#ffffff'),
            'gradient_type': 'none',
            'texture_type': 'none',
            'code_shape': 'square',
            'add_logo': False
        }
        result = generate_code_internal(params)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 ПРОДВИНУТЫЙ ГЕНЕРАТОР МАТРИЧНЫХ КОДОВ")
    print("=" * 60)
    print(f"📱 Откройте в браузере: http://localhost:5000")
    print(f"🔌 API endpoint: http://localhost:5000/api/generate")
    print(f"📊 История: http://localhost:5000/history")
    print("=" * 60)
    app.run(debug=True, host='localhost', port=5000, use_reloader=False)