def atbash_decrypt(text):
    # Русский алфавит
    alphabet = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
    reverse_alphabet = alphabet[::-1]

    result = ""
    for char in text:
        if char.isalpha():
            lower_char = char.lower()
            if lower_char in alphabet:
                idx = alphabet.index(lower_char)
                decrypted_char = reverse_alphabet[idx]
                if char.isupper():
                    result += decrypted_char.upper()
                else:
                    result += decrypted_char
            else:
                result += char
        else:
            result += char
    return result

text = "Йохчор гиф ыщиюбе укпцфчкшв"
print("Оригинал:", text)
print("Атбаш:", atbash_decrypt(text))