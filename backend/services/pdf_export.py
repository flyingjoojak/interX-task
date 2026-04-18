from playwright.async_api import async_playwright

FRONTEND_BASE_URL = "http://localhost:3102"


async def generate_pdf(candidate_id: str) -> bytes:
    url = f"{FRONTEND_BASE_URL}/candidates/{candidate_id}?pdf=true"
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle")
            pdf_bytes = await page.pdf(format="A4", print_background=True)
            return pdf_bytes
        finally:
            await browser.close()
