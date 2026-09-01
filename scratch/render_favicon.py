import asyncio
from playwright.async_api import async_playwright
from PIL import Image
import os

async def main():
    svg_path = os.path.abspath("public/flowgentic-meet-icon.svg")
    file_url = f"file:///{svg_path.replace(os.sep, '/')}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 512, "height": 512})
        await page.goto(file_url)
        os.makedirs("scratch", exist_ok=True)
        png_path = os.path.abspath("scratch/temp_icon.png")
        await page.screenshot(path=png_path, omit_background=True)
        await browser.close()
        
    img = Image.open(png_path)
    img = img.convert("RGBA")
    
    # Save PNG formats
    img.resize((128, 128), Image.Resampling.LANCZOS).save("public/favicon.png", "PNG")
    img.resize((64, 64), Image.Resampling.LANCZOS).save("public/favicon-64.png", "PNG")
    img.resize((32, 32), Image.Resampling.LANCZOS).save("public/favicon-32.png", "PNG")
    
    # Save true ICO formats containing 16x16, 32x32, 48x48, 64x64, 128x128
    img.save("public/favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)])
    img.save("app/favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)])
    img.resize((128, 128), Image.Resampling.LANCZOS).save("app/icon.png", "PNG")
    print("Successfully generated all favicon.ico, favicon.png, app/icon.png files!")

if __name__ == "__main__":
    asyncio.run(main())
