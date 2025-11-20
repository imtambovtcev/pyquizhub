#!/usr/bin/env python3
"""
Find replacement URLs for failed file types
"""

import requests

# Alternative URLs to test
ALTERNATIVE_URLS = {
    "png": [
        "https://www.w3.org/Graphics/PNG/alphatest.png",
        "https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png",
        "https://www.fnordware.com/superpng/pnggrad16rgb.png"
    ],
    "gif": [
        "https://www.w3.org/Graphics/PNG/BearsGillespies.gif",
        "https://upload.wikimedia.org/wikipedia/commons/2/2c/Rotating_earth_%28large%29.gif",
        "https://www.w3.org/2008/site/images/logo-w3c-mobile-lg.gif"
    ],
    "mp4": [
        "https://www.w3schools.com/html/mov_bbb.mp4",
        "https://download.blender.org/demo/movies/BBB/bbb_sunflower_1080p_30fps_normal.mp4.zip",
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
    ],
    "ogg": [
        "https://www.w3schools.com/html/mov_bbb.ogg",
        "https://upload.wikimedia.org/wikipedia/commons/f/f2/Misc_roswellae.ogg",
        "https://upload.wikimedia.org/wikipedia/commons/0/06/Wiki-Kerkrade.ogg"
    ],
    "xml": [
        "https://www.w3schools.com/xml/note.xml",
        "https://raw.githubusercontent.com/opengapps/opengapps/master/LICENSE",
        "https://www.w3.org/2001/XMLSchema.xsd"
    ]
}


def test_url(url, format_name):
    """Test a single URL"""
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)

        if response.status_code == 200:
            content_length = response.headers.get('Content-Length')
            content_type = response.headers.get('Content-Type')

            if content_length:
                size_bytes = int(content_length)
                if size_bytes < 1024:
                    size_str = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes / 1024:.1f} KB"
                else:
                    size_str = f"{size_bytes / (1024 * 1024):.1f} MB"

                return {
                    "url": url,
                    "status": "✅ WORKS",
                    "size": size_str,
                    "size_bytes": size_bytes,
                    "content_type": content_type
                }
            else:
                # Try GET
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    size_bytes = len(response.content)
                    if size_bytes < 1024:
                        size_str = f"{size_bytes} B"
                    elif size_bytes < 1024 * 1024:
                        size_str = f"{size_bytes / 1024:.1f} KB"
                    else:
                        size_str = f"{size_bytes / (1024 * 1024):.1f} MB"

                    return {
                        "url": url,
                        "status": "✅ WORKS (GET)",
                        "size": size_str,
                        "size_bytes": size_bytes,
                        "content_type": response.headers.get('Content-Type')
                    }

        return {
            "url": url,
            "status": f"❌ HTTP {response.status_code}",
            "size": None,
            "size_bytes": None,
            "content_type": None
        }

    except requests.exceptions.Timeout:
        return {"url": url, "status": "❌ TIMEOUT", "size": None, "size_bytes": None, "content_type": None}
    except Exception as e:
        return {"url": url, "status": f"❌ {str(e)[:50]}", "size": None, "size_bytes": None, "content_type": None}


def main():
    print("🔍 Testing alternative URLs for failed file types...\n")

    results = {}

    for format_name, urls in ALTERNATIVE_URLS.items():
        print(f"\n{'='*60}")
        print(f"Testing: {format_name.upper()}")
        print(f"{'='*60}")

        format_results = []

        for url in urls:
            print(f"\n{url}")
            result = test_url(url, format_name)
            print(f"  {result['status']}")
            if result['size']:
                print(f"  Size: {result['size']}")
                print(f"  Type: {result['content_type']}")

            format_results.append(result)

        # Find best working URL (smallest working file)
        working = [r for r in format_results if r['status'].startswith('✅')]
        if working:
            best = min(working, key=lambda x: x['size_bytes'])
            results[format_name] = best
            print(f"\n  ⭐ BEST: {best['url']}")
            print(f"     Size: {best['size']}, Type: {best['content_type']}")
        else:
            print(f"\n  ❌ NO WORKING URLS FOUND FOR {format_name}")

    # Print summary
    print("\n\n" + "="*60)
    print("SUMMARY - BEST REPLACEMENT URLs")
    print("="*60)

    for format_name, result in results.items():
        print(f"\n{format_name.upper()}:")
        print(f"  URL: {result['url']}")
        print(f"  Size: {result['size']}")
        print(f"  Type: {result['content_type']}")


if __name__ == "__main__":
    main()
