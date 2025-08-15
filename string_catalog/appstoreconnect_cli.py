import os
import time
from enum import Enum
from pathlib import Path
from typing import Dict, Optional
from rich import print

import httpx
import typer
from authlib.jose import jwt

from .whats_new import load_whats_new_json, find_best_matching_locale


ASC_BASE_URL = "https://api.appstoreconnect.apple.com/v1"


class Platform(str, Enum):
    IOS = "IOS"
    MAC_OS = "MAC_OS"
    TV_OS = "TV_OS"
    VISION_OS = "VISION_OS"
    WATCH_OS = "WATCH_OS"


app = typer.Typer(
    add_completion=False,
    help="Tools for App Store Connect automation",
)


def generate_jwt_token(key_id: str, issuer_id: str, private_key_pem: str) -> str:
    expiration_timestamp = int(round(time.time() + (20.0 * 60.0)))  # 20 minutes
    header = {"alg": "ES256", "kid": key_id, "typ": "JWT"}
    payload = {
        "iss": issuer_id,
        "exp": expiration_timestamp,
        "aud": "appstoreconnect-v1",
    }
    token = jwt.encode(header, payload, private_key_pem)
    return f"Bearer {token.decode()}"


def build_client(auth_bearer: str) -> httpx.Client:
    return httpx.Client(
        base_url=ASC_BASE_URL,
        headers={
            "Authorization": auth_bearer,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )


def get_app_id(client: httpx.Client, bundle_id: str) -> str:
    resp = client.get("/apps", params={"filter[bundleId]": bundle_id, "limit": 1})
    resp.raise_for_status()
    data = resp.json().get("data", [])
    if not data:
        raise RuntimeError(f"App not found for bundleId: {bundle_id}")
    return data[0]["id"]


def get_app_store_version_id(
    client: httpx.Client, app_id: str, version_string: str, platform: str
) -> str:
    params = {
        "filter[platform]": platform,
        "filter[versionString]": version_string,
        "limit": 1,
    }
    try:
        resp = client.get(f"/apps/{app_id}/appStoreVersions", params=params)
        resp.raise_for_status()
        data = resp.json().get("data", [])
    except httpx.HTTPStatusError as e:
        message = getattr(e.response, "text", str(e))
        raise RuntimeError(
            f"Failed to query app store versions for app={app_id} platform={platform}: {message}"
        ) from e

    if len(data) == 0:
        print(
            f"No app store version found for app={app_id} platform={platform} version={version_string}"
        )
        exit(1)

    return data[0]["id"]


def list_localizations_by_locale(
    client: httpx.Client, app_store_version_id: str
) -> Dict[str, Dict[str, Optional[str]]]:
    try:
        resp = client.get(
            f"/appStoreVersions/{app_store_version_id}/appStoreVersionLocalizations",
        )
    except httpx.HTTPStatusError as e:
        message = getattr(e.response, "text", str(e))
        raise RuntimeError(
            f"Failed to query app store versions for app={app_store_version_id}: {message}"
        ) from e

    data = resp.json().get("data", [])
    locale_to_localization: Dict[str, Dict[str, Optional[str]]] = {}
    for item in data:
        attributes = item.get("attributes", {})
        locale = attributes.get("locale")
        whats_new = attributes.get("whatsNew")
        if locale:
            locale_to_localization[locale] = {"id": item["id"], "whatsNew": whats_new}
    return locale_to_localization


def update_localization_whats_new(
    client: httpx.Client, localization_id: str, whats_new: str
) -> None:
    payload = {
        "data": {
            "id": localization_id,
            "type": "appStoreVersionLocalizations",
            "attributes": {"whatsNew": whats_new},
        }
    }
    resp = client.patch(
        f"/appStoreVersionLocalizations/{localization_id}", json=payload
    )
    resp.raise_for_status()


def upsert_whats_new(
    client: httpx.Client,
    app_store_version_id: str,
    updates: Dict[str, str],
) -> None:
    existing = list_localizations_by_locale(client, app_store_version_id)
    success_count = 0
    for existing_locale in existing.keys():
        # Find the best matching locale in updates
        best_match = find_best_matching_locale(existing_locale, updates)

        if best_match:
            success_count += 1
            whats_new = updates[best_match]
            text = (whats_new or "").strip()
            if not text:
                continue

            update_localization_whats_new(client, existing[existing_locale]["id"], text)
            if best_match == existing_locale:
                print(f"✅ Successfully updated {existing_locale}")
            else:
                print(f"✅ Successfully updated {existing_locale} → {best_match}")
        else:
            print(f"⚠️ No matching content found for existing locale {existing_locale}")
    print(f"✅ Successfully updated {success_count} locales")


@app.command("list-locales", help="List all available locales for an app version")
def list_locales(
    bundle_id: str = typer.Option(..., "--bundle-id", help="App bundle identifier"),
    version: str = typer.Option(
        ..., "--version", help="App version string, e.g. 1.2.3"
    ),
    platform: Platform = typer.Option(
        Platform.IOS, "--platform", help="Target platform"
    ),
    issuer_id: Optional[str] = typer.Option(
        os.getenv("ASC_ISSUER_ID"),
        "--issuer-id",
        help="App Store Connect API Issuer ID",
        envvar=["ASC_ISSUER_ID"],
    ),
    key_id: Optional[str] = typer.Option(
        os.getenv("ASC_KEY_ID"),
        "--key-id",
        help="App Store Connect API Key ID",
        envvar=["ASC_KEY_ID"],
    ),
    key_file: Optional[Path] = typer.Option(
        os.getenv("ASC_KEY_FILE"),
        "--key-file",
        help="Path to .p8 private key file",
        envvar=["ASC_KEY_FILE"],
    ),
) -> None:
    if not issuer_id or not key_id or not key_file:
        print(
            "Missing credentials. Provide --issuer-id, --key-id, --key-file or set env ASC_ISSUER_ID, ASC_KEY_ID, ASC_KEY_FILE",
        )
        raise typer.Exit(2)

    if not Path(key_file).exists():
        print(f"Key file not found: {key_file}")
        raise typer.Exit(2)

    try:
        private_key_pem = Path(key_file).read_text(encoding="utf-8")
    except Exception as e:
        print(f"Failed to read key file: {e}")
        raise typer.Exit(2)

    auth_bearer = generate_jwt_token(key_id, issuer_id, private_key_pem)

    with build_client(auth_bearer) as client:
        print("Fetching app id...")
        app_id = get_app_id(client, bundle_id)
        print("Fetching app store version id...")
        version_id = get_app_store_version_id(client, app_id, version, platform.value)
        print("Fetching existing localizations...")
        existing = list_localizations_by_locale(client, version_id)

        print("\nAvailable locales:")
        for locale in existing.keys():
            print(f"  {locale}")

        print(f"\nTotal locales: {len(existing.keys())}")


@app.command(
    "update-whats-new", help="Update 'What's New' text for locales from a JSON file"
)
def update_whats_new(
    bundle_id: str = typer.Option(..., "--bundle-id", help="App bundle identifier"),
    version: str = typer.Option(
        ..., "--version", help="App version string, e.g. 1.2.3"
    ),
    platform: Platform = typer.Option(
        Platform.IOS, "--platform", help="Target platform"
    ),
    json_path: Path = typer.Option(
        ..., "--json-path", help="Path to JSON file: {locale: whatsNew}"
    ),
    issuer_id: Optional[str] = typer.Option(
        os.getenv("ASC_ISSUER_ID"),
        "--issuer-id",
        help="App Store Connect API Issuer ID",
        envvar=["ASC_ISSUER_ID"],
    ),
    key_id: Optional[str] = typer.Option(
        os.getenv("ASC_KEY_ID"),
        "--key-id",
        help="App Store Connect API Key ID",
        envvar=["ASC_KEY_ID"],
    ),
    key_file: Optional[Path] = typer.Option(
        os.getenv("ASC_KEY_FILE"),
        "--key-file",
        help="Path to .p8 private key file",
        envvar=["ASC_KEY_FILE"],
    ),
) -> None:
    if not issuer_id or not key_id or not key_file:
        print(
            "Missing credentials. Provide --issuer-id, --key-id, --key-file or set env ASC_ISSUER_ID, ASC_KEY_ID, ASC_KEY_FILE",
        )
        raise typer.Exit(2)

    if not Path(key_file).exists():
        print(f"Key file not found: {key_file}")
        raise typer.Exit(2)

    try:
        private_key_pem = Path(key_file).read_text(encoding="utf-8")
    except Exception as e:
        print(f"Failed to read key file: {e}")
        raise typer.Exit(2)

    auth_bearer = generate_jwt_token(key_id, issuer_id, private_key_pem)

    try:
        updates = load_whats_new_json(json_path)
    except FileNotFoundError:
        print(f"JSON file not found: {json_path}")
        raise typer.Exit(2)
    except ValueError as e:
        print(f"Invalid JSON format: {e}")
        raise typer.Exit(2)

    with build_client(auth_bearer) as client:
        print("Fetching app id...")
        app_id = get_app_id(client, bundle_id)
        print("Fetching app store version id...")
        version_id = get_app_store_version_id(client, app_id, version, platform.value)
        print('Updating "What\'s New"...')
        upsert_whats_new(client, version_id, updates)


if __name__ == "__main__":
    app()
