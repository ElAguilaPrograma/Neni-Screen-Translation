import re

class NormalizeText:
    def normalize_text(self, text):
        text = text.replace("\n", " ")
        text = re.sub(r'[^\x00-\x7F]+', ' ', text) # Remover no-ASCII si es inglés puro
        text = " ".join(text.split())
        
        return text.strip()