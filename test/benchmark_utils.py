import time
import re

TEXT_HTML = "<div><p>Hello World</p></div>"
TEXT_PLAIN = "Just a simple plain text string without any html markup at all."

# Original implementation
def is_html_content_orig(text):
    if not text or not isinstance(text, str):
        return False
    return bool(re.search(r'<(?:!doctype|html|head|body|div|span|p|h[1-6]|br|strong|em|ul|ol|li|table|tr|td|th)', text, re.IGNORECASE))

# Precompiled regex implementation
HTML_TAG_RE = re.compile(r'<(?:!doctype|html|head|body|div|span|p|h[1-6]|br|strong|em|ul|ol|li|table|tr|td|th)', re.IGNORECASE)

def is_html_content_fast(text):
    if not text or not isinstance(text, str) or '<' not in text:
        return False
    return bool(HTML_TAG_RE.search(text))

# Verification
assert is_html_content_orig(TEXT_HTML) == is_html_content_fast(TEXT_HTML) == True
assert is_html_content_orig(TEXT_PLAIN) == is_html_content_fast(TEXT_PLAIN) == False

N = 200000

print("Testing plain text (no '<'):")
t0 = time.perf_counter()
for _ in range(N):
    is_html_content_orig(TEXT_PLAIN)
t1 = time.perf_counter()

t2 = time.perf_counter()
for _ in range(N):
    is_html_content_fast(TEXT_PLAIN)
t3 = time.perf_counter()

print(f"Original ({N} calls): {t1 - t0:.4f}s")
print(f"Optimized ({N} calls): {t3 - t2:.4f}s")
print(f"Speedup: {(t1 - t0) / (t3 - t2):.2f}x")

print("\nTesting HTML text:")
t0 = time.perf_counter()
for _ in range(N):
    is_html_content_orig(TEXT_HTML)
t1 = time.perf_counter()

t2 = time.perf_counter()
for _ in range(N):
    is_html_content_fast(TEXT_HTML)
t3 = time.perf_counter()

print(f"Original ({N} calls): {t1 - t0:.4f}s")
print(f"Optimized ({N} calls): {t3 - t2:.4f}s")
print(f"Speedup: {(t1 - t0) / (t3 - t2):.2f}x")
