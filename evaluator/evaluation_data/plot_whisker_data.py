import pandas as pd
from pathlib import Path
import seaborn as sns
import matplotlib.pyplot as plt

# -------------------------
# 1. Load all datasets
# -------------------------

data_dir = Path("evaluator/evaluation_data")

dfs = []
for csv_path in data_dir.glob("*.csv"):
    df = pd.read_csv(csv_path)
    df["dataset"] = csv_path.stem
    dfs.append(df)

all_data = pd.concat(dfs, ignore_index=True)

# -------------------------
# 2. Define metrics
# -------------------------

metric_cols = [
    "num_chars",
    "num_words",
    "perplexity",
    "thematic_fit",
    "semantic_distance",
    "polysemy",
    "llm_wit",
    "llm_uniqueness",
    "llm_fairness",
    "llm_surface_read",
    "llm_overall"
]

# -------------------------
# 3. Convert to long format
#    (NO aggregation)
# -------------------------

long_data = all_data.melt(
    id_vars=["dataset"],
    value_vars=metric_cols,
    var_name="metric",
    value_name="score"
)

print(long_data)

# -------------------------
# 4. Plot: faceted boxplots
#    Each metric = subplot
#    Each dataset = x-axis
# -------------------------

sns.set_theme(style="whitegrid")

g = sns.catplot(
    data=long_data,
    x="dataset",
    y="score",
    col="metric",
    kind="box",
    col_wrap=2,
    sharey=False,
    sharex=False,
    height=3,
    aspect=2
)

for ax in g.axes.flatten():
    ax.tick_params(axis="x", labelsize=8)
    ax.tick_params(axis="y", labelsize=8)

g.set_titles("{col_name}")
g.set_axis_labels("", "Score")

g.fig.subplots_adjust(
    top=0.93,
    hspace=0.35,
    wspace=0.25
)

g.fig.savefig(
    "boxplots/dataset_boxplots_by_metric",
    dpi=300,
    bbox_inches="tight"
)

plt.show()
