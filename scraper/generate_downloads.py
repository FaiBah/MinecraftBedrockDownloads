import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SOURCES = {
    "mcpelife": "https://mcpelife.com/download/",
    "mcpedl": "https://mcpedl.org/downloading/",
}

SECTIONS = {
    "release": "🟢 Release",
    "beta": "🔵 Beta",
}


def size(n):
    if n is None:
        return "Unknown"

    value = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024:
            return f"{value:.2f} {unit} ({n:,} bytes)"
        value /= 1024

    return f"{value:.2f} PB ({n:,} bytes)"


def generate(source):
    data = json.loads(
        (ROOT / "data" / f"{source}.json").read_text(encoding="utf-8")
    )

    lines = [
        "# 🎮 Minecraft Downloads",
        "",
        "> Latest **Minecraft Release & Beta** download links.",
        "",
        "---",
        "",
    ]

    for kind, title in SECTIONS.items():
        section = data.get(kind, {})
        files = section.get("files", [])

        lines += [
            f"## {title}",
            "",
            f"### `{section.get('version') or 'Not found'}`",
            "",
        ]

        if not files:
            lines += ["> ⚠️ **No files found.**", ""]
        else:
            for file in files:
                name = file.get("name", "Unknown")
                url = file.get("url")

                if file.get("status") == "ok" and url:
                    lines += [
                        f"> 📦 **{name}**  ",
                        f"> **Size:** `{size(file.get('size'))}`  ",
                        f"> [⬇️ Download]({url})",
                        "",
                    ]
                else:
                    lines += [
                        f"> ⚠️ **{name}**  ",
                        f"> **Status:** {file.get('error', 'Unknown error')}",
                        "",
                    ]

        lines += ["---", ""]

    lines += [
        "## 🌐 Source",
        "",
        f"🔗 [{source.upper()}]({SOURCES[source]})",
        "",
    ]

    (ROOT / f"DOWNLOAD-{source.upper()}.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


for source in SOURCES:
    generate(source)
