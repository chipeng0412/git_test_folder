# UAV Tracking 論文復現前置學習路線

這份筆記是給 Obsidian 用的學習地圖。目標不是把所有課都學完，而是把「看懂 Networked ISAC UAV tracking 論文並用 Python 復現」需要的知識排出優先順序。

## 先讀本專案

- [[next_steps_checklist]]
  - 接下來可勾選的實作與學習任務，用 `- [ ]` 管理進度。
- [[beginner_python_thinking_guide]]
  - 先用基礎 Python 的角度理解：幾何、軌跡、量測、EKF、handover、實驗流程。
- [beginner_ekf_walkthrough.py](../examples/beginner_ekf_walkthrough.py)
  - 最小 EKF 教學範例。建議先跑一次，再逐行讀註釋。
- [[paper_notes]]
  - 論文中文主筆記。
- [[formula_implementation_map]]
  - 公式與 Python 模組對照。
- [[figure_reproduction_map]]
  - Fig. 6-13 對應的 CLI、輸出與限制。

## 路線總覽

```text
Python 基礎
  -> NumPy / 矩陣運算
  -> 線性代數
  -> 機率與高斯噪聲
  -> Kalman Filter / EKF
  -> DSP / FFT
  -> OFDM
  -> MUSIC / angle-range-Doppler estimation
  -> 回到論文 Section V 復現
```

如果時間有限，優先順序是：

```text
必學：Python, NumPy, 線代, 機率, Kalman/EKF
次要但重要：FFT, OFDM, MUSIC
可暫時跳過：MPC, LQR, optimal control
```

## 1. Python 基礎與程式抽象

### CS61A

- [CS 61A official site](https://cs61a.org/)
  - Berkeley 的 Python/Scheme/SQL 入門課。你不需要完整刷完才做本專案，但它能補 function、abstraction、class、iterator 等基礎。
- [Composing Programs](https://www.composingprograms.com/)
  - CS61A 的主要線上教材。建議先看 Python 相關章節。

建議先看：

- Functions
- Control
- Higher-Order Functions
- Data Abstraction
- Object-Oriented Programming
- Mutable Data
- Iterators / Generators

暫時可跳過：

- Scheme macros
- SQL
- interpreters 深入部分

本專案對應：

- [geometry.py](../isac_uav/geometry.py)：function、dataclass、type hints。
- [measurement.py](../isac_uav/measurement.py)：資料物件與函數拆分。
- [experiments.py](../isac_uav/experiments.py)：完整實驗流程。

## 2. NumPy 與科學計算

### NumPy 官方入門

- [NumPy: the absolute basics for beginners](https://numpy.org/doc/stable/user/absolute_beginners.html)
  - 官方新手教程。先學 `np.array`、shape、indexing、broadcasting、axis。
- [NumPy linear algebra reference](https://numpy.org/doc/stable/reference/routines.linalg.html)
  - 查 `np.linalg.norm`、`inv`、`pinv`、矩陣分解時用。

你需要先會：

```python
np.array(...)
np.zeros(...)
np.eye(...)
np.diag(...)
a @ b
matrix.T
np.linalg.norm(...)
np.linalg.pinv(...)
```

本專案對應：

- [ekf.py](../isac_uav/ekf.py)：EKF 大量使用矩陣乘法。
- [geometry.py](../isac_uav/geometry.py)：距離、角度、座標轉換。

## 3. 線性代數

### MIT 18.06 Linear Algebra

- [MIT OpenCourseWare 18.06 Linear Algebra](https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/)
  - Gilbert Strang 的經典線性代數課。對 Kalman filter 很有幫助。

優先學：

- 向量與矩陣乘法
- 轉置
- 反矩陣
- 投影
- 最小二乘
- 特徵值與特徵向量
- 正定矩陣

和本專案的關係：

- `F @ x`：狀態轉移。
- `H @ P @ H.T`：把狀態不確定性映射到量測空間。
- `np.linalg.pinv(S)`：計算 Kalman gain 時處理可能不穩定的矩陣。

## 4. 機率與高斯噪聲

### Harvard Stat 110

- [Stat 110: Introduction to Probability](https://projects.iq.harvard.edu/stat110/home)
  - 很好的機率入門課。完整學完很花時間，但先理解隨機變量、期望、方差就夠用。

優先學：

- random variable
- expectation
- variance
- covariance
- Gaussian distribution
- conditional probability

本專案對應：

- `P`：EKF state covariance，表示狀態估計的不確定性。
- `Q`：process covariance，表示運動模型的不確定性。
- `R`：measurement covariance，表示量測噪聲。
- [experiments.py](../isac_uav/experiments.py) 裡的 `default_measurement_covariance()`。

## 5. Kalman Filter / EKF

### Kalman and Bayesian Filters in Python

- [Kalman and Bayesian Filters in Python](https://rlabbe.github.io/Kalman-and-Bayesian-Filters-in-Python/)
  - Roger R. Labbe 的免費線上書，用 Python/Jupyter 寫。非常適合從實作理解 Kalman filter。
- [FilterPy documentation](https://filterpy.readthedocs.io/en/latest/)
  - 配套 Python library。可以看 API，但本專案目前自己寫 EKF，方便和論文公式對照。

建議順序：

1. g-h filter / alpha-beta filter
2. 1D Kalman filter
3. Multivariate Kalman filter
4. Nonlinear filters
5. Extended Kalman Filter

本專案對應：

- [ekf.py](../isac_uav/ekf.py)
  - `ExtendedKalmanFilter.predict()`
  - `ExtendedKalmanFilter.update(...)`
  - `constant_velocity_transition(dt)`
  - `numerical_jacobian(...)`
- [beginner_ekf_walkthrough.py](../examples/beginner_ekf_walkthrough.py)
  - 新手先讀這個，再讀正式 EKF。

你需要能說清楚：

```text
x: state
P: state covariance
F: state transition matrix
Q: process noise covariance
z: measurement
R: measurement noise covariance
h(x): nonlinear measurement function
H: Jacobian of h(x)
K: Kalman gain
```

## 6. DSP / FFT

### SciPy FFT 官方教程

- [SciPy FFT tutorial](https://docs.scipy.org/doc/scipy/tutorial/fft.html)
  - 官方 FFT 教程。先用它補 `fft`、`ifft`、frequency bins。

### 你本機的 notebook

- [scipy_essentials.ipynb](file:///Users/chipeng/Downloads/scipy_essentials.ipynb)
  - 你之前打開過，裡面有 `from scipy.fft import fft, fftfreq` 的範例。

優先學：

- time domain vs frequency domain
- FFT / IFFT
- sampling rate
- frequency bin
- complex signal
- magnitude / phase

和論文的關係：

- OFDM 需要 IFFT 產生 time-domain symbol。
- delay / Doppler estimation 會使用頻域與時間域結構。
- MUSIC 前面通常要先理解複數訊號與頻率。

## 7. SDR / OFDM

### PySDR

- [PySDR: A Guide to SDR and DSP using Python](https://pysdr.org/)
  - 免費線上教材，用 Python 講 SDR、DSP、IQ signal、modulation、OFDM、beamforming。
- [PySDR: Cyclostationary Processing](https://pysdr.org/content/cyclostationary.html)
  - 有 OFDM 相關 Python 模擬內容。
- [PySDR: Direction of Arrival](https://pysdr.org/content/doa.html)
  - 對 MUSIC / angle estimation 有幫助。

### scikit-dsp-comm

- [scikit-dsp-comm digital communications docs](https://scikit-dsp-comm.readthedocs.io/en/v2.0.1/digitalcom.html)
  - 有教學型 OFDM 發射/接收函數，例如 `OFDM_tx`、`ofdm_rx`。

### NVIDIA Sionna

- [Sionna PHY tutorials](https://nvlabs.github.io/sionna/phy/tutorials.html)
  - 研究級 Python 通訊系統模擬。
- [Sionna OFDM MIMO Detection tutorial](https://nvlabs.github.io/sionna/phy/tutorials/OFDM_MIMO_Detection.html)
  - 比 PySDR 難，適合後期看。

建議順序：

1. 先用 NumPy 自己寫最小 OFDM。
2. 再看 PySDR 的 OFDM / SDR 概念。
3. 再看 scikit-dsp-comm 的封裝函數。
4. 最後看 Sionna 的 MIMO-OFDM。

本專案對應：

- [signal_music.py](../isac_uav/signal_music.py)
  - `synthesize_single_target_echo(...)`
  - `estimate_single_target_parameters(...)`
- [music_measurement.py](../isac_uav/music_measurement.py)
  - 把 MUSIC 估計接回 Table I 量測向量。

## 8. MUSIC / DOA / Delay-Doppler

先不要一開始讀很硬的陣列信號處理教材。建議先用 PySDR 建直覺：

- [PySDR: Direction of Arrival](https://pysdr.org/content/doa.html)
  - 先理解 antenna array、steering vector、DOA、MUSIC。

你需要理解：

- array response / steering vector
- covariance matrix
- signal subspace
- noise subspace
- peak search
- angle grid

和論文的關係：

- 論文用 MUSIC 從 OFDM echo 中估計 angle、delay、Doppler。
- 第一版復現用 noisy analytic measurement 代替完整 MUSIC。
- 第二版再逐步補 OFDM echo、MTI、MUSIC。

## 9. 回到論文復現

當你能看懂上面基礎後，按這個順序回來讀本專案：

1. [geometry.py](../isac_uav/geometry.py)
   - BS / VSC 幾何、座標轉換、Table I measurement function。
2. [trajectory.py](../isac_uav/trajectory.py)
   - UAV trajectory。
3. [measurement.py](../isac_uav/measurement.py)
   - noisy measurement 與 blockage dropout。
4. [ekf.py](../isac_uav/ekf.py)
   - EKF predict / update。
5. [handover.py](../isac_uav/handover.py)
   - PBS handover / VSC handover。
6. [experiments.py](../isac_uav/experiments.py)
   - 完整 tracking 實驗主流程。
7. [signal_music.py](../isac_uav/signal_music.py)
   - 第二階段 OFDM / MUSIC。
8. [section_v_suite.py](../isac_uav/section_v_suite.py)
   - Fig. 6-13 batch reproduction。

## 每週學習建議

### Week 1: Python + NumPy

- 看 CS61A function / class。
- 看 NumPy absolute beginners。
- 跑 `examples/beginner_ekf_walkthrough.py`。

### Week 2: 線性代數 + Kalman 直覺

- 學矩陣乘法、反矩陣、最小二乘。
- 看 Kalman and Bayesian Filters in Python 的前幾章。
- 手寫一個 1D Kalman filter。

### Week 3: EKF + 本專案 EKF

- 看 multivariate Kalman filter。
- 看 Extended Kalman Filter。
- 回來讀 [ekf.py](../isac_uav/ekf.py)。

### Week 4: FFT + OFDM

- 看 SciPy FFT tutorial。
- 看 PySDR 的 SDR / OFDM 相關章節。
- 自己寫一個最小 OFDM IFFT/FFT demo。

### Week 5: MUSIC + 論文量測

- 看 PySDR DOA。
- 回來讀 [signal_music.py](../isac_uav/signal_music.py)。
- 對照 [[formula_implementation_map]]。

### Week 6: Section V 復現

- 跑：

```bash
. .venv/bin/activate
python main.py --scenario section-v --monte-carlo 2 --steps 60
```

- 看：
  - [[section_v_report]]
  - [[figure_reproduction_map]]
  - `outputs/section_v_summary.csv`

## 不必現在學完的內容

這些不是沒用，而是不是第一優先：

- MPC
  - Model Predictive Control 是控制決策，不是 tracking estimation 的必要前置。
- LQR / optimal control
  - 和 Kalman filter 常一起出現，但本論文重點是 UAV tracking and handover。
- 5G NR 完整 PHY
  - 論文有 OFDM，但第一版復現不需要完整 5G receiver。
- 嚴格測度論機率
  - 先懂高斯噪聲和協方差即可。

## 最小完成標準

學到下面程度，就可以開始正式讀論文和改復現代碼：

- 能看懂 `np.array`、`@`、`np.linalg.norm`。
- 能說清楚 `x, P, F, Q, z, R, h(x), H, K`。
- 能跑並修改 [beginner_ekf_walkthrough.py](../examples/beginner_ekf_walkthrough.py)。
- 能解釋 `measurement_function()` 的輸入狀態和輸出 12 維量測。
- 能解釋 `run_tracking_experiment()` 的主循環。

最後再回到論文：

- [[paper_notes]]
- [[formula_implementation_map]]
- [[figure_reproduction_map]]
