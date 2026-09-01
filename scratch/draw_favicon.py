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

def draw_os_window_logo():
    size = 400
    resample = get_resample_filter()
    
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Gradient helper color calculation: #A78BFA -> #8B5CF6 -> #7C3AED
    # Outer stroke (window box)
    rect_box = [60, 90, 340, 310]
    
    # Draw stroke by drawing outer rounded rect and masking inner rounded rect
    mask_outer = Image.new("L", (size, size), 0)
    d_out = ImageDraw.Draw(mask_outer)
    d_out.rounded_rectangle(rect_box, radius=28, fill=255)
    
    inner_box = [60 + 14, 90 + 14, 340 - 14, 310 - 14]
    mask_inner = Image.new("L", (size, size), 0)
    d_in = ImageDraw.Draw(mask_inner)
    d_in.rounded_rectangle(inner_box, radius=20, fill=255)
    
    stroke_mask = Image.new("L", (size, size), 0)
    for y in range(size):
        for x in range(size):
            out_v = mask_outer.getpixel((x, y))
            in_v = mask_inner.getpixel((x, y))
            if out_v > 0 and in_v == 0:
                stroke_mask.putpixel((x, y), 255)
                
    # Create gradient layer
    grad = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * size)
            r = int(167 * (1 - t) + 124 * t)
            g = int(139 * (1 - t) + 58 * t)
            b = int(250 * (1 - t) + 237 * t)
            grad.putpixel((x, y), (r, g, b, 255))
            
    # Apply stroke mask
    window_stroke = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    window_stroke.paste(grad, (0, 0), stroke_mask)
    img = Image.alpha_composite(img, window_stroke)
    
    # Draw horizontal divider line: y1=150, height=10, x1=60, x2=340
    line_mask = Image.new("L", (size, size), 0)
    l_draw = ImageDraw.Draw(line_mask)
    l_draw.rectangle([60, 145, 340, 155], fill=255)
    
    line_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    line_layer.paste(grad, (0, 0), line_mask)
    img = Image.alpha_composite(img, line_layer)
    
    # Traffic light dots
    draw = ImageDraw.Draw(img)
    # Red dot
    draw.ellipse([94 - 10, 120 - 10, 94 + 10, 120 + 10], fill="#F43F5E")
    # Yellow dot
    draw.ellipse([126 - 10, 120 - 10, 126 + 10, 120 + 10], fill="#FACC15")
    # Green dot
    draw.ellipse([158 - 10, 120 - 10, 158 + 10, 120 + 10], fill="#22C55E")
    
    # Play Triangle: M175 172 l0 80 66-40z
    tri_mask = Image.new("L", (size, size), 0)
    t_draw = ImageDraw.Draw(tri_mask)
    t_draw.polygon([(175, 172), (175, 252), (241, 212)], fill=255)
    
    tri_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    tri_layer.paste(grad, (0, 0), tri_mask)
    img = Image.alpha_composite(img, tri_layer)
    
    # Save formats
    os.makedirs("public", exist_ok=True)
    os.makedirs("app", exist_ok=True)
    
    img.resize((128, 128), resample).save("public/favicon.png", "PNG")
    img.resize((64, 64), resample).save("public/favicon-64.png", "PNG")
    img.resize((32, 32), resample).save("public/favicon-32.png", "PNG")
    img.resize((128, 128), resample).save("public/flowgentic-meet-icon.png", "PNG")
    img.resize((128, 128), resample).save("app/icon.png", "PNG")
    img.resize((180, 180), resample).save("app/apple-icon.png", "PNG")
    
    img.save("public/favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)])
    img.save("app/favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)])
    print("SUCCESS: Updated all favicon formats with OS Window Trafficdots logo!")

if __name__ == "__main__":
    draw_os_window_logo()
