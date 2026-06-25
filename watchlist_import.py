import os
import csv


def import_from_file(filepath: str) -> list:
    if not os.path.exists(filepath):
        return []
    symbols = []
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".csv":
        with open(filepath) as f:
            reader = csv.reader(f)
            for row in reader:
                for cell in row:
                    s = cell.strip().upper()
                    if s and s not in symbols:
                        symbols.append(s)
    else:
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("//"):
                    parts = line.replace(",", " ").split()
                    for p in parts:
                        s = p.upper()
                        if s and s not in symbols:
                            symbols.append(s)
    return symbols


def merge_watchlist(current: list, imported: list) -> list:
    merged = list(current)
    for s in imported:
        if s not in merged:
            merged.append(s)
    return merged
