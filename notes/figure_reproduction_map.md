# 論文圖與復現輸出對照表

這份文件把論文 Section V 的每張 simulation figure 對應到目前 Python 復現命令、輸出檔與主要代碼位置。

| 論文圖 | 目前狀態 | 復現命令 | 輸出檔 | 主要代碼 | 當前限制 |
| --- | --- | --- | --- | --- | --- |
| Fig. 6 | implemented | `python main.py --scenario detection-rmse --monte-carlo 8` | `outputs/detection_rmse.csv`<br>`outputs/detection_rmse.png` | `isac_uav.detection_experiment.run_detection_rmse_experiment`<br>`isac_uav.signal_music` | Default Monte Carlo is small for speed; paper uses N_MC=10000 and compares more parameter groups. |
| Fig. 7 | implemented | `python main.py --scenario multi` | `outputs/multi_top_view.png` | `isac_uav.geometry.build_vsc`<br>`isac_uav.trajectory.simulate_trajectory` | Geometry is an equilateral VSC preserving the existing project convention; it is rotationally equivalent but not a pixel match to the paper figure. |
| Fig. 8 | implemented | `python main.py --scenario multi` | `outputs/multi_position_velocity.png`<br>`outputs/multi_tracking_3d.png` | `isac_uav.experiments.run_tracking_experiment`<br>`isac_uav.ekf.ExtendedKalmanFilter` | Analytic measurements are the default; use --measurement-source music for the slower MUSIC-backed path. |
| Fig. 9 | implemented | `python main.py --scenario multi` | `outputs/multi_pbs_history.png` | `isac_uav.handover.select_pbs`<br>`isac_uav.experiments.run_tracking_experiment` | PBS selection uses nearest unblocked BS, matching the paper's no-blockage rule. |
| Fig. 10 | implemented | `python main.py --scenario blockage` | `outputs/blockage_position_velocity.png`<br>`outputs/blockage_tracking_3d.png` | `isac_uav.experiments._blockage_for`<br>`isac_uav.measurement.active_measurement_roles` | Blockage is scenario-scripted rather than detected from a missed MUSIC peak region. |
| Fig. 11 | implemented | `python main.py --scenario blockage` | `outputs/blockage_pbs_history.png` | `isac_uav.handover.select_pbs`<br>`isac_uav.experiments._blockage_for` | Uses known blockage state instead of a full echo-detection failure classifier. |
| Fig. 12 | implemented | `python main.py --scenario vsc` | `outputs/vsc_top_view.png`<br>`outputs/vsc_tracking_3d.png` | `isac_uav.handover.choose_vsc_index`<br>`isac_uav.experiments._vsc_for_time` | Active VSC geometry is used for measurements and EKF updates; the sector beam pattern itself is still simplified. |
| Fig. 13 | implemented | `python main.py --scenario vsc` | `outputs/vsc_pbs_history.png` | `isac_uav.handover.in_vsc_buffer`<br>`isac_uav.handover.choose_vsc_index` | PBS history uses paper-style labels such as 1-1 and 2-3; full transceiver-sector beam switching is approximated by active VSC geometry switching. |

整套 Section V smoke run 可以使用 `python main.py --scenario section-v --monte-carlo 2 --steps 60`，會輸出 `outputs/section_v_summary.csv`。
tracking 類場景可以加上 `--measurement-source music`，把 analytic noisy measurement 換成目前的 MTI/MUSIC-backed measurement generator。
MUSIC-backed multi-UAV path 目前仍使用 prediction-gated angle windows，因此應視為中間階段復現，而不是完全等價於論文的無先驗全局多目標角度關聯。
