"""Quick test to examine .X file structure"""
import sys

with open('../sample files/Satoko.X', 'rb') as f:
    data = f.read()

print(f"Total file size: {len(data)} bytes")
print(f"\nHeader: {data[:20]}")

# Look for text strings (ASCII printable)
text_parts = []
i = 0
while i < len(data):
    if 32 <= data[i] <= 126 or data[i] in [9, 10, 13]:
        start = i
        while i < len(data) and (32 <= data[i] <= 126 or data[i] in [9, 10, 13]):
            i += 1
        if i - start > 5:
            text_parts.append(data[start:i])
        # i is already incremented by the inner loop, don't increment again
    else:
        i += 1

print(f"\nText sections found: {len(text_parts)}")
print("\nFirst 10 text sections:")
for idx, t in enumerate(text_parts[:10]):
    print(f"{idx+1}. {repr(t)}")

# Look for potential Shift-JIS strings (high bytes)
print("\n\nSearching for potential Japanese (Shift-JIS) strings...")
potential_sjis = []
i = 0
max_iterations = len(data)  # Safety limit
iterations = 0

while i < len(data) - 1 and iterations < max_iterations:
    iterations += 1
    # Shift-JIS first byte ranges: 0x81-0x9F, 0xE0-0xFC
    if (0x81 <= data[i] <= 0x9F or 0xE0 <= data[i] <= 0xFC):
        start = i
        count = 0
        # Limit inner loop iterations
        inner_iterations = 0
        while i < len(data) - 1 and inner_iterations < 1000:
            inner_iterations += 1
            if (0x81 <= data[i] <= 0x9F or 0xE0 <= data[i] <= 0xFC) and (0x40 <= data[i+1] <= 0xFC):
                i += 2
                count += 1
            else:
                break
        if count >= 2:  # At least 2 Japanese characters
            potential_sjis.append((start, data[start:i]))
        # Ensure we always move forward
        if i == start:
            i += 1
    else:
        i += 1

print(f"Found {len(potential_sjis)} potential Shift-JIS strings")
for idx, (pos, text) in enumerate(potential_sjis[:5]):
    print(f"\nPosition {pos}: {text[:50]}")
    try:
        decoded = text.decode('shift-jis', errors='ignore')
        print(f"  Decoded: {decoded}")
    except:
        print(f"  Could not decode")
