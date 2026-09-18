# The existing runner's input contract

Quoted from the read-only checkout at `../harness_benchmark` on 2026-09-18. Treat that
checkout as authoritative; this file is a summary plus the parts that create leakage risk.

## Layout

From `datasets/common.py`:

```
data/prepared/<name>/
    public/train.csv      labeled training data   (copied into the agent's workdir)
    public/eval.csv       labeled evaluation data (copied into the agent's workdir; the
                                                    agent's keep/discard signal)
    private/holdout.csv   labeled holdout         (NEVER copied into a workdir; used only
                                                    by `bench eval`)
    meta.json             target column, positive label, id columns, split description,
                          row counts
```

The agent sees train + eval. **The benchmark score is AUC on the holdout.**

`write_split()` writes those three files, then extends `meta.json` with `name`,
`columns` (from the train frame), `rows` and `positive_rate` per split, where
`positive_rate` is `(df[target] == positive_label).mean()`.

## What the runner reads

`task_template/train.py`:

```python
TASK = json.load(open("task.json"))
TARGET = TASK["target"]
POSITIVE = TASK["positive_label"]
ID_COLS = TASK.get("id_columns", [])

train = pd.read_csv("data/train.csv")
evald = pd.read_csv("data/eval.csv")

feature_cols = [c for c in train.columns if c not in ID_COLS + [TARGET]]
```

`task_template/validate.py`:

```python
df = pd.read_csv("data/eval.csv")
y = (df[task["target"]] == task["positive_label"]).astype(int).to_numpy()
p = np.asarray(fn(df.drop(columns=[task["target"]])), dtype=float).ravel()
```

## The three consequences that matter

1. **Every non-target column is model input.** `feature_cols` excludes only the declared id
   columns and the target, and `predict_proba` receives the frame with only the target
   dropped. A declared feature list is not a control: anything you ship, a solver can use.
   An answer-source column must be absent from the files, not merely omitted from a list.
2. **`meta.json` must agree with the files.** `rows` and `positive_rate` are read as facts
   about the data. A stale or hand-written `meta.json` is a silent inconsistency.
3. **`positive_label` is a value, not a position.** `(df[target] == positive_label)` means
   the target may be any comparable value, and a label written as the string `"1"` while
   `positive_label` is the integer `1` can silently compare false. Keep the written values
   and the declared label the same type, and let the gate check the rate it computes against
   the declared one.

## Local expectations

The reference datasets (`airline`, `fraud`, `credit`) are prepared by
`datasets/prepare_*.py`, which need `polars` and, for two of them, network access or Kaggle
credentials. A fresh clone has the preparation scripts and saved baseline JSON but no
`data/prepared/` datasets. Preparation belongs on a worker; the coordinator keeps code,
evidence and checksums.

## Related runner behaviour worth knowing

- The runner scores **binary classification** only, and the saved `fraud` baseline is about
  0.863 AUC (the ~0.997 figure in the original spec came from a different model using
  selected features).
- The holdout may be published; what matters during an evaluation run is that it stays
  outside the evaluated agent's workspace.
- A cell whose final `train.py` fails the contract has an empty `holdout_auc` and the reason
  in `holdout_error`; it is never silently scored.
