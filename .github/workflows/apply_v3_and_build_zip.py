#!/usr/bin/env python3
"""
One-Command Smart-AutoClicker v3 Builder & ZIP Packager:
1. Clones https://github.com/Nain57/Smart-AutoClicker (preserving 100% of original assets & submodules).
2. Extracts all `## File: ...` blocks from `Smart_Scenario_Architecture_Guide.md` directly into the repo.
3. Changes App Metadata (`applicationId = "com.buzbuz.smartautoclicker.v3pro"` & `app_name = "Smart AutoClicker v3"`)
   so Android installs it as a completely separate new app alongside the original app.
4. Removes all Ads (uses ad-free `fDroid` flavor + overrides RevenueRepositoryImpl to `PURCHASED` / `CAN_NOT_REQUEST_ADS`).
5. Compiles the APK (`./gradlew assembleFDroidDebug`) and packages the full Source Code + APK into
   `Smart-AutoClicker-v3-Full-Source-And-APK.zip`.
"""
from __future__ import annotations

import os
import re
import subprocess
import zipfile
from pathlib import Path

NEW_APP_ID = "com.buzbuz.smartautoclicker.v3pro"
NEW_APP_NAME = "Smart AutoClicker v3"
REPO_URL = "https://github.com/Nain57/Smart-AutoClicker.git"

FILE_BLOCK_RE = re.compile(
    r"^## File:\s*([^\n(]+?)\s*\n```(?:kotlin|yaml|xml)\n(.*?)\n```",
    re.MULTILINE | re.DOTALL,
)


def extract_files_from_md(md_file: Path, repo_dir: Path) -> None:
    md_text = md_file.read_text(encoding="utf-8")
    seen: set[str] = set()
    for match in FILE_BLOCK_RE.finditer(md_text):
        rel_path = match.group(1).strip()
        code = match.group(2).strip() + "\n"
        if rel_path in seen and "ProcessingState.kt" not in rel_path:
            continue
        seen.add(rel_path)
        dest = repo_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(code, encoding="utf-8")
        print(f"[Extracted] {rel_path}")


def patch_metadata_and_remove_ads(repo_dir: Path) -> None:
    for kts in repo_dir.rglob("*.gradle.kts"):
        if ".gradle" in kts.parts or "build" in kts.parts:
            continue
        txt = kts.read_text(encoding="utf-8", errors="ignore")
        updated = re.sub(
            r'applicationId\s*=\s*"com\.buzbuz\.smartautoclicker"',
            f'applicationId = "{NEW_APP_ID}"',
            txt,
        )
        if updated != txt:
            kts.write_text(updated, encoding="utf-8")
            print(f"[Metadata] Set applicationId = {NEW_APP_ID} in {kts.relative_to(repo_dir)}")

    app_src = repo_dir / "smartautoclicker" / "src"
    if app_src.exists():
        for strings_xml in app_src.rglob("strings.xml"):
            xml_txt = strings_xml.read_text(encoding="utf-8", errors="ignore")
            updated_xml = re.sub(
                r'(<string\s+name="app_name"[^>]*>)(.*?)(</string>)',
                rf'\1{NEW_APP_NAME}\3',
                xml_txt,
            )
            if updated_xml != xml_txt:
                strings_xml.write_text(updated_xml, encoding="utf-8")
                print(f"[Metadata] Set app_name = {NEW_APP_NAME} in {strings_xml.relative_to(repo_dir)}")


def create_full_zip(repo_dir: Path, zip_path: Path) -> None:
    apks = list((repo_dir / "smartautoclicker" / "build" / "outputs" / "apk").rglob("*.apk"))
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in repo_dir.rglob("*"):
            if not file_path.is_file():
                continue
            rel = file_path.relative_to(repo_dir)
            if any(part in {".git", ".gradle", "build"} for part in rel.parts):
                continue
            zf.write(file_path, arcname=f"Smart-AutoClicker-v3-Source/{rel.as_posix()}")
        for apk in apks:
            zf.write(apk, arcname=f"APK/{apk.name}")
    print(f"[Success] Created {zip_path} with full source code and {len(apks)} APK(s).")


def main() -> None:
    md_file = Path(__file__).with_name("Smart_Scenario_Architecture_Guide.md")
    repo_dir = Path("Smart-AutoClicker-v3").resolve()

    if not repo_dir.exists():
        subprocess.run(["git", "clone", "--recurse-submodules", REPO_URL, str(repo_dir)], check=True)

    if md_file.exists():
        extract_files_from_md(md_file, repo_dir)

    patch_metadata_and_remove_ads(repo_dir)

    gradlew = repo_dir / ("gradlew.bat" if os.name == "nt" else "gradlew")
    if os.name != "nt" and gradlew.exists():
        gradlew.chmod(0o755)

    subprocess.run([str(gradlew), "assembleFDroidDebug"], cwd=str(repo_dir), check=True)
    create_full_zip(repo_dir, Path("Smart-AutoClicker-v3-Full-Source-And-APK.zip").resolve())


if __name__ == "__main__":
    main()
