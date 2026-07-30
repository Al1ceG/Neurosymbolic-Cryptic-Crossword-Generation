

import pandas as pd
from pathlib import Path
import seaborn as sns
import matplotlib.pyplot as plt

# -------------------------
# 1. Load all datasets
# -------------------------

data_dir = "evaluator/evaluation_data/"
datapaths = ["times.csv", "gpt_DSL.csv", "gpt_text_batch.csv", "gpt_text.csv"]

dfs = []
for csv_path in datapaths:
    df = pd.read_csv(data_dir + csv_path)
    df["dataset"] = csv_path  # filename = dataset name
    dfs.append(df)

all_data = pd.concat(dfs, ignore_index=True)

# -------------------------
# 2. Define metrics & clue types
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

clue_types = [
    "hidden",
    "charade",
    "container",
    "anagram",
    "deletion",
    "double_definition"
]

# Optional: ensure consistent ordering
all_data["clue_type"] = pd.Categorical(
    all_data["clue_type"],
    categories=clue_types,
    ordered=True
)

# -------------------------
# 3. Compute MEDIAN per dataset × clue_type × metric
# -------------------------

median_scores = (
    all_data
    .groupby(["dataset", "clue_type"])[metric_cols]
    .median()
    .reset_index()
)

# -------------------------
# 4. Convert to long format for seaborn
# -------------------------

long_medians = median_scores.melt(
    id_vars=["dataset", "clue_type"],
    value_vars=metric_cols,
    var_name="metric",
    value_name="score"
)

print(long_medians)

# -------------------------
# 5. Plot: faceted bar charts
#    Each metric = subplot
#    Each dataset = x-axis
#    Each clue type = bar (hue)
# -------------------------

sns.set_theme(style="whitegrid")

g = sns.catplot(
    data=long_medians,
    x="dataset",
    y="score",
    hue="clue_type",
    col="metric",
    kind="bar",
    col_wrap=2,
    sharey=False,
    sharex=False,
    height=3,
    aspect=2
)

for ax in g.axes.flatten():
    ax.tick_params(
        axis="x",
        labelsize=8
    )

# Remove seaborn's auto legend
if g._legend is not None:
    g._legend.remove()

g.add_legend(
    title="Clue type",
    bbox_to_anchor=(0.78, 0.12),
    loc="lower right",
    frameon=True,
    ncol=2
)

g.fig.subplots_adjust(
    top=0.93,
    right=0.82,    
    hspace=0.35,
    wspace=0.25
)

g.set_titles("{col_name}")
g.set_axis_labels("", "Median score")

g.fig.savefig(
    "bar_charts/all_charts",
    dpi=300,
    bbox_inches="tight"
)

plt.show()


