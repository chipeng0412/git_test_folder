# Networked ISAC-Based UAV Tracking and Handover Toward Low-Altitude Economy 讀書筆記

## 1. 這篇論文要解決什麼

低空經濟場景中會有大量 UAV。合法 UAV 可以主動回報位置，但非合作 UAV 可能不回報，甚至造成安全風險。論文的核心想法是：利用 cellular network 中相鄰三個 BS 的 ISAC 感知能力，把三個相鄰 sector 組成一個 virtual sensing cell (VSC)，由一個 primary BS (PBS) 發射感知信號，PBS 與兩個 secondary BS (SBS) 都接收回波，最後在資料中心用 EKF 融合三個 BS 的估計結果。

代碼對照：
- VSC 與 BS 幾何：`isac_uav.geometry.build_vsc`
- PBS 選擇：`isac_uav.handover.select_pbs`
- 端到端第一階段實驗：`isac_uav.experiments.run_tracking_experiment`

配套文件：
- `notes/formula_implementation_map.md`：公式、算法與 Python 函數/變量的逐項對照。
- `notes/figure_reproduction_map.md`：論文 Fig. 6-13 與 CLI、輸出圖、代碼位置的對照。
- `notes/section_v_report.md`：Section V smoke reproduction 的中文結果報告。

## 2. VSC 與座標

論文使用球座標 `(d, theta, phi)` 描述 UAV 相對於 BS 的位置，其中 `d` 是距離，`theta` 是水平角，`phi` 是俯仰角。轉成直角座標是：

```text
x = d cos(phi) cos(theta)
y = d cos(phi) sin(theta)
z = d sin(phi)
```

代碼對照：
- `sph2cart` / `cart2sph`：球座標與直角座標互轉
- `measurement_function`：把狀態 `x=[x,vx,y,vy,z,vz]` 轉成論文的量測向量

## 3. 第一階段如何替代 MUSIC

論文完整感知鏈是：OFDM echo -> MTI 去除靜態雜波 -> MUSIC 估計角度、距離、徑向速度。第一版復現先不實作這條信號鏈，而是直接從真實狀態生成帶噪聲量測：

```text
z = [theta_PBS, phi_PBS, v_PBS, d_PBS,
     theta_SBS1, phi_SBS1, v_PBS+v_SBS1, d_PBS+d_SBS1,
     theta_SBS2, phi_SBS2, v_PBS+v_SBS2, d_PBS+d_SBS2]
```

這樣可以先驗證「多 BS 量測融合 + handover + EKF tracking」是否能跑通。之後第二階段再把 `generate_measurement` 替換成真正的 MTI/MUSIC 輸出。

代碼對照：
- 帶噪聲量測：`isac_uav.measurement.generate_measurement`
- 12 維量測定義：`isac_uav.geometry.measurement_function`

## 4. EKF 融合

論文狀態向量是：

```text
x_q = [x_q, v_xq, y_q, v_yq, z_q, v_zq]^T
```

狀態轉移採用短時間常速度模型。量測函數 `h(x)` 是非線性的，因為角度、距離、徑向速度都由幾何關係算出，所以 EKF 需要 Jacobian。論文使用有限差分數值 Jacobian，本代碼也照這個方法實作。

代碼對照：
- EKF 主體：`isac_uav.ekf.ExtendedKalmanFilter`
- 常速度矩陣：`constant_velocity_transition`
- 有限差分 Jacobian：`numerical_jacobian`

## 5. PBS handover

無遮擋時，離 UAV 最近的 BS 通常有最高 SNR，因此選最近 BS 作為 PBS。若 PBS 被遮擋，三個 BS 都收不到由 PBS 發出的有效回波，所以要把 PBS 切到第二近且未遮擋的 BS。若只是 SBS 被遮擋，PBS 不切換，但 EKF 更新時丟掉該 SBS 的 4 個量測分量。

代碼對照：
- 選 PBS：`select_pbs`
- 遮擋狀態：`BlockageState`
- 依遮擋降維量測：`active_measurement_roles`

## 6. VSC handover

當 UAV 接近 VSC 邊界時，如果等到真正越界才切換，容易丟失目標。論文設定一個 buffer region，在 buffer 裡由相鄰兩個 VSC 交替形成波束追蹤。代碼現在建立了兩個相鄰 VSC 的幾何與 paper-style sector label，其中 `1-1` 與 `2-3` 代表同一個 physical BS 的不同 sector；當 `vsc_history` 切到相鄰 VSC 時，PBS 選擇、量測生成、association scoring 和 EKF update 都會使用 active VSC 的幾何。這比只切 index 更接近 Fig. 12-13，但 transceiver sector beam pattern 仍是幾何近似。

代碼對照：
- buffer 判斷：`in_vsc_buffer`
- 交替 VSC：`choose_vsc_index`
- 相鄰 VSC 幾何：`build_adjacent_vsc_pair`
- vsc 場景：`python main.py --scenario vsc`

## 7. MTI 與 MUSIC 的第二階段起點

論文第 III 節的完整感知流程是：BS 收到含有 UAV 與靜態建築雜波的 OFDM 回波，先用 moving target indicator (MTI) 做相鄰 OFDM symbol 相減，去掉零 Doppler 的靜態 clutter。之後對動態回波做 MUSIC：

- 角度估計：用接收 UPA 的 steering vector 搜尋 `(theta, phi)`，峰值就是 UAV 的 AOA。
- 距離估計：對 subcarrier 方向的 delay steering vector 做 1D MUSIC。
- 速度估計：對 OFDM symbol 方向的 Doppler steering vector 做 1D MUSIC。

目前代碼已從單 BS、單 UAV demo 擴展到 tracking 主流程：`measurement_source="music"` 會把 OFDM echo 經 MTI+MUSIC 轉成 Table I 的 12 維量測，再送進同一套 EKF。多 UAV 版本也已加入 distance-Doppler MUSIC 峰值與 Algorithm 1 風格的 SVD 配對；角度部分目前採用 EKF prediction 周圍的小範圍 gated 2D MUSIC，而不是完全無先驗的全局 peak association。

代碼對照：
- 回波合成：`isac_uav.signal_music.synthesize_single_target_echo`
- MTI：`apply_mti`
- 角度 MUSIC：`estimate_angle_music`
- 距離/速度 MUSIC：`estimate_delay_doppler_music`
- 單目標端到端估計：`estimate_single_target_parameters`
- CLI demo：`python main.py --scenario music`

## 8. 從 MUSIC 接回 Table I 的 12 維量測

論文 Table I 的 PBS 和 SBS 量測不是完全相同：

- PBS 是單站雷達：`tau = 2 d_PBS / c`，`f_D = 2 f_0 v_PBS / c`。
- SBS 是雙站接收：`tau = (d_PBS + d_SBS) / c`，`f_D = f_0 (v_PBS + v_SBS) / c`。

因此代碼把 echo conversion 拆成兩種 mode：

- `MONOSTATIC`：用於 PBS，MUSIC 峰值轉回 `d_PBS` 和 `v_PBS`。
- `BISTATIC_SUM`：用於 SBS，MUSIC 峰值轉回距離和速度的 sum。

`generate_music_measurement` 會對 PBS、SBS1、SBS2 各跑一次單目標 MUSIC，最後組成和 `measurement_function` 相同順序的 12 維向量。這是把信號層替換進 EKF tracking 前的接口橋接。

代碼對照：
- 單站/雙站轉換：`EchoMode`, `MONOSTATIC`, `BISTATIC_SUM`
- MUSIC 量測向量：`isac_uav.music_measurement.generate_music_measurement`
- CLI demo：`python main.py --scenario music-measurement`

## 9. 用 MUSIC 量測驅動 EKF tracking

`run_tracking_experiment` 現在有兩種量測來源：

- `measurement_source="analytic"`：直接用真實狀態經 `measurement_function` 產生 12 維量測，再加高斯噪聲。這是快速驗證 EKF、handover、多 UAV association 的主路徑。
- `measurement_source="music"`：先合成 OFDM echo，再經 MTI+MUSIC 估計 PBS/SBS 的角度、距離、速度，最後把 MUSIC 結果送進同一個 EKF。單 UAV 會用單目標 MUSIC；多 UAV 會用多目標 distance-Doppler MUSIC 和 Algorithm 1 SVD matching 生成候選量測。

運行例子：

```bash
python main.py --scenario vsc --measurement-source music --steps 20 --no-plots
python main.py --scenario blockage --measurement-source music --steps 20 --no-plots
python main.py --scenario multi --measurement-source music --steps 20 --no-plots
```

## 10. Algorithm 1：SVD 配對 distance 與 Doppler

多目標時，1D MUSIC 會分別得到多個 distance 峰和多個 Doppler 峰，但它們不是天然成對的。論文 Algorithm 1 的核心做法是對 beamformed delay-Doppler 矩陣做 SVD，取每個 singular vector pair 形成 rank-1 basis，再計算每個 Doppler steering vector 與每個 delay steering vector 在該 basis 上的匹配分數。分數最大的 `(f_D, tau)` 就是一個目標的 pair。

代碼對照：
- 合成多目標 delay-Doppler 矩陣：`synthesize_beamformed_delay_doppler`
- 取多個 1D MUSIC 峰：`estimate_delay_doppler_peaks`
- SVD 配對：`match_delay_doppler_svd`
- 測試：`test_svd_matches_multi_target_delay_doppler_pairs`

## 11. 多目標 MUSIC 量測生成

`generate_multi_target_music_measurements` 會對多個 UAV 生成 Table I 的量測矩陣，形狀是 `K x 12`。目前這一步已把 Algorithm 1 用到每個 role 的 distance-Doppler 配對上：

- PBS role 使用 `MONOSTATIC` mode。
- SBS1/SBS2 role 使用 `BISTATIC_SUM` mode。
- 每個 role 的多個 `(range, velocity)` pair 由 `match_delay_doppler_svd` 配對。

角度估計也已經使用多目標 2D MUSIC，但採用 tracking 中自然會有的 gated window：每個目標根據預測/幾何中心建立小範圍 `(theta, phi)` 搜尋窗，再在該窗內取 MUSIC 峰。多 UAV tracking 目前使用較窄的角度 gate，因為寬 gate 容易被鄰近強目標峰拉偏。這比直接使用真值角度更接近論文中「用 EKF one-step prediction 區分目標」的流程，但還不是完全無先驗的全局 angle peak association。`multi --measurement-source music` 已可運行，但這個限制需要在解讀結果時保留。

## 12. 如何運行

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests
python main.py --scenario music
python main.py --scenario music-measurement
python main.py --scenario detection-rmse --monte-carlo 8
python main.py --scenario figure-map
python main.py --scenario section-v --monte-carlo 2 --steps 60
python main.py --scenario multi
python main.py --scenario blockage
python main.py --scenario vsc
```

`detection-rmse` 對應論文 Fig. 6 的精神：在不同 SNR 下重複合成 echo、執行 MTI+MUSIC，統計 `theta/phi/d/v` 的 RMSE。它會輸出 `outputs/detection_rmse.csv` 和 `outputs/detection_rmse.png`；若加上 `--no-plots`，只會跳過 PNG，CSV 仍會保留。為了讓本地測試快速，它的 Monte Carlo 次數預設遠小於論文的 `N_MC=10000`，但接口和輸出欄位已經對齊後續擴大實驗的需求。

輸出圖片或 CSV 會放在 `outputs/`。目前 tracking/handover 和 detection RMSE 都已有入口。

## 13. 論文圖與復現輸出的對照

`notes/figure_reproduction_map.md` 是目前的逐圖對照表，內容由 `isac_uav.reproduction_suite.figure_reproduction_map` 生成。它把論文 Section V 的 Fig. 6-13 對應到本 repo 的 CLI 命令、輸出圖片或 CSV、主要代碼位置，以及目前還不是精確復現的限制。

生成或刷新對照表：

```bash
python main.py --scenario figure-map
```

一次跑 Section V 的 smoke reproduction 並輸出 RMSE summary：

```bash
python main.py --scenario section-v --monte-carlo 2 --steps 60
```

這會生成 `outputs/section_v_summary.csv` 和 `notes/section_v_report.md`。CSV 中 tracking 場景會列出 `x/y/z/vx/vy/vz` RMSE；Markdown report 則把同一批結果整理成中文表格和解讀。對於論文文字有明確給出數值的場景，CSV 也會列出 `paper_rmse_*` 與 `delta_rmse_*`：

- `multi` 對照 Fig. 8 文字中的 10 組 two-UAV trajectory 平均 RMSE。
- `vsc` 對照 Fig. 13 文字中的 cross-VSC tracking RMSE。
- `blockage` 在論文文字中主要是定性說明，沒有完整列出 `x/y/z/vx/vy/vz` RMSE，因此 CSV 的 paper benchmark 欄位保留說明文字。

## 14. 建議學習路線

1. 先讀本文第 1-6 節，建立 VSC、量測向量、EKF、PBS/VSC handover 的大圖。
2. 打開 `notes/formula_implementation_map.md`，逐項查論文公式和代碼的對應關係。
3. 再讀本文第 7-11 節，理解 OFDM echo、MTI、MUSIC、Algorithm 1 SVD pairing 和多 UAV 量測生成。
4. 跑 `python main.py --scenario section-v --monte-carlo 2 --steps 60`，閱讀 `notes/section_v_report.md`。
5. 如果要深入信號層，從 `python main.py --scenario music` 和 `python main.py --scenario music-measurement` 開始；如果要深入 tracking 層，從 `python main.py --scenario multi`、`blockage`、`vsc` 開始。
