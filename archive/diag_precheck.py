from playwright.sync_api import sync_playwright
import domx

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(no_viewport=True)
    page.goto(domx.BASE_URL + "/")
    print("Συνδέσου, μείνε στο dashboard, Resume.")
    page.pause()
    for wo in ["WOTEST0013", "WOTEST0011"]:          # 1ο δεν υπάρχει, 2ο υπάρχει
        try:
            r = domx.exists_in_domx(page, wo)
            print(f"[{wo}] exists_in_domx -> {r} | Σύνολο: {page.get_by_text('Σύνολο').first.inner_text()!r}")
        except Exception as e:
            print(f"[{wo}] ΣΦΑΛΜΑ: {type(e).__name__}: {e}")
            page.screenshot(path=f"diag_{wo}.png", full_page=True)
    page.pause()
    browser.close()