"""
Convert Activity Diagram HTML files to PDF using Playwright.
Run: python export_diagrams_pdf.py
"""
import subprocess
import sys
import os

def install_playwright():
    print("Installing playwright...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
    print("Installing Chromium browser...")
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])

def export_pdfs():
    from playwright.sync_api import sync_playwright

    diagrams_dir = os.path.dirname(os.path.abspath(__file__))
    
    files = [
        ("activity_registration.html", "Activity_Diagram_Registration.pdf"),
        ("activity_student.html",      "Activity_Diagram_Student.pdf"),
        ("activity_admin.html",        "Activity_Diagram_Admin.pdf"),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        for html_file, pdf_file in files:
            html_path = os.path.join(diagrams_dir, html_file)
            pdf_path  = os.path.join(diagrams_dir, pdf_file)

            if not os.path.exists(html_path):
                print(f"[SKIP] {html_file} not found.")
                continue

            # Load the HTML file
            page.goto(f"file:///{html_path.replace(os.sep, '/')}")
            
            # Wait for Mermaid to render all diagrams
            page.wait_for_selector(".mermaid svg", timeout=15000)
            page.wait_for_timeout(1500)  # Extra settle time

            # Export to PDF (A3 landscape for large diagrams)
            page.pdf(
                path=pdf_path,
                format="A3",
                landscape=False,
                print_background=True,
                margin={"top": "20mm", "bottom": "20mm", "left": "20mm", "right": "20mm"}
            )
            print(f"[OK]  Exported: {pdf_file}")

        browser.close()

if __name__ == "__main__":
    # Try importing playwright; install if missing
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        install_playwright()

    print("\n--- Exporting Activity Diagrams to PDF ---\n")
    export_pdfs()
    print("\nDone! PDF files saved in the 'diagrams' folder.")
