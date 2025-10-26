from bs4 import BeautifulSoup

html = """<ul class="content-alignment ul-reset ..."> ... (đoạn HTML bạn dán vào đây) ... </ul>"""

soup = BeautifulSoup(html, "html.parser")

colors = []

# Mỗi <button> là một màu
for btn in soup.select("ul li button.chip"):
    color_name = btn.find("img")["alt"] if btn.find("img") else None
    color_img = btn.find("img")["src"] if btn.find("img") else None
    color_id = btn.get("id")
    color_value = btn.get("value")

    colors.append({
        "name": color_name,
        "id": color_id,
        "value": color_value,
        "image": color_img
    })

for c in colors:
    print(c)
