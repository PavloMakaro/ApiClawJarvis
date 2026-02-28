def caesar_decrypt(text, shift):
    result = ""
    for char in text:
        if char.isalpha():
            if char.isupper():
                base = ord('А')
            else:
                base = ord('а')

            # Русский алфавит
            if char.lower() in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя':
                shifted = (ord(char) - base - shift) % 33
                result += chr(base + shifted)
            else:
                result += char
        else:
            result += char
    return result

text = "Йохчор гиф ыщиюбе укпцфчкшв"
print("Оригинал:", text)
print()

# Попробуем разные сдвиги
for shift in range(1, 33):
    decrypted = caesar_decrypt(text, shift)
    print(f"Сдвиг {shift:2d}: {decrypted}")