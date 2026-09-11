from pathlib import Path
import base64


PROJECT = Path(__file__).resolve().parents[1]
html = (PROJECT / "src" / "index.html").read_text(encoding="utf-8")
css = (PROJECT / "dist" / "styles.css").read_text(encoding="utf-8")
js = (PROJECT / "dist" / "app.js").read_text(encoding="utf-8")

for image_path in sorted((PROJECT / "dist" / "assets").glob("*.png")):
    data = base64.b64encode(image_path.read_bytes()).decode("ascii")
    js = js.replace(f"assets/{image_path.name}", f"data:image/png;base64,{data}")

html = html.replace('<link rel="stylesheet" href="styles.css">', f"<style>\n{css}\n</style>")
html = html.replace('<script src="app.js"></script>', f"<script>\n{js}\n</script>")
(PROJECT / "dist" / "index.html").write_text(html, encoding="utf-8")
print(PROJECT / "dist" / "index.html")
