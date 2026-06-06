import asyncio
from playwright.async_api import async_playwright

async def main():
    try:
        print("Starting playwright...")
        async with async_playwright() as p:
            for channel in ["msedge", "chrome"]:
                try:
                    print(f"Trying channel: {channel}...")
                    browser = await p.chromium.launch(headless=True, channel=channel)
                    print(f"Success launching browser with channel: {channel}!")
                    page = await browser.new_page()
                    await page.goto("https://example.com")
                    title = await page.title()
                    print(f"Page title is: {title}")
                    await browser.close()
                    return
                except Exception as e:
                    print(f"Failed with channel {channel}: {e}")
    except Exception as e:
        print(f"Outer error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
