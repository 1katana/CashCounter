from PIL import Image, ImageDraw, ImageFont
import math
import os

def add_watermark(input_image_path, 
                 output_image_path, 
                 watermark_text, 
                 line_spacing=50, 
                 font_size=40,
                 angle=45, 
                 color=(255, 255, 255, 128)):
    """
    Добавляет водяные знаки по диагонали, полностью заполняя изображение.

    Параметры:
    - input_image_path: путь к исходному изображению
    - output_image_path: путь для сохранения изображения с водяными знаками
    - watermark_text: текст водяного знака
    - line_spacing: расстояние между линиями водяных знаков (в пикселях)
    - font_size: размер шрифта
    - color: цвет водяного знака (R, G, B, A)
    - angle: угол наклона водяных знаков (в градусах)
    """
    
    try:
    
        if not os.path.exists(input_image_path):
            raise FileNotFoundError(f"Input file not found: {input_image_path}")


        input_filename = os.path.basename(input_image_path)
        name, ext = os.path.splitext(input_filename)
        output_ext = ext.lower() if ext.lower() in [".jpg", ".jpeg", ".png"] else ".jpg"
        
        if os.path.isdir(output_image_path) or output_image_path.endswith(("\\", "/")):
            output_image_path = os.path.join(output_image_path, f"{name}_watermarked{output_ext}")
        

        output_dir = os.path.dirname(output_image_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        if output_dir and not os.access(output_dir, os.W_OK):
            raise PermissionError(f"No write permissions for directory: {output_dir}")
        
        image = Image.open(input_image_path).convert("RGBA")
        width, height = image.size
        
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        diagonal_length = int(math.sqrt(width**2 + height**2))*2

        watermark = Image.new("RGBA", (diagonal_length,diagonal_length), (0, 0, 0, 0))
        draw = ImageDraw.Draw(watermark)
        
        bbox = draw.textbbox((0, 0), watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        step = text_height + line_spacing

        for y in range(-diagonal_length, diagonal_length, step):

            x_offset = -diagonal_length
            while x_offset < diagonal_length:
                draw.text((x_offset, y), watermark_text, fill=color, font=font)
                x_offset += text_width + line_spacing
        
        watermark = watermark.rotate(angle, resample=Image.BICUBIC, expand=True)
        
        w_width, w_height = watermark.size
        watermark = watermark.crop((
            (w_width - width) // 2,
            (w_height - height) // 2,
            (w_width + width) // 2,
            (w_height + height) // 2
        ))

        watermarked = Image.alpha_composite(image, watermark)
        
        if output_ext.lower() in [".jpg", ".jpeg"]:
            watermarked = watermarked.convert("RGB")
            watermarked.save(output_image_path, quality=95)
        else:
            watermarked.save(output_image_path)
            
        return True
    
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    
    
if __name__ == "__main__":
    add_watermark("images/dowload/1595227146122330398.jpg", 
                  "images/with_watermark/", 
                  "Watermark Text", 
                  line_spacing=80, 
                  font_size=40, 
                  angle=45, 
                  color=(180, 180, 180, 128))
    
    
    
    