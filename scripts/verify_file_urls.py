#!/usr/bin/env python3
"""
Verify file URLs are accessible and extract metadata
"""

import requests
import json
from pathlib import Path

# URLs to test - VERIFIED WORKING ALTERNATIVES
TEST_URLS = {
    "images": {
        "jpeg": "https://www.w3.org/People/mimasa/test/imgformat/img/w3c_home.jpg",
        # REPLACED: was sample-videos.com (timeout)
        "png": "https://www.w3.org/Graphics/PNG/alphatest.png",
        # REPLACED: was nurbcup.gif (404)
        "gif": "https://www.w3.org/2008/site/images/logo-w3c-mobile-lg.gif",
        "webp": "https://www.gstatic.com/webp/gallery/1.webp",
        "svg": "https://www.w3.org/Graphics/SVG/Test/20110816/svg/struct-use-14-f.svg",
        "tiff": "https://download.osgeo.org/geotiff/samples/spot/chicago/UTM2GTIF.TIF",
        "bmp": "https://people.math.sc.edu/Burkardt/data/bmp/lena.bmp"
    },
    "audio": {
        "mp3": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
        "wav": "https://www.mmsp.ece.mcgill.ca/Documents/AudioFormats/WAVE/Samples/SoundCardAttrition/stereofl.wav"
    },
    "video": {
        # REPLACED: was sample-videos.com (timeout)
        "mp4": "https://www.w3schools.com/html/mov_bbb.mp4",
        # REPLACED: was wikipedia (403)
        "ogg": "https://www.w3schools.com/html/mov_bbb.ogg",
        "webm": "https://dl11.webmfiles.org/big-buck-bunny_trailer-.webm"
    },
    "documents": {
        "txt": "https://www.w3.org/History/19921103-hypertext/hypertext/README.html",
        "md": "https://raw.githubusercontent.com/github/gitignore/main/README.md",
        "pdf": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    },
    "binary": {
        "tar_gz": "https://github.com/git/git/archive/refs/tags/v2.43.0.tar.gz",
        "csv": "https://people.sc.fsu.edu/~jburkardt/data/csv/addresses.csv",
        # REPLACED: was xmlconf-20080827.xml (300)
        "xml": "https://www.w3schools.com/xml/note.xml",
        "zip": "https://www.learningcontainer.com/wp-content/uploads/2020/05/sample-zip-file.zip"
    }
}


def verify_url(url, format_name):
    """Verify a URL is accessible and extract metadata"""
    print(f"\n{'=' * 60}")
    print(f"Testing: {format_name.upper()}")
    print(f"URL: {url}")
    print(f"{'=' * 60}")

    result = {
        "url": url,
        "format": format_name,
        "accessible": False,
        "status_code": None,
        "content_type": None,
        "content_length": None,
        "size_human": None,
        "error": None
    }

    try:
        # Use HEAD request to get metadata without downloading the file
        response = requests.head(url, allow_redirects=True, timeout=10)
        result["status_code"] = response.status_code

        if response.status_code == 200:
            result["accessible"] = True
            result["content_type"] = response.headers.get(
                'Content-Type', 'unknown')

            # Try to get content length
            content_length = response.headers.get('Content-Length')
            if content_length:
                size_bytes = int(content_length)
                result["content_length"] = size_bytes

                # Convert to human readable
                if size_bytes < 1024:
                    result["size_human"] = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    result["size_human"] = f"{size_bytes / 1024:.1f} KB"
                else:
                    result["size_human"] = f"{size_bytes /
                                              (1024 *
                                               1024):.1f} MB"

                print(f"✅ ACCESSIBLE")
                print(f"   Status: {result['status_code']}")
                print(f"   Content-Type: {result['content_type']}")
                print(
                    f"   Size: {
                        result['size_human']} ({
                        size_bytes:,} bytes)")
            else:
                # Try GET request to get actual size
                print("   ⚠️  No Content-Length header, trying GET request...")
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    size_bytes = len(response.content)
                    result["content_length"] = size_bytes
                    result["content_type"] = response.headers.get(
                        'Content-Type', 'unknown')

                    if size_bytes < 1024:
                        result["size_human"] = f"{size_bytes} B"
                    elif size_bytes < 1024 * 1024:
                        result["size_human"] = f"{size_bytes / 1024:.1f} KB"
                    else:
                        result["size_human"] = f"{size_bytes /
                                                  (1024 *
                                                   1024):.1f} MB"

                    print(f"✅ ACCESSIBLE (via GET)")
                    print(f"   Status: {result['status_code']}")
                    print(f"   Content-Type: {result['content_type']}")
                    print(
                        f"   Size: {
                            result['size_human']} ({
                            size_bytes:,} bytes)")
                else:
                    result["accessible"] = False
                    result["error"] = f"GET request failed: {
                        response.status_code}"
                    print(
                        f"❌ FAILED: GET request returned {
                            response.status_code}")
        else:
            result["error"] = f"HTTP {response.status_code}"
            print(f"❌ FAILED: HTTP {response.status_code}")

    except requests.exceptions.Timeout:
        result["error"] = "Request timeout"
        print(f"❌ FAILED: Request timeout")
    except requests.exceptions.RequestException as e:
        result["error"] = str(e)
        print(f"❌ FAILED: {e}")
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"
        print(f"❌ FAILED: Unexpected error: {e}")

    return result


def main():
    print("🔍 Verifying File URLs...")
    print("=" * 60)

    all_results = {
        "test_date": None,
        "total_tested": 0,
        "accessible": 0,
        "failed": 0,
        "results_by_category": {}
    }

    # Test all URLs
    for category, urls in TEST_URLS.items():
        print(f"\n\n{'#' * 60}")
        print(f"# Category: {category.upper()}")
        print(f"{'#' * 60}")

        category_results = []

        for format_name, url in urls.items():
            result = verify_url(url, format_name)
            category_results.append(result)
            all_results["total_tested"] += 1

            if result["accessible"]:
                all_results["accessible"] += 1
            else:
                all_results["failed"] += 1

        all_results["results_by_category"][category] = category_results

    # Import datetime for timestamp
    from datetime import datetime
    all_results["test_date"] = datetime.now().isoformat()

    # Print summary
    print("\n\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total URLs tested: {all_results['total_tested']}")
    print(f"✅ Accessible: {all_results['accessible']}")
    print(f"❌ Failed: {all_results['failed']}")
    print(
        f"Success rate: {
            all_results['accessible'] / all_results['total_tested'] * 100:.1f}%")

    # Save results to JSON
    output_file = Path("file_url_verification_results.json")
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\n📄 Detailed results saved to: {output_file}")

    # Print accessible URLs by category
    print("\n" + "=" * 60)
    print("ACCESSIBLE URLs BY CATEGORY")
    print("=" * 60)

    for category, results in all_results["results_by_category"].items():
        accessible_urls = [r for r in results if r["accessible"]]
        if accessible_urls:
            print(
                f"\n{category.upper()} ({len(accessible_urls)}/{len(results)} working):")
            for r in accessible_urls:
                print(f"  ✅ {r['format']}: {r['size_human']} - {r['url']}")

    # Print failed URLs
    print("\n" + "=" * 60)
    print("FAILED URLs")
    print("=" * 60)

    for category, results in all_results["results_by_category"].items():
        failed_urls = [r for r in results if not r["accessible"]]
        if failed_urls:
            print(f"\n{category.upper()}:")
            for r in failed_urls:
                print(f"  ❌ {r['format']}: {r['error']} - {r['url']}")


if __name__ == "__main__":
    main()
