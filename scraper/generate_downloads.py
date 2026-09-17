import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent

SOURCES={
    "mcpelife":"https://mcpelife.com/download/",
    "mcpedl":"https://mcpedl.org/downloading/"
}

def readable(n):
    if n is None:return "-"
    n=float(n)
    for u in ("B","KB","MB","GB","TB"):
        if n<1024:return f"{n:.2f} {u}"
        n/=1024
    return f"{n:.2f} PB"

def size_text(n):
    return f"{n} bytes ({readable(n)})" if n is not None else "-"

def generate(source,outfile):
    data=json.loads((ROOT/"data"/f"{source}.json").read_text(encoding="utf-8"))

    lines=[
        "# 🎮 Minecraft Downloads",
        "",
        "Latest Minecraft Release and Beta download links.",
        ""
    ]

    for kind,title in [
        ("release","🟢 Release"),
        ("beta","🔵 Beta")
    ]:
        section=data.get(kind,{})
        version=section.get("version")

        lines += [
            f"## {title} — {version or 'Not found'}",
            "",
            "| File | Size | Download |",
            "|:---:|:---:|:---:|"
        ]

        files=section.get("files",[])

        if not files:
            lines += [
                "| - | - | ❌ No files found. |",
                ""
            ]
            continue

        for f in files:
            name=f.get("name","Unknown")
            size=f.get("size")
            url=f.get("url")

            if f.get("status")=="ok" and url:
                lines.append(
                    f"| {name} | {size_text(size)} | [Download]({url}) |"
                )
            else:
                error=f.get("error","Unknown error")
                lines.append(
                    f"| {name} | - | ❌ {error} |"
                )

        lines.append("")

    lines += [
        "## 🌐 Source",
        "",
        SOURCES[source],
        ""
    ]

    (ROOT/outfile).write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

generate("mcpelife","DOWNLOAD-MCPELIFE.md")
generate("mcpedl","DOWNLOAD-MCPEDL.md")
