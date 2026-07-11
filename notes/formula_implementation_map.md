# 公式與代碼對照表

這份文件用來回答一個問題：論文裡的每個核心公式或算法，在目前 Python 復現中對應到哪個模組、函數與變量。閱讀順序建議是先看 `notes/paper_notes.md`，再用本文件查細節。

## 1. 幾何與 VSC

| 論文內容 | 作用 | Python 對應 | 主要變量 | 目前狀態 |
| --- | --- | --- | --- | --- |
| VSC 定義 | 三個相鄰 BS sector 組成一個 virtual sensing cell | `isac_uav.geometry.build_vsc` | `VSC.base_stations`, `BaseStation.position`, `BaseStation.alpha` | 已實作 |
| 相鄰 VSC | UAV 跨 VSC 時，兩個 VSC 在 buffer 區交替追蹤 | `isac_uav.geometry.build_adjacent_vsc_pair` | `VSCNetwork.vscs`, labels `1-1`, `2-3` | 已實作幾何近似 |
| 球座標轉直角座標 | 將 `(d, theta, phi)` 轉成 `(x, y, z)` | `sph2cart` | `distance`, `theta`, `phi` | 已實作 |
| 直角座標轉球座標 | 從 UAV/BS 相對位置取得距離、水平角、俯仰角 | `cart2sph`, `_single_bs_measurement` | `rel`, `distance`, `theta`, `phi` | 已實作 |
| 徑向速度 | 投影 UAV 速度到 BS-UAV line-of-sight | `_single_bs_measurement` | `vel`, `e_t`, `radial_velocity` | 已實作 |

## 2. Table I 量測向量

論文 Table I 的融合量測可以理解為三組 BS 量測排成 12 維向量：

```text
z = [theta_PBS, phi_PBS, v_PBS, d_PBS,
     theta_SBS1, phi_SBS1, v_PBS + v_SBS1, d_PBS + d_SBS1,
     theta_SBS2, phi_SBS2, v_PBS + v_SBS2, d_PBS + d_SBS2]
```

| 論文內容 | Python 對應 | 主要變量 | 說明 |
| --- | --- | --- | --- |
| PBS 單站距離/速度 | `measurement_function` | `pbs[2]`, `pbs[3]` | PBS 對應 `v_PBS`, `d_PBS` |
| SBS 雙站 sum 量測 | `measurement_function` | `pbs[2] + sbs[2]`, `pbs[3] + sbs[3]` | SBS 量測使用 PBS+SBS 的速度/距離和 |
| PBS/SBS 排序 | `order_base_stations` | `pbs_index`, `ordered` | 先放 PBS，再放另外兩個 SBS |
| 遮擋後降維 | `isac_uav.measurement.active_measurement_roles` | `active_indices` | 只把未遮擋 role 的量測分量送進 EKF |

## 3. OFDM Echo、MTI、MUSIC

| 論文內容 | 作用 | Python 對應 | 主要變量 | 目前狀態 |
| --- | --- | --- | --- | --- |
| OFDM/UPA 參數 | 設定 subcarrier、symbol、UPA size、carrier frequency | `RadarConfig` | `m_subcarriers`, `n_symbols`, `nx_rx`, `nz_rx`, `f0`, `delta_f`, `ts` | 已實作 |
| 角度 steering | UPA 角度導向向量 | `spatial_directions`, `upa_steering` | `psi`, `omega`, `array` | 已實作 |
| delay steering | 距離對應 subcarrier 相位 | `delay_steering` | `tau`, `delta_f` | 已實作 |
| Doppler steering | 徑向速度對應 OFDM symbol 相位 | `doppler_steering` | `fd`, `ts` | 已實作 |
| 單目標 echo | 合成 moving UAV echo + static clutter + noise | `synthesize_single_target_echo` | `signal`, `clutter`, `noise`, `snr_db` | 已實作簡化模型 |
| 多目標 echo | 合成多 UAV echo | `synthesize_multi_target_echo` | `targets`, `amplitudes` | 已實作 |
| MTI | 相鄰 OFDM symbol 相減去除 zero-Doppler clutter | `apply_mti` | `echo[:, :-1, :] - echo[:, 1:, :]` | 已實作 |
| 2D angle MUSIC | 搜尋 `(theta, phi)` 的 MUSIC spectrum peak | `estimate_angle_music`, `estimate_angle_music_peaks` | `covariance`, `noise_space`, `spectrum` | 已實作 |
| delay/Doppler MUSIC | 分別估計 distance 和 velocity peak | `estimate_delay_doppler_music`, `estimate_delay_doppler_peaks` | `tau_grid`, `fd_grid`, `delay_spectrum`, `doppler_spectrum` | 已實作 |
| 單目標端到端 MUSIC | echo -> MTI -> angle MUSIC -> range/velocity MUSIC | `estimate_single_target_parameters` | `MusicEstimate` | 已實作 |

## 4. PBS/SBS 的單站與雙站轉換

| 論文內容 | Python 對應 | 主要變量 | 說明 |
| --- | --- | --- | --- |
| PBS 單站 delay | `MONOSTATIC` | `delay_distance_factor=2.0` | `tau = 2 d / c` |
| PBS 單站 Doppler | `MONOSTATIC` | `doppler_velocity_factor=2.0` | `fd = 2 f0 v / c` |
| SBS 雙站 delay sum | `BISTATIC_SUM` | `delay_distance_factor=1.0` | `tau = (d_PBS + d_SBS) / c` |
| SBS 雙站 Doppler sum | `BISTATIC_SUM` | `doppler_velocity_factor=1.0` | `fd = f0 (v_PBS + v_SBS) / c` |
| MUSIC 量測接回 Table I | `generate_music_measurement` | `full`, `pbs_index`, `grids` | 產生和 `measurement_function` 同順序的 12 維向量 |

## 5. 多 UAV 區分與 Algorithm 1

| 論文內容 | 作用 | Python 對應 | 主要變量 | 目前狀態 |
| --- | --- | --- | --- | --- |
| EKF one-step prediction 區分目標 | 用 prediction 和量測距離做 assignment | `_assign_measurements` | `predicted_states`, `candidate_grid`, `score_matrix` | 已實作 |
| 多目標 angle peak | 找多個 2D MUSIC peaks | `estimate_angle_music_peaks` | `theta_peaks`, `phi_peaks` | 已實作 |
| gated angle MUSIC | 在 prediction 附近建立小角度窗 | `MusicMeasurementGrids`, `_music_grids_for_tracking` | `theta_half_width`, `phi_half_width` | 已實作，仍是近似 |
| distance/Doppler 分別取峰 | 取多個 tau 和 fd candidates | `estimate_delay_doppler_peaks` | `tau_candidates`, `fd_candidates` | 已實作 |
| SVD 配對 | 把 distance peaks 和 Doppler peaks 成對 | `match_delay_doppler_svd` | `u_matrix`, `vh_matrix`, `DelayDopplerMatch` | 已實作 |
| 多 UAV MUSIC 量測 | 產生 `K x 12` Table I 量測矩陣 | `generate_multi_target_music_measurements` | `full_measurements` | 已實作 |

目前限制：多 UAV angle MUSIC 使用 prediction-gated window，還不是完全無先驗的全局 angle peak association。

## 6. EKF Tracking

| 論文內容 | Python 對應 | 主要變量 | 說明 |
| --- | --- | --- | --- |
| 狀態向量 | `ExtendedKalmanFilter.state` | `[x, vx, y, vy, z, vz]` | 和論文 tracking state 一致 |
| 常速度轉移 | `constant_velocity_transition` | `dt` | 位置由速度推進 |
| prediction | `ExtendedKalmanFilter.predict` | `self.state`, `self.covariance` | `x_q+1|q` |
| 非線性量測函數 | `measurement_function` | `h_full` | `h(x)` |
| 數值 Jacobian | `numerical_jacobian` | `epsilon`, `jacobian_full` | 有限差分 |
| 可變維度 update | `ExtendedKalmanFilter.update` | `active_components`, `r_active` | 遮擋時只更新可見分量 |
| 實驗主迴圈 | `run_tracking_experiment` | `filters`, `candidate_grid`, `assignment` | 串起 prediction、measurement、assignment、update |

## 7. PBS Handover

| 論文內容 | Python 對應 | 主要變量 | 說明 |
| --- | --- | --- | --- |
| 無遮擋選最近 BS | `select_pbs` | `ranked` | 距離最近者作為 PBS |
| PBS blockage | `_blockage_for`, `select_pbs` | `blocked={nearest}` | PBS blocked 時切到下一個未遮擋 BS |
| SBS blockage | `active_measurement_roles` | `active_roles` | PBS 不切換，只降維 |
| 全部被遮擋 | `select_pbs`, `ExtendedKalmanFilter.update` | empty `active_indices` | 無可用量測時跳過 update |

## 8. VSC Handover

| 論文內容 | Python 對應 | 主要變量 | 說明 |
| --- | --- | --- | --- |
| buffer region | `in_vsc_buffer` | `theta_min`, `theta_max`, `buffer_theta` | 邊界附近進入 buffer |
| 交替 VSC | `choose_vsc_index` | `time_index`, `current_vsc_index` | buffer 內交替 VSC |
| 相鄰 VSC 幾何 | `build_adjacent_vsc_pair` | `VSCNetwork.vscs` | 建立 VSC1/VSC2 |
| paper-style PBS label | `pbs_label_history` | `1-1`, `2-3` | 對應 Fig. 13 的 label 風格 |
| active VSC tracking | `run_tracking_experiment` | `active_vscs` | PBS 選擇、量測、EKF update 使用 active VSC 幾何 |

目前限制：sector beam pattern 沒有逐 antenna/transceiver sector 建模，而是用 active VSC 幾何近似。

## 9. Trajectory 與 Section V 復現

| 論文內容 | Python 對應 | 主要變量 | 說明 |
| --- | --- | --- | --- |
| truncated Gaussian trajectory | `simulate_trajectory` | `yaw`, `pitch`, `speed`, `truncnorm` | 連續但隨機的 UAV 飛行 |
| sharp turns | `simulate_trajectory` | `sharp_turn_steps` | 測試 EKF 對機動的 lag |
| Fig. 6 | `run_detection_rmse_experiment` | `snr_db`, `monte_carlo`, `rmse_*` | detection RMSE vs SNR |
| Fig. 7-9 | `run_tracking_experiment(scenario="multi")` | `multi_*` figures | 多 UAV tracking 和 PBS index |
| Fig. 10-11 | `run_tracking_experiment(scenario="blockage")` | `blockage_*` figures | blockage tracking 和 PBS handover |
| Fig. 12-13 | `run_tracking_experiment(scenario="vsc")` | `vsc_*` figures | 跨 VSC tracking 和 PBS/VSC index |
| Section V summary | `run_section_v_suite` | `section_v_summary.csv` | 本地 RMSE、論文 RMSE、delta |
| 中文報告 | `write_section_v_report` | `section_v_report.md` | 可閱讀的中文結果解讀 |

## 10. 建議閱讀順序

1. 先讀 `notes/paper_notes.md` 的第 1-6 節，理解 VSC、量測向量、EKF、handover。
2. 對照本文件第 1、2、6、7、8 節，看幾何、量測、EKF、handover 具體如何寫成 Python。
3. 再讀 `notes/paper_notes.md` 第 7-11 節，理解 MTI/MUSIC 和多目標 SVD pairing。
4. 對照本文件第 3、4、5 節，看 signal 層如何接回 tracking 層。
5. 最後執行：

```bash
python main.py --scenario section-v --monte-carlo 2 --steps 60
```

然後閱讀 `notes/section_v_report.md`，用 `outputs/section_v_summary.csv` 檢查本地 RMSE 和論文文字數值的差距。
