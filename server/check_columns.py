import pandas as pd

df = pd.read_csv("data/processed_data.csv", nrows=0)
cols = list(df.columns)

print(f"总列数: {len(cols)}\n")
for i, col in enumerate(cols):
    print(f"{i:2d}: {col}")
