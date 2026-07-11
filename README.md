# Networked ISAC UAV Tracking Reproduction

這個 repo 是論文 *Networked ISAC-Based UAV Tracking and Handover Toward Low-Altitude Economy* 的中文學習筆記與 Python 復現工程。

目標不是一次性精確複製所有論文圖，而是分層復現：

1. 先復現 VSC 幾何、UAV trajectory、Table I 量測向量、集中式 EKF、多 UAV association、PBS handover、VSC handover。
2. 再把 analytic noisy measurement 逐步替換成 OFDM echo、MTI、MUSIC、multi-target SVD pairing。
3. 最後用 Section V 的 Fig. 6-13 對照表、summary CSV 和中文報告檢查本地結果與論文文字數值的差距。

## Environment

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

依賴目前保持精簡：

- `numpy`
- `scipy`
- `matplotlib`

## Quick Start

先跑測試：

```bash
. .venv/bin/activate
python -m unittest discover -s tests
```

生成 Section V 的 smoke reproduction：

```bash
python main.py --scenario section-v --monte-carlo 2 --steps 60
```

這會輸出：

- `outputs/section_v_summary.csv`：Fig. 6-13 的本地 RMSE、論文 RMSE、delta。
- `notes/section_v_report.md`：中文可讀的 Section V 復現報告。
- `notes/figure_reproduction_map.md`：論文圖、CLI、輸出圖與代碼位置的對照。

## Main CLI

```bash
python main.py --scenario multi
python main.py --scenario blockage
python main.py --scenario vsc
python main.py --scenario music
python main.py --scenario music-measurement
python main.py --scenario detection-rmse --monte-carlo 8
python main.py --scenario figure-map
python main.py --scenario section-v --monte-carlo 2 --steps 60
```

常用選項：

- `--measurement-source analytic|music`：tracking 場景預設使用 analytic noisy measurement；改成 `music` 後會用目前的 MTI/MUSIC-backed measurement generator。
- `--steps N`：tracking time slots。
- `--monte-carlo N`：detection RMSE 的 Monte Carlo 次數。
- `--no-plots`：跳過 PNG 生成，但仍保留 CSV/report 類輸出。

## Reading Path

建議按下面順序閱讀：

1. `notes/beginner_python_thinking_guide.md`：給基礎 Python 新手的思考路線，先學會怎麼拆問題。
2. `examples/beginner_ekf_walkthrough.py`：可單獨執行的小型 EKF 教學範例，代碼有細節註釋。
3. `notes/paper_notes.md`：中文主筆記，先建立 VSC、量測、EKF、handover、MUSIC 的大圖。
4. `notes/formula_implementation_map.md`：逐項查看論文公式/算法對應到哪個 Python 模組、函數與變量。
5. `notes/figure_reproduction_map.md`：查看 Fig. 6-13 對應的 CLI、輸出圖與目前限制。
6. `notes/section_v_report.md`：查看最近一次 Section V smoke reproduction 的中文結果報告。
7. `outputs/section_v_summary.csv`：查看本地 RMSE、論文文字 RMSE 和 delta。

## Code Structure

- `isac_uav/geometry.py`：BS/VSC 幾何、球座標/直角座標、Table I 量測函數。
- `isac_uav/trajectory.py`：truncated Gaussian UAV trajectory 和 sharp turn。
- `isac_uav/measurement.py`：analytic noisy measurement、blockage 後的 active components。
- `isac_uav/ekf.py`：集中式 EKF、常速度模型、數值 Jacobian、可變維度 update。
- `isac_uav/handover.py`：PBS handover、VSC buffer handover。
- `isac_uav/signal_music.py`：OFDM echo、MTI、angle MUSIC、delay/Doppler MUSIC、SVD pairing。
- `isac_uav/music_measurement.py`：把 MUSIC estimate 接回 Table I 的 12 維量測。
- `isac_uav/detection_experiment.py`：Fig. 6-style detection RMSE vs SNR。
- `isac_uav/experiments.py`：multi/blockage/vsc tracking experiment 主流程。
- `isac_uav/reproduction_suite.py`：Fig. 6-13 對照表。
- `isac_uav/section_v_suite.py`：Section V batch runner、summary CSV、中文 report。

## Current Reproduction Status

已完成：

- VSC / adjacent VSC 幾何與 paper-style `1-1`、`2-3` label。
- Table I 12 維量測向量。
- EKF tracking with variable-dimensional update。
- PBS handover：最近未遮擋 BS、PBS blockage 時切換。
- VSC handover：buffer 區交替 tracking，並使用 active VSC 幾何做 measurement / EKF update。
- OFDM echo、MTI、MUSIC single-target estimate。
- Multi-target distance-Doppler MUSIC peaks + Algorithm 1-style SVD pairing。
- Fig. 6-13 的 CLI、輸出圖、summary CSV 和中文 report。

仍是近似或待加強：

- Fig. 6 預設 Monte Carlo 很小，只適合 smoke run；論文使用 `N_MC=10000`。
- Multi-UAV angle MUSIC 使用 prediction-gated window，還不是完全無先驗的全局 angle peak association。
- Blockage 目前是 scripted blockage state，不是從 missed MUSIC peak region 自動偵測。
- VSC handover 已使用 active VSC 幾何，但完整 transceiver sector beam pattern 仍是幾何近似。

## Verification

目前主要驗證命令：

```bash
. .venv/bin/activate
python -m unittest discover -s tests
python -m py_compile main.py isac_uav/*.py tests/*.py
python main.py --scenario section-v --monte-carlo 1 --steps 24 --no-plots
```

`outputs/` 被 `.gitignore` 忽略，因為圖和 CSV 都可以由 CLI 重新生成。
