#!/usr/bin/env python3
"""把 wiki/ 下的手册类 Markdown 合成一份自包含 HTML。

用法：./scripts/build-handbook.py
产物：output/reports/知识库使用方法.html（output/ 不入库）

只读源文件，不修改任何笔记。改完手册重跑一次即可。
"""

import html
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "reports" / "知识库使用方法.html"

# 要合成的源文件，顺序即章节顺序
SOURCES = [
    ROOT / "wiki" / "知识库操作手册.md",
    ROOT / "wiki" / "知识库安装记录.md",
]

CALLOUT = {
    "WARNING": ("warn", "注意"),
    "NOTE": ("note", "说明"),
    "TIP": ("tip", "提示"),
    "IMPORTANT": ("warn", "重要"),
}

CSS = """
  :root{
    --fg:#1f2328; --fg-soft:#57606a; --bg:#ffffff; --bg-soft:#f6f8fa;
    --border:#d0d7de; --accent:#0969da; --accent-soft:#ddf4ff;
    --warn-bg:#fff8c5; --warn-border:#d4a72c;
    --note-bg:#ddf4ff; --note-border:#54aeff;
    --tip-bg:#dafbe1; --tip-border:#4ac26b;
  }
  .dark{
    --fg:#e6edf3; --fg-soft:#8b949e; --bg:#0d1117; --bg-soft:#161b22;
    --border:#30363d; --accent:#4493f8; --accent-soft:#121d2f;
    --warn-bg:#2e2a1a; --warn-border:#9e6a03;
    --note-bg:#121d2f; --note-border:#1f6feb;
    --tip-bg:#12261e; --tip-border:#238636;
  }
  *{box-sizing:border-box}
  body{
    margin:0; padding:3rem 1.25rem 6rem;
    background:var(--bg); color:var(--fg);
    font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB",
      "Microsoft YaHei","Source Han Sans SC","Noto Sans CJK SC",sans-serif;
    font-size:16px; line-height:1.75;
  }
  main{max-width:46rem; margin:0 auto}
  h1{font-size:1.85rem; line-height:1.3; margin:0 0 .5rem}
  h1.part{margin:4rem 0 1rem; padding-bottom:.5rem; border-bottom:2px solid var(--border)}
  h2{font-size:1.28rem; margin:3rem 0 1rem; padding-bottom:.4rem;
     border-bottom:1px solid var(--border)}
  h3{font-size:1.05rem; margin:2rem 0 .6rem}
  p{margin:.9rem 0}
  a{color:var(--accent)}
  code{font-family:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
       font-size:.875em; background:var(--bg-soft); padding:.15em .38em;
       border-radius:5px; border:1px solid var(--border)}
  pre{background:var(--bg-soft); border:1px solid var(--border); border-radius:8px;
      padding:1rem 1.1rem; overflow-x:auto; margin:1rem 0}
  pre code{background:none; border:none; padding:0; font-size:.86rem; line-height:1.6}
  .lede{font-size:1.05rem; color:var(--fg-soft); margin:.4rem 0 0}
  .meta{color:var(--fg-soft); font-size:.85rem; margin:1.2rem 0 0;
        padding-bottom:1.5rem; border-bottom:1px solid var(--border)}
  table{border-collapse:collapse; width:100%; margin:1.2rem 0; font-size:.93rem}
  th,td{border:1px solid var(--border); padding:.55rem .75rem; text-align:left; vertical-align:top}
  th{background:var(--bg-soft); font-weight:600}
  tbody tr:nth-child(even){background:var(--bg-soft)}
  .box{border-left:4px solid; border-radius:6px; padding:.85rem 1.1rem; margin:1.2rem 0}
  .box p{margin:.4rem 0} .box p:first-child{margin-top:0} .box p:last-child{margin-bottom:0}
  .box .box-title{font-weight:600}
  .note{background:var(--note-bg); border-color:var(--note-border)}
  .warn{background:var(--warn-bg); border-color:var(--warn-border)}
  .tip{background:var(--tip-bg); border-color:var(--tip-border)}
  ol,ul{padding-left:1.6rem; margin:.9rem 0} li{margin:.35rem 0}
  hr{border:none; border-top:1px solid var(--border); margin:2.5rem 0}
  footer{margin-top:4rem; padding-top:1.5rem; border-top:1px solid var(--border);
         color:var(--fg-soft); font-size:.85rem}
  @media print{
    body{padding:0; font-size:11pt}
    h1.part{page-break-before:always}
    h2{page-break-after:avoid}
    table,pre,.box,li{page-break-inside:avoid}
  }
  @media (max-width:600px){
    body{padding:2rem 1rem 4rem} h1{font-size:1.5rem}
    th,td{padding:.45rem .55rem; font-size:.86rem}
  }
"""


def inline(text: str) -> str:
    """行内标记 → HTML。先转义，再还原允许的标记。"""
    out = html.escape(text, quote=False)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    # [[目标]] 或 [[目标|显示文本]] → 纯文本（HTML 里无法跳转，保留可读性）
    out = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", out)
    out = re.sub(r"\[\[([^\]]+)\]\]", r"\1", out)
    out = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', out)
    out = re.sub(r"&lt;(https?://[^&]+?)&gt;", r'<a href="\1">\1</a>', out)
    return out


def render(lines):
    """Markdown 行列表 → HTML 片段。覆盖手册实际用到的语法。"""
    out, i, n = [], 0, len(lines)
    while i < n:
        ln = lines[i]

        # 代码块
        if ln.startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].startswith("```"):
                buf.append(html.escape(lines[i]))
                i += 1
            i += 1
            out.append("<pre><code>" + "\n".join(buf) + "</code></pre>")
            continue

        # 表格：表头 + 分隔行
        if ln.startswith("|") and i + 1 < n and re.match(r"^\|[\s:|-]+\|$", lines[i + 1]):
            rows = []
            while i < n and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head, body = rows[0], rows[2:]
            t = ["<table><thead><tr>"]
            t += [f"<th>{inline(c)}</th>" for c in head]
            t.append("</tr></thead><tbody>")
            for r in body:
                t.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            t.append("</tbody></table>")
            out.append("".join(t))
            continue

        # 引用块 / callout
        if ln.startswith(">"):
            buf = []
            while i < n and lines[i].startswith(">"):
                buf.append(lines[i].lstrip(">").strip())
                i += 1
            m = re.match(r"^\[!(\w+)\]\s*(.*)$", buf[0]) if buf and buf[0] else None
            if m and m.group(1).upper() in CALLOUT:
                cls, label = CALLOUT[m.group(1).upper()]
                rest = [m.group(2)] + buf[1:]
                body = " ".join(x for x in rest if x).strip()
                out.append(
                    f'<div class="box {cls}"><p class="box-title">{label}</p>'
                    f"<p>{inline(body)}</p></div>"
                )
            else:
                body = " ".join(x for x in buf if x).strip()
                out.append(f'<div class="box note"><p>{inline(body)}</p></div>')
            continue

        # 标题
        m = re.match(r"^(#{1,4})\s+(.*)$", ln)
        if m:
            lvl, txt = len(m.group(1)), m.group(2).strip()
            if lvl == 1:
                out.append(f'<h1 class="part">{inline(txt)}</h1>')
            else:
                tag = f"h{min(lvl, 3)}"
                out.append(f"<{tag}>{inline(txt)}</{tag}>")
            i += 1
            continue

        # 水平线
        if re.match(r"^-{3,}$", ln.strip()):
            out.append("<hr>")
            i += 1
            continue

        # 有序列表
        if re.match(r"^\d+\.\s", ln):
            items = []
            while i < n and re.match(r"^\d+\.\s", lines[i]):
                items.append(re.sub(r"^\d+\.\s", "", lines[i]))
                i += 1
            out.append("<ol>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ol>")
            continue

        # 无序列表
        if re.match(r"^[-*]\s", ln):
            items = []
            while i < n and re.match(r"^[-*]\s", lines[i]):
                items.append(re.sub(r"^[-*]\s", "", lines[i]))
                i += 1
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>")
            continue

        # 空行
        if not ln.strip():
            i += 1
            continue

        # 段落：连续非空行合并
        buf = []
        while i < n and lines[i].strip() and not re.match(
            r"^(#{1,4}\s|>|```|\||[-*]\s|\d+\.\s|-{3,}$)", lines[i]
        ):
            buf.append(lines[i].strip())
            i += 1
        if buf:
            out.append(f"<p>{inline(' '.join(buf))}</p>")
        else:
            i += 1
    return "\n".join(out)


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2]
    return text


def main() -> int:
    missing = [str(p) for p in SOURCES if not p.exists()]
    if missing:
        print("找不到源文件：" + ", ".join(missing), file=sys.stderr)
        return 1

    parts = []
    for src in SOURCES:
        parts.append(render(strip_frontmatter(src.read_text(encoding="utf-8")).splitlines()))

    body = "\n".join(parts)
    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CS_StudyNotes 知识库 · 使用方法</title>
<style>{CSS}</style>
</head>
<body>
<main>

<h1>CS_StudyNotes 知识库 · 使用方法</h1>
<p class="lede">剪藏 → 判定 → 写正文 → 定期体检。这份文档讲的是「怎么用」。</p>
<p class="meta">生成日期：{date.today().isoformat()}　·　由 scripts/build-handbook.py 从 wiki/ 手册自动合成，请勿手改</p>

{body}

<footer>
<p>本文件是 <code>wiki/知识库操作手册.md</code> 与 <code>wiki/知识库安装记录.md</code> 的合并视图，放在 <code>output/reports/</code>——该目录不入库，可随时删除重建。</p>
<p>正文层永远以 <code>01_</code>~<code>04_</code> 为准。</p>
</footer>

</main>
<script>
  try{{
    if(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches){{
      document.documentElement.classList.add('dark');
    }}
  }}catch(e){{}}
</script>
</body>
</html>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(doc, encoding="utf-8")
    print(f"已生成 {OUT.relative_to(ROOT)}  ({len(doc)} 字符)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
