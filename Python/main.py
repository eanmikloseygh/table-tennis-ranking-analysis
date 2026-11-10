
from pathlib import Path
import re
import pandas as pd

INPUT_DIR = Path(
    r"C:\Users\leosp\Downloads\Compressed\Table-Tennis-Rankings-main"
    r"\Table-Tennis-Rankings-main\history"
)

OUTPUT_FILE = Path("rankings.csv")

# Matches a row even when fields contain ? or are empty.
ROW_PATTERN = re.compile(
    r'\[(\d+)\]\s*,\s*'
    r'\[#name\("([^"]*)"\)\]\s*,\s*'
    r'\[#age\(([^)]*)\)\]\s*,\s*'
    r'\[#assoc\("([^"]*)"\)\]\s*,\s*'
    r'\[(.*?)\]\s*,\s*'
    r'\[(.*?)\]\s*,\s*'
    r'\[(.*?)\]\s*,\s*'
    r'\[(.*?)\]\s*,\s*'
    r'\[#delta\(([^)]*)\)\]',
    re.DOTALL
)


def clean_value(value):
    """Turn unknown markers into missing values."""
    if value is None:
        return None

    value = value.strip()

    if value in {"", "?", "??", "None", "null"}:
        return None

    return value


def extract_wrapped_value(value, pattern):
    """Extract a field's value; return None if it is unknown."""
    value = clean_value(value)
    if value is None:
        return None

    match = re.fullmatch(pattern, value)
    if not match:
        return None

    return clean_value(match.group(1))


def parse_int(value):
    """Convert known numeric values to integers."""
    value = clean_value(value)

    if value is None:
        return None

    try:
        return int(value)
    except (ValueError, TypeError):
        return None


records = []
files = sorted(INPUT_DIR.rglob("MS-*.typ"))

print(f"Found {len(files)} men's ranking files.")

for file in files:
    year = file.parent.name
    month_match = re.fullmatch(r"MS-(\d{2})", file.stem)

    if not re.fullmatch(r"\d{4}", year) or not month_match:
        print(f"Skipping unexpected path: {file}")
        continue

    month = int(month_match.group(1))

    if not 1 <= month <= 12:
        print(f"Skipping invalid month: {file}")
        continue

    date = f"{year}-{month:02d}"
    content = file.read_text(
        encoding="utf-8-sig",
        errors="replace"
    )

    matches = list(ROW_PATTERN.finditer(content))

    if not matches:
        print(f"WARNING: No player rows found in {file.name}")
        continue

    for match in matches:
        (
            rank, player, age, country,
            hand, grip, style, rating, delta
        ) = match.groups()

        player = clean_value(player)

        # Rank and player name are required; other fields may be missing.
        if player is None:
            continue

        records.append({
            "date": date,
            "rank": int(rank),
            "player": player,
            "age": parse_int(age),
            "country": clean_value(country),
            "hand": clean_value(hand.lstrip("#")),
            "grip": clean_value(grip.lstrip("#")),
            "style": clean_value(style.lstrip("#")),
            "rating": parse_int(rating.strip("*")),
            "delta": parse_int(delta),
            "source_file": str(file),
        })

if not records:
    raise RuntimeError(
        "No rows extracted. Check INPUT_DIR and the .typ row format."
    )

df = pd.DataFrame(records)

# Sort chronologically, then by rank.
df = df.sort_values(
    ["date", "rank"]
).reset_index(drop=True)

df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)

print(f"\nExtracted {len(df):,} player-ranking rows.")
print(f"Saved CSV to: {OUTPUT_FILE.resolve()}")
print(f"Files contributing data: {df['source_file'].nunique()}")
print(f"Date range: {df['date'].min()} to {df['date'].max()}")

print("\nMissing values per column:")
print(df.isna().sum().to_string())

print("\nFirst 10 rows:")
print(df.head(10).to_string(index=False))

print("\nRows per ranking month:")
print(df.groupby("date").size().to_string())


