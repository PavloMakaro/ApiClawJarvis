text = "Йохчор гиф ыщиюбе укпцфчкшв"
text_no_spaces = text.replace(" ", "")

print("Текст:", text)
print("Без пробелов:", text_no_spaces)
print("Длина:", len(text_no_spaces))
print()

# Частота букв
freq = {}
for char in text_no_spaces:
    freq[char] = freq.get(char, 0) + 1

print("Частота букв:")
for char, count in sorted(freq.items(), key=lambda x: x[1], reverse=True):
    print(f"  {char}: {count} ({count/len(text_no_spaces)*100:.1f}%)")

print()
print("Позиции букв:")
for i, char in enumerate(text_no_spaces):
    print(f"  {i+1}: {char}")