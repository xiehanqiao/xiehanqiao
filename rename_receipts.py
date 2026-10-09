#!/usr/bin/env python3
"""批量重命名中国银行「国内支付业务收款回单」PDF。

新文件名格式：付款人名称_币种金额.pdf，例如  中兴通讯股份有限公司_CNY1765.00.pdf
同名时自动追加 _2、_3 ...

用法：
    pip install pdfplumber
    python rename_receipts.py 回单文件夹            # 直接改名
    python rename_receipts.py 回单文件夹 --dry-run  # 只预览，不改名
    python rename_receipts.py                       # 不带参数则提示输入文件夹路径
"""
import argparse
import re
import sys
from pathlib import Path

import pdfplumber

SPLIT_X = 300  # 回单左栏(收款人)/右栏(付款人)的分界 x 坐标
ILLEGAL = re.compile(r'[\\/:*?"<>|\r\n\t]')


def extract(pdf_path: Path):
    """返回 (付款人名称, 金额字符串)，失败时抛 ValueError。"""
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        words = page.extract_words(keep_blank_chars=False, use_text_flow=False)
        text = page.extract_text() or ""

    # 金额：如 "金额：CNY1,765.00" / "USD4,170.00"
    m = re.search(r"金额[：:]\s*([A-Z]{3})\s*([\d,]+\.?\d*)", text)
    if not m:
        raise ValueError("未找到金额")
    amount = f"{m.group(1)}{m.group(2).replace(',', '')}"

    # 付款人名称：取右栏中「付款人名称：」到「付款人开户行：」之间的文字（名称过长会换行）
    right = [w for w in words if w["x0"] >= SPLIT_X - 5]
    right.sort(key=lambda w: (round(w["top"]), w["x0"]))
    lines = {}
    for w in right:
        lines.setdefault(round(w["top"]), []).append(w["text"])
    ordered = ["".join(v) for _, v in sorted(lines.items())]

    name_parts, started = [], False
    for line in ordered:
        if "付款人名称" in line:
            started = True
            line = re.split(r"付款人名称[：:]", line, maxsplit=1)[1]
        elif started and "付款人开户行" in line:
            break
        elif not started:
            continue
        name_parts.append(line)
    name = "".join(name_parts).strip()
    if not name:
        raise ValueError("未找到付款人名称")
    return ILLEGAL.sub("_", name), amount


def unique_path(folder: Path, stem: str, taken: set) -> Path:
    candidate, n = folder / f"{stem}.pdf", 2
    while candidate.name.lower() in taken or candidate.exists():
        candidate = folder / f"{stem}_{n}.pdf"
        n += 1
    taken.add(candidate.name.lower())
    return candidate


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("folder", nargs="?", help="存放回单 PDF 的文件夹")
    ap.add_argument("--dry-run", action="store_true", help="只预览，不实际改名")
    args = ap.parse_args()

    folder = Path(args.folder or input("请输入回单文件夹路径：").strip().strip('"'))
    if not folder.is_dir():
        sys.exit(f"文件夹不存在：{folder}")

    pdfs = sorted(p for p in folder.iterdir() if p.suffix.lower() == ".pdf")
    ok = failed = 0
    taken = set()
    for pdf in pdfs:
        try:
            name, amount = extract(pdf)
        except Exception as e:  # 单个文件失败不影响其他文件
            print(f"[失败] {pdf.name}: {e}")
            failed += 1
            continue
        target = unique_path(folder, f"{name}_{amount}", taken)
        print(f"{pdf.name}  ->  {target.name}")
        if not args.dry_run:
            pdf.rename(target)
        ok += 1
    print(f"\n完成：成功 {ok}，失败 {failed}" + ("（预览模式，未实际改名）" if args.dry_run else ""))


if __name__ == "__main__":
    main()
