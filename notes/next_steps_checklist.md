# 下一步任務清單：Networked ISAC UAV 論文復現

這份清單用來在 Obsidian 裡管理接下來的學習與復現進度。不要一次想完成全部；每次只勾掉一小項。

## 0. 目前狀態確認

- [ ] 用 3-5 句話寫下目前已理解的論文結果：多 UAV tracking、blockage handover、VSC handover 分別想證明什麼。
- [ ] 寫下目前還沒看懂的部分：EKF 如何估計位置速度、MUSIC/SVD 如何形成量測、AI 代碼如何分模組。
- [ ] 打開 [[beginner_python_thinking_guide]]，確認自己知道 `geometry -> measurement -> ekf -> handover -> experiments` 的主線。
- [ ] 跑一次新手範例：

```bash
. .venv/bin/activate
python examples/beginner_ekf_walkthrough.py
```

## 1. 先補 EKF Tracking 主骨架

教材：

- [Kalman and Bayesian Filters in Python](https://rlabbe.github.io/Kalman-and-Bayesian-Filters-in-Python/)
- [beginner_ekf_walkthrough.py](../examples/beginner_ekf_walkthrough.py)
- [ekf.py](../isac_uav/ekf.py)

任務：

- [ ] 閱讀 g-h filter / alpha-beta filter，理解「預測 + 修正」的基本思想。
- [ ] 閱讀 1D Kalman filter，能說明 `x`、`P`、`z`、`R` 是什麼。
- [ ] 閱讀 multivariate Kalman filter，理解為什麼狀態可以是向量。
- [ ] 閱讀 Extended Kalman Filter，理解為什麼非線性量測需要 Jacobian。
- [ ] 對照 [ekf.py](../isac_uav/ekf.py)，標註 `predict()` 裡每一行在做什麼。
- [ ] 對照 [ekf.py](../isac_uav/ekf.py)，標註 `update()` 裡 `innovation`、`s`、`k_gain` 的意義。
- [ ] 用自己的話寫下：

```text
EKF 如何由 BS 的角度、距離、徑向速度量測，修正 UAV 的 x/y/z/vx/vy/vz？
```

完成標準：

- [ ] 能說清楚 `x, P, F, Q, z, R, h(x), H, K`。
- [ ] 能解釋 `numerical_jacobian()` 為什麼需要。
- [ ] 能說明 `measurement_function()` 和 EKF `update()` 的關係。

## 2. 補 NumPy / 矩陣運算

教材：

- [NumPy absolute beginners](https://numpy.org/doc/stable/user/absolute_beginners.html)
- [MIT 18.06 Linear Algebra](https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/)

任務：

- [ ] 練習 `np.array`、`np.zeros`、`np.eye`、`np.diag`。
- [ ] 練習矩陣乘法 `A @ x`。
- [ ] 練習轉置 `A.T` 和共軛轉置 `A.conj().T`。
- [ ] 練習 `np.linalg.norm`。
- [ ] 練習 `np.linalg.pinv`，理解它在 EKF 裡為什麼比直接 `inv` 更穩。
- [ ] 在 Obsidian 寫一小段筆記：矩陣在 EKF 中分別代表什麼。

完成標準：

- [ ] 能看懂 [ekf.py](../isac_uav/ekf.py) 中大部分 `@` 運算。
- [ ] 能看懂 [signal_music.py](../isac_uav/signal_music.py) 中 covariance 的基本形狀。

## 3. 補 FFT / QAM / OFDM 基礎

教材：

- [PySDR](https://pysdr.org/)
- [SciPy FFT tutorial](https://docs.scipy.org/doc/scipy/tutorial/fft.html)
- [scipy_essentials.ipynb](file:///Users/chipeng/Downloads/scipy_essentials.ipynb)

任務：

- [ ] 學 complex number / IQ signal。
- [ ] 學 QAM symbol 是什麼。
- [ ] 學 FFT / IFFT 的基本意義。
- [ ] 跑你本機的 `scipy_essentials.ipynb` 中 FFT 範例。
- [ ] 用 NumPy 寫一個最小 IFFT 產生 OFDM symbol 的 demo。
- [ ] 加 cyclic prefix，理解 CP 的作用。
- [ ] 寫一段筆記：OFDM 發射波在論文公式中對應哪幾個符號。

完成標準：

- [ ] 能說明為什麼 OFDM 會用 IFFT。
- [ ] 能說明 subcarrier、OFDM symbol、cyclic prefix 的角色。
- [ ] 能開始對照論文公式 (1)-(9)。

## 4. 補 MUSIC / DOA

教材：

- [PySDR DOA / MUSIC](https://pysdr.org/content/doa.html#music)
- [signal_music.py](../isac_uav/signal_music.py)

任務：

- [ ] 學 antenna array / UPA 的基本概念。
- [ ] 學 steering vector 是什麼。
- [ ] 學 covariance matrix 在 MUSIC 裡的作用。
- [ ] 學 signal subspace / noise subspace。
- [ ] 學 MUSIC spectrum peak 如何對應 angle。
- [ ] 對照 [signal_music.py](../isac_uav/signal_music.py) 的 `estimate_angle_music()`。
- [ ] 對照 [signal_music.py](../isac_uav/signal_music.py) 的 `estimate_delay_doppler_music()`。
- [ ] 寫一段筆記：MUSIC 的輸入為什麼是 MTI 差分後的 echo。

完成標準：

- [ ] 能說明 MUSIC 的輸入、輸出。
- [ ] 能說明 covariance 在 MUSIC 中不是 EKF covariance。
- [ ] 能說明 angle MUSIC、delay MUSIC、Doppler MUSIC 的差異。

## 5. 補 SVD 與 Algorithm 1

教材：

- [MIT 18.065 Matrix Methods, Spring 2018](https://ocw.mit.edu/courses/18-065-matrix-methods-in-data-analysis-signal-processing-and-machine-learning-spring-2018/)
- [signal_music.py](../isac_uav/signal_music.py)

任務：

- [ ] 看 Lecture 6: Singular Value Decomposition。
- [ ] 理解 `A = U Σ V^T` 的直覺。
- [ ] 理解 singular value 代表主要模式強度。
- [ ] 理解 rank-1 approximation。
- [ ] 做 Lecture 6 對應的簡單題，不需要刷完整 18.065。
- [ ] 對照 [signal_music.py](../isac_uav/signal_music.py) 的 `match_delay_doppler_svd()`。
- [ ] 寫一段筆記：Algorithm 1 為什麼要用 SVD 配對 distance 和 Doppler。

完成標準：

- [ ] 能說明 MUSIC 找候選峰，SVD 做 distance / velocity 配對。
- [ ] 能用自己的話解釋 `match_delay_doppler_svd()` 的輸入和輸出。

## 6. 分類整理論文公式 (1)-(9)

目標：把公式拆成可重用 module，而不是全部塞進 `main.py`。

建議分類：

- [ ] OFDM transmitter packet：QAM symbols、IFFT、cyclic prefix。
- [ ] Channel / echo packet：delay、Doppler、angle steering。
- [ ] Clutter / noise packet：static clutter、AWGN。
- [ ] MTI packet：相鄰 OFDM symbol 差分。
- [ ] MUSIC packet：angle、delay、Doppler estimation。

任務：

- [ ] 在 Obsidian 建一張表：公式編號、物理意義、輸入、輸出、對應 Python 函數。
- [ ] 檢查 [signal_music.py](../isac_uav/signal_music.py) 已經覆蓋哪些公式。
- [ ] 找出公式 (1)-(9) 中尚未明確對應到函數的部分。
- [ ] 每個函數加 docstring 草稿，例如：

```python
def example_function(...):
    """對應論文公式 (x)：說明這個函數的輸入、輸出和物理意義。"""
```

完成標準：

- [ ] 能把公式 (1)-(9) 分成上面幾類。
- [ ] 每一類都有明確 Python module 或預計 module。
- [ ] main.py 只負責調用，不負責堆公式細節。

## 7. 學 AI 代碼的工程結構

教材：

- [geometry.py](../isac_uav/geometry.py)
- [measurement.py](../isac_uav/measurement.py)
- [experiments.py](../isac_uav/experiments.py)
- [[learning_roadmap_obsidian]]

任務：

- [ ] 學 `dataclass`：為什麼 `BaseStation`、`VSC`、`Measurement` 適合用 dataclass。
- [ ] 學 `frozen=True`：為什麼有些資料建立後不該被改。
- [ ] 學 `typing`：`Iterable`、`Callable`、`tuple[str, ...]`、`A | B`。
- [ ] 學 module/package：為什麼 `geometry.py`、`ekf.py`、`handover.py` 要分開。
- [ ] 用自己的話寫下每個 module 的責任。

完成標準：

- [ ] 能解釋 `Measurement` dataclass 裡 `full`、`observed`、`active_indices` 的差異。
- [ ] 能解釋 `ExperimentConfig` 為什麼要做成 dataclass。
- [ ] 能說明 main.py 為什麼只是入口，不應該放所有公式。

## 8. 最後整合到可運行復現

任務：

- [ ] 跑 analytic tracking：

```bash
python main.py --scenario multi --steps 60
```

- [ ] 跑 MUSIC demo：

```bash
python main.py --scenario music
```

- [ ] 跑 MUSIC measurement demo：

```bash
python main.py --scenario music-measurement
```

- [ ] 跑 Section V smoke reproduction：

```bash
python main.py --scenario section-v --monte-carlo 2 --steps 60
```

- [ ] 閱讀 [[section_v_report]]。
- [ ] 對照 [[figure_reproduction_map]]。
- [ ] 寫一段報告進度：目前哪些看懂，哪些還在補。

完成標準：

- [ ] 能用文字說明：信號處理如何接到 EKF tracking。
- [ ] 能用文字說明：Algorithm 1-5 如何貫穿全文。
- [ ] 能指出目前代碼與論文完整模型相比的近似與限制。

