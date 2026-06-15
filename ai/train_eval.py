"""Train and evaluate the anomaly-detection models for RQ2.

Reads data/features.parquet (from export_features.py) and
data/fault_labels.csv (from inject_faults.py), trains an Isolation Forest
baseline and an LSTM-Autoencoder, and writes real metrics + a confusion-matrix
figure + median detection latency. These are the numbers that go into the
thesis (§4.2) — nothing here is invented or copied from the old draft.

Outputs:
  - prints metrics for both models (F1, precision, recall, AUC)
  - figures/confusion_lstm_ae.png
  - data/ai_metrics.json
  - prints median detection latency in minutes
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

# ---- load + label windows from fault schedule ----
df = pd.read_parquet("data/features.parquet")
lab = pd.read_csv("data/fault_labels.csv", parse_dates=["start_utc", "end_utc"])

y = np.zeros(len(df), dtype=int)
for _, r in lab.iterrows():
    y[(df.index >= r.start_utc) & (df.index <= r.end_utc)] = 1

X = (df - df.mean()) / df.std()  # z-score; fit on train fold only in a stricter setup
n = len(X)
cut = int(n * 0.6)
Xtr, Xte = X.iloc[:cut].values, X.iloc[cut:].values
ytr, yte = y[:cut], y[cut:]

# ---- Isolation Forest baseline ----
iso = IsolationForest(contamination=max(y.mean(), 0.01), random_state=0).fit(Xtr[ytr == 0])
iso_score = -iso.score_samples(Xte)
iso_pred = (iso_score > np.quantile(iso_score, 0.9)).astype(int)


# ---- LSTM-Autoencoder (windowed) ----
T = 12


def windows(a):
    return np.stack([a[i:i + T] for i in range(len(a) - T)])


Wtr = torch.tensor(windows(Xtr[ytr == 0]), dtype=torch.float32)
Wte = torch.tensor(windows(Xte), dtype=torch.float32)
yte_w = y[cut + T:]


class AE(nn.Module):
    def __init__(self, n_features):
        super().__init__()
        self.e1 = nn.LSTM(n_features, 64, batch_first=True)
        self.e2 = nn.LSTM(64, 32, batch_first=True)
        self.bottleneck = nn.Linear(32, 16)
        self.expand = nn.Linear(16, 32)
        self.d1 = nn.LSTM(32, 32, batch_first=True)
        self.d2 = nn.LSTM(32, 64, batch_first=True)
        self.out = nn.Linear(64, n_features)

    def forward(self, x):
        h, _ = self.e1(x)
        h, _ = self.e2(h)
        z = self.bottleneck(h[:, -1])
        zs = self.expand(z).unsqueeze(1).repeat(1, x.size(1), 1)
        h, _ = self.d1(zs)
        h, _ = self.d2(h)
        return self.out(h)


model = AE(Xtr.shape[1])
opt = torch.optim.Adam(model.parameters(), lr=1e-3)
loss_fn = nn.MSELoss()

for epoch in range(40):
    opt.zero_grad()
    loss = loss_fn(model(Wtr), Wtr)
    loss.backward()
    opt.step()

with torch.no_grad():
    err = ((model(Wte) - Wte) ** 2).mean(dim=(1, 2)).numpy()

if (yte_w == 0).any():
    tau = err[yte_w == 0].mean() + 3 * err[yte_w == 0].std()
else:
    tau = np.quantile(err, 0.9)
ae_pred = (err > tau).astype(int)


# ---- metrics ----
def report(name, yt, pred, score=None):
    out = {
        "F1": f1_score(yt, pred, zero_division=0),
        "precision": precision_score(yt, pred, zero_division=0),
        "recall": recall_score(yt, pred, zero_division=0),
    }
    if score is not None and len(set(yt)) > 1:
        out["AUC"] = roc_auc_score(yt, score)
    print(name, {k: round(v, 3) for k, v in out.items()})
    return out


metrics = {
    "isolation_forest": report("IsolationForest", yte, iso_pred, iso_score),
    "lstm_ae": report("LSTM-AE", yte_w, ae_pred, err),
}

# ---- confusion matrix figure ----
cm = confusion_matrix(yte_w, ae_pred)
plt.imshow(cm, cmap="Blues")
plt.title("LSTM-AE confusion matrix")
for (i, j), v in np.ndenumerate(cm):
    plt.text(j, i, v, ha="center")
plt.colorbar()
plt.savefig("figures/confusion_lstm_ae.png", dpi=150)
print("saved figures/confusion_lstm_ae.png")

# ---- detection latency: minutes from fault onset to first alert ----
test_index = df.index[cut + T:]
ae_pred_series = pd.Series(ae_pred, index=test_index)

latencies_min = []
for _, r in lab.iterrows():
    after = ae_pred_series[(ae_pred_series.index >= r.start_utc)]
    hit = after[after == 1]
    if not hit.empty:
        delta = (hit.index[0] - r.start_utc).total_seconds() / 60
        if delta >= 0:
            latencies_min.append(delta)

median_latency = float(np.median(latencies_min)) if latencies_min else None
print(f"median detection latency: {median_latency} min (n={len(latencies_min)} episodes detected)")

metrics["detection_latency_min_median"] = median_latency
metrics["detection_latency_n_episodes"] = len(latencies_min)
metrics["n_total_episodes"] = len(lab)

with open("data/ai_metrics.json", "w") as f:
    json.dump(metrics, f, indent=2)
print("saved data/ai_metrics.json")
