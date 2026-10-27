"""The shared quantity formatters (status bar, Render window and report all use them)."""

from fractalchemy.render.units import aspect_text, format_bytes, format_count, format_memory, format_rate, format_seconds


def test_counts_and_rates():
    assert format_count(42) == "42" and format_count(4560) == "4.56 k" and format_count(12_300_000) == "12.3 M"
    assert format_count(1.2e9) == "1.2 G" and format_count(999_999_999) == "1 G" and format_count(999_400) == "999 k"
    assert format_rate(2.5e6) == "2.5 M samples/s" and format_rate(1.2e9) == "1.2 G samples/s" and format_rate(0) == "0 samples/s"


def test_seconds_read_naturally():
    assert format_seconds(None) == "—" and format_seconds(-3) == "0.0 s" and format_seconds(4.26) == "4.3 s"
    assert format_seconds(42) == "42 s" and format_seconds(187) == "3 min 07 s" and format_seconds(8100) == "2 h 15 min"
    assert format_seconds(3 * 86400) == "3 d 0 h"


def test_bytes_memory_and_aspect():
    assert format_bytes(512) == "512 B" and format_bytes(204_680) == "204.68 kB" and format_bytes(3.2e12) == "3.20 TB"
    assert format_memory(768 << 20) == "768 MB" and format_memory(3 << 30) == "3.0 GB"
    assert aspect_text(1920, 1080) == "16 : 9" and aspect_text(1920, 1080, ":") == "16:9"
    assert aspect_text(1000, 999) == "1.001 : 1" and aspect_text(10, 0) == "10 : 1"
