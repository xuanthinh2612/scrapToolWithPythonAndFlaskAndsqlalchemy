import re
import json

text = """


"""

# Regex để bắt cặp (to ...)(認証コード： ...)
matches = re.findall(r'to\s+([\w+@.]+)\s+.*?認証コード：\s*(\d+)', text, flags=re.DOTALL)

# Đưa ra dict
result = {email+ "@gmail.com" : code for email , code in matches}
# Xuất ra file JSON
with open("verifyCode.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

