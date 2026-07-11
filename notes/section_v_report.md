# Section V 復現報告

這份報告由 `python main.py --scenario section-v` 自動生成，目的是把本地 Python 復現結果整理成可閱讀的中文筆記。

## 運行設定

- tracking steps: `24`
- measurement interval dt: `0.2` s
- seed: `4`
- tracking measurement source: `analytic`
- detection Monte Carlo: `1`

## 圖表對照

| 論文圖 | 場景 | 本地 RMSE x/y/z | 本地 RMSE vx/vy/vz | single-BS baseline | 論文 RMSE x/y/z | 論文 RMSE vx/vy/vz | delta 重點 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Fig. 6 | detection-rmse | - | - | - | - | - | - |
| Fig. 7-9 | multi | 0.719838 / 0.566279 / 0.446545 m | 1.566012 / 1.150561 / 1.120515 m/s | pos 0.759458 / 0.926798 / 0.766997 m; vel 1.445089 / 1.913240 / 1.776123 m/s | 0.350000 / 0.390000 / 0.430000 m | 0.980000 / 1.270000 / 0.510000 m/s | 0.369838 / 0.176279 / 0.016545 / 0.586012 / -0.119439 / 0.610515 |
| Fig. 10-11 | blockage | 0.609707 / 0.589085 / 0.487321 m | 1.273503 / 1.173341 / 1.253928 m/s | - | - | - | No complete numeric RMSE benchmark is stated in the paper text for this scenario. |
| Fig. 12-13 | vsc | 0.687323 / 0.593010 / 0.660734 m | 1.029940 / 1.483947 / 1.061451 m/s | - | 0.320000 / 0.370000 / 0.520000 m | 1.120000 / 1.460000 / 0.670000 m/s | 0.367323 / 0.223010 / 0.140734 / -0.090060 / 0.023947 / 0.391451 |

## 解讀

- Fig. 6 對應 detection RMSE vs SNR；本地預設 Monte Carlo 次數較小，用於 smoke reproduction，不應直接宣稱等同論文的 `N_MC=10000`。
- Fig. 7-9 的 `multi` 場景可直接和論文 Fig. 8 的平均 RMSE 文字數值比較；`delta_rmse_*` 是本地 RMSE 減去論文 RMSE。`single-BS baseline` 用固定 BS1 的 PBS 四維量測，對照論文中單站追蹤失效的觀察。
- Fig. 10-11 的 `blockage` 場景目前能復現三段 blockage 行為和 PBS handover，但論文文字沒有列完整 RMSE benchmark，因此報告保留定性對照。
- Fig. 12-13 的 `vsc` 場景已使用 active VSC 幾何更新量測與 EKF；仍用幾何近似 sector beam switching。

## 來源文件

- 數值 CSV：`outputs/section_v_summary.csv`
- 圖表地圖：`notes/figure_reproduction_map.md`
