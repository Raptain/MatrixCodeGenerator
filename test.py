import segno
from PIL import Image

# Тест генерации
try:
    qr = segno.make('https://example.com', error='h')
    img = qr.to_pil(scale=10, border=1)
    img.save('test_output.png')
    print("✅ Тест успешен! Изображение сохранено как test_output.png")
except Exception as e:
    print(f"❌ Ошибка: {e}")