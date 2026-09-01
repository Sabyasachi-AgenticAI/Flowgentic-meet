from PIL import Image, ImageDraw
import os

def get_resample_filter():
    if hasattr(Image, 'Resampling'):
        return Image.Resampling.LANCZOS
    elif hasattr(Image, 'LANCZOS'):
        return Image.LANCZOS
    elif hasattr(Image, 'ANTIALIAS'):
        return Image.ANTIALIAS
    return 1

def create_flowgentic_favicon():
    size = 512
    resample = get_resample_filter()
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    
    # Create mask for rounded rectangle
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    margin = 16
    rect_box = [margin, margin, size - margin, size - margin]
    radius = 112
    mask_draw.rounded_rectangle(rect_box, radius=radius, fill=255)
    
    # Create background gradient image
    bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    
    # Diagonal purple gradient
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * size)
            r = int(124 * (1 - t) + 167 * t)
            g = int(58 * (1 - t) + 139 * t)
            b = int(237 * (1 - t) + 250 * t)
            bg.putpixel((x, y), (r, g, b, 255))
            
    # Apply rounded mask to background
    bg.putalpha(mask)
    img = Image.alpha_composite(img, bg)
    
    # Draw shapes over image
    draw = ImageDraw.Draw(img)
    
    # Chat bubble base
    bubble_path = [
        (256, 108), (172, 108), (104, 168), (104, 243),
        (104, 285), (126, 323), (160, 348), (157, 368),
        (145, 387), (133, 403), (137, 412), (141, 412),
        (176, 412), (203, 400), (224, 384), (236, 387),
        (248, 388), (256, 388), (340, 388), (408, 327),
        (408, 253), (408, 178), (340, 108), (256, 108)
    ]
    
    # Draw bubble base with white 14% opacity
    bubble_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(bubble_layer)
    b_draw.polygon(bubble_path, fill=(255, 255, 255, 36))
    img = Image.alpha_composite(img, bubble_layer)
    draw = ImageDraw.Draw(img)
    
    # 5 Audio waveform bars
    bars = [
        (150, 228, 26, 56),
        (196, 192, 26, 128),
        (242, 160, 26, 192),
        (288, 192, 26, 128),
        (334, 228, 26, 56),
    ]
    
    for x, y, w, h in bars:
        bar_box = [x, y, x + w, y + h]
        draw.rounded_rectangle(bar_box, radius=13, fill=(255, 255, 255, 255))
        
    # AI Spark Accent (star)
    star_points = [
        (368, 132), (377, 152), (397, 161), (377, 170),
        (368, 190), (359, 170), (339, 161), (359, 152)
    ]
    draw.polygon(star_points, fill=(255, 255, 255, 255))
    
    # Save PNG formats
    os.makedirs("public", exist_ok=True)
    os.makedirs("app", exist_ok=True)
    
    img.resize((128, 128), resample).save("public/favicon.png", "PNG")
    img.resize((64, 64), resample).save("public/favicon-64.png", "PNG")
    img.resize((32, 32), resample).save("public/favicon-32.png", "PNG")
    img.resize((128, 128), resample).save("public/flowgentic-meet-icon.png", "PNG")
    img.resize((128, 128), resample).save("app/icon.png", "PNG")
    img.resize((180, 180), resample).save("app/apple-icon.png", "PNG")
    
    # Generate multi-resolution favicon.ico
    img.save("public/favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)])
    img.save("app/favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)])
    print("SUCCESS: Overwritten public/favicon.ico and generated all favicon formats!")

if __name__ == "__main__":
    create_flowgentic_favicon()
