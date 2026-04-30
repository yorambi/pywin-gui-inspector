"""
Upload all project source files to a new NotebookLM notebook.

Run after logging in:
    notebooklm login
    python upload_to_notebooklm.py
"""

import asyncio
from pathlib import Path

import notebooklm
from notebooklm import NotebookLMClient

NOTEBOOK_NAME = "pywin-gui-inspector"
STORAGE = Path.home() / ".notebooklm/storage_state.json"

PROJECT_FILES = [
    Path("gui_detector.py"),
    Path("gui_helper.py"),
    Path("ExampleScripts/01_inspect_and_export.py"),
    Path("ExampleScripts/02_click_and_type.py"),
    Path("ExampleScripts/03_ocr_text_search.py"),
    Path("ExampleScripts/04_image_template_search.py"),
    Path("ExampleScripts/05_smart_click.py"),
    Path("ExampleScripts/06_script_writer.py"),
    Path("ExampleScripts/07_bulk_element_processing.py"),
    Path("ExampleScripts/08_watch_mode.py"),
    Path("ExampleScripts/09_full_workflow.py"),
    Path("README.md"),
]


async def main() -> None:
    async with await NotebookLMClient.from_storage(str(STORAGE)) as client:
        # Reuse existing notebook if name matches, otherwise create
        notebooks = await client.notebooks.list()
        nb = next((n for n in notebooks if n.title == NOTEBOOK_NAME), None)
        if nb:
            print(f"[+] Using existing notebook: {NOTEBOOK_NAME!r}  (ID: {nb.id})")
        else:
            print(f"[+] Creating notebook: {NOTEBOOK_NAME!r}")
            nb = await client.notebooks.create(NOTEBOOK_NAME)
            print(f"    ID: {nb.id}")

        # Upload each file as a text source
        for path in PROJECT_FILES:
            if not path.exists():
                print(f"[!] Skipping (not found): {path}")
                continue

            title = path.name
            content = path.read_text(encoding="utf-8")
            print(f"[>] Adding {title} ({len(content):,} chars)...", end=" ", flush=True)

            try:
                await client.sources.add_text(nb.id, title, content, wait=True)
                print("done")
            except Exception as exc:
                print(f"FAILED: {exc}")

        print(f"\n[+] All done. Open your notebook at:")
        print(f"    https://notebooklm.google.com/notebook/{nb.id}")


asyncio.run(main())