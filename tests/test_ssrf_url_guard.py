"""Tests for SSRF-hardened platform URL detection (H3).

detect_platform must match on the URL *hostname* (not a substring) and reject
non-http(s) schemes and raw-IP hosts, so an attacker cannot smuggle an internal
or cloud-metadata target past the allow-list while still containing a platform
keyword.
"""

import pytest

from app.parsers.runner import detect_platform


# --- legitimate URLs still resolve to the right platform --------------------


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://yandex.ru/maps/org/1543198007/reviews/", "yandex_maps"),
        ("https://yandex.by/maps/org/123/", "yandex_maps"),
        ("https://www.google.com/maps/place/Clinic/reviews", "google_maps"),
        ("https://2gis.ru/spb/firm/70000001006556409", "2gis"),
        ("https://2gis.com/spb/firm/123", "2gis"),
        ("https://prodoctorov.ru/spb/lpu/12345-clinic/", "prodoctorov"),
        ("https://napopravku.ru/spb/clinics/clinic-name/", "napopravku"),
    ],
)
def test_legitimate_urls_detected(url, expected):
    assert detect_platform(url) == expected


# --- SSRF bypass attempts must NOT be accepted (return "other") -------------


@pytest.mark.parametrize(
    "url",
    [
        # cloud-metadata IP with a platform keyword in query/path/fragment
        "http://169.254.169.254/maps?x=yandex.ru",
        "http://169.254.169.254/latest/meta-data/?host=2gis.ru",
        "http://127.0.0.1:6379/#prodoctorov.ru",
        "http://localhost/maps?yandex.ru",
        # non-http schemes
        "file:///etc/passwd#prodoctorov.ru",
        "file://C:/Windows/System32/drivers/etc/hosts?2gis.ru",
        "gopher://127.0.0.1:6379/_INFO%0d%0a#yandex.ru/maps",
        # look-alike / suffix-smuggling hosts
        "http://2gis.ru.attacker.com/",
        "http://evil2gis.ru/",
        "https://attacker.com/?next=https://yandex.ru/maps",
        # private ranges
        "http://10.0.0.5/maps?yandex.ru",
        "http://192.168.1.1/#2gis.ru",
    ],
)
def test_ssrf_bypass_rejected(url):
    assert detect_platform(url) == "other"


def test_yandex_without_maps_path_is_not_maps():
    # yandex.ru homepage (no /maps) must not be treated as a maps target.
    assert detect_platform("https://yandex.ru/") == "other"


def test_empty_and_garbage():
    assert detect_platform("") == "other"
    assert detect_platform("not a url") == "other"
