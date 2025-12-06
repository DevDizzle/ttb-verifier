import re
from playwright.sync_api import Page, expect

def test_homepage_loads(page: Page):
    # 1. Go to the local app (Ensure your app is running locally first!)
    page.goto("http://127.0.0.1:8000")

    # 2. Check page title
    expect(page).to_have_title(re.compile("TTB Label Verifier"))

    # 3. Check that the header exists
    expect(page.locator(".navbar-brand")).to_contain_text("TTB Verifier")

def test_full_verification_flow(page: Page):
    """
    Simulates a user filling out the form and uploading a label.
    """
    page.goto("http://127.0.0.1:8000")

    # 1. Fill out the form
    page.locator('input[name="brand_name"]').fill("Old Tom Distillery")
    page.locator('input[name="product_type"]').fill("Kentucky Straight Bourbon Whiskey")
    page.locator('input[name="abv"]').fill("45%")

    # 2. Upload the image (Make sure path is correct relative to where you run pytest)
    # We use set_input_files on the file input locator
    page.locator('input[name="file"]').set_input_files("samples/old_tom_distillery.jpg")

    # 3. Click Verify
    page.get_by_role("button", name="Verify Compliance").click()

    # 4. Wait for results
    # We look for the success alert to appear
    success_alert = page.locator("#overallStatus")

    # Wait up to 10 seconds for AI to process
    expect(success_alert).to_be_visible(timeout=10000)

    # 5. Verify the text is Compliance Check Passed
    expect(success_alert).to_contain_text("Compliance Check Passed")
