import asyncio
import os
import sys

async def main():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("Playwright is not installed. Please install it by running: pip install playwright")
        return

    print("==================================================")
    print("Linear Session Login Helper")
    print("==================================================")
    print("This script will open a browser window for you to log in to Linear.")
    print("Once logged in, your session state will be saved to 'linear_state.json'.")
    print("==================================================")

    async with async_playwright() as p:
        # Launch headful browser so the user can interact
        print("Launching browser...")
        try:
            browser = await p.chromium.launch(
                headless=False,
                channel="msedge",
                args=["--disable-blink-features=AutomationControlled"]
            )
        except Exception:
            try:
                browser = await p.chromium.launch(
                    headless=False,
                    channel="chrome",
                    args=["--disable-blink-features=AutomationControlled"]
                )
            except Exception:
                browser = await p.chromium.launch(
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"]
                )

        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        # Hides webdriver flag to bypass automation checks
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = await context.new_page()

        print("Navigating to Linear login page...")
        await page.goto("https://linear.app/login")

        print("\n--> ACTION REQUIRED:")
        print("Please log in to your Linear account in the opened browser window.")
        print("Once you are fully logged in and see your dashboard/backlog,")
        input("Press [ENTER] here in the console to save your session state...")

        # Save state to root directory (one level up from scratch)
        state_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "linear_state.json"))
        await context.storage_state(path=state_path)
        print(f"\nSuccess! Session state saved to: {state_path}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
