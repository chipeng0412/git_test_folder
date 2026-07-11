# Python 新手如何思考這篇 UAV Tracking 論文復現

這份筆記不是先教你背 EKF 公式，而是教你看這個 repo 時應該怎麼拆問題。你只需要有基礎 Python：變量、list、函數、class、for loop、numpy array 的基本概念。

## 先抓住一句話

這篇論文復現的第一階段可以先想成：

> UAV 真的在空中移動，但我們看不到真實位置；BS 每一個 time slot 給一些有噪聲的角度、距離、速度量測；EKF 用「上一刻預測」加「這一刻量測」估計 UAV 的位置和速度；handover 決定現在主要聽哪一個 BS。

所以你讀代碼時，不要一開始就看全部。先問 5 個問題：

1. UAV 真實狀態放在哪裡？
2. BS / VSC 的幾何位置放在哪裡？
3. 真實狀態怎麼變成量測 `z`？
4. EKF 怎麼用 `z` 修正估計狀態？
5. PBS / VSC handover 什麼時候換？

## 這個 repo 的學習順序

建議順序如下：

1. `isac_uav/geometry.py`
   - 先看 `build_vsc()`：三個 BS 的位置。
   - 再看 `measurement_function()`：把 UAV 狀態變成 12 維量測。
2. `isac_uav/trajectory.py`
   - 看 `simulate_trajectory()`：產生 UAV 真實軌跡。
3. `isac_uav/measurement.py`
   - 看 `generate_measurement()`：在乾淨量測上加噪聲，並處理 blockage。
4. `isac_uav/ekf.py`
   - 看 `predict()`：先用物理模型猜下一刻。
   - 看 `update()`：再用量測修正這個猜測。
5. `isac_uav/handover.py`
   - 看 `select_pbs()`：選最近且未遮擋的 BS。
6. `isac_uav/experiments.py`
   - 看 `run_tracking_experiment()`：把前面所有零件串起來跑完整實驗。

## 最重要的變量

### 狀態 `x`

在這個 repo，UAV 狀態固定寫成 6 維：

```text
x = [x, vx, y, vy, z, vz]
```

意思是：

```text
x  : x 方向位置
vx : x 方向速度
y  : y 方向位置
vy : y 方向速度
z  : 高度
vz : 垂直速度
```

為什麼不是 `[x, y, z, vx, vy, vz]`？因為常速度轉移矩陣比較容易寫成：

```text
下一刻位置 = 現在位置 + 速度 * dt
下一刻速度 = 現在速度
```

所以 `x` 和 `vx` 放一起，`y` 和 `vy` 放一起，`z` 和 `vz` 放一起。

### 量測 `z`

論文 Table I 的量測向量是 12 維。這個 repo 用同樣順序：

```text
[
  theta_pbs, phi_pbs, v_pbs, d_pbs,
  theta_sbs1, phi_sbs1, v_pbs + v_sbs1, d_pbs + d_sbs1,
  theta_sbs2, phi_sbs2, v_pbs + v_sbs2, d_pbs + d_sbs2,
]
```

可以先簡化理解：

- `theta` / `phi`：角度，告訴你 UAV 往哪個方向。
- `d`：距離，告訴你 UAV 大約多遠。
- `v`：徑向速度，告訴你 UAV 是靠近還是遠離 BS。
- PBS 是 primary BS，SBS 是 secondary BS。

## EKF 的思考方式

EKF 可以用一句話理解：

> 我先根據速度預測 UAV 下一刻在哪裡；再看 BS 量測覺得我猜得差多少；最後把預測往量測方向修正一點。

對應到代碼：

```python
ekf.predict()  # 只用運動模型，不看新的 BS 量測
ekf.update(z, active_components, pbs_index)  # 用量測 z 修正剛才的預測
```

你讀 `isac_uav/ekf.py` 時可以先忽略矩陣細節，只看資料流：

1. `self.state` 是目前 EKF 相信的 UAV 狀態。
2. `predict()` 把 `self.state` 往下一個 time slot 推進。
3. `measurement_fn(self.state, pbs_index)` 把「目前猜測的狀態」轉成「如果猜測是真的，BS 應該看到什麼」。
4. `innovation = z - h_active` 表示「真實量測」和「預期量測」的差。
5. `self.state = self.state + k_gain @ innovation` 表示用這個差值修正狀態。

## 讀 numpy 時的最低要求

你不需要一開始就懂所有線性代數，但至少要認得：

```python
a @ b
```

這是矩陣乘法。

```python
np.array([...])
```

這是建立向量或矩陣。

```python
matrix.T
```

這是矩陣轉置。

```python
np.diag([...])
```

這是建立只有對角線有值的矩陣，常用來表示各個變量的不確定性。

## 最小可跑範例

先跑這個教學範例：

```bash
. .venv/bin/activate
python examples/beginner_ekf_walkthrough.py
```

這個範例只做一件事：

1. 建立一個 VSC。
2. 放一台 UAV 在固定真實位置。
3. 用真實位置生成一筆帶噪聲量測。
4. 故意給 EKF 一個有誤差的初始猜測。
5. 跑一次 `predict()` 和一次 `update()`。
6. 印出修正前後的估計誤差。

等你看懂這個小範例，再去看 `isac_uav/experiments.py` 的完整 for loop，會容易很多。

## 看完整實驗時的心法

讀 `run_tracking_experiment()` 時，把它想成這個流程：

```text
準備幾何和軌跡
初始化每一台 UAV 的 EKF

for 每一個 time slot:
    每個 EKF 先 predict
    根據 predicted state 選 PBS
    根據真實 state 產生 measurement
    多 UAV 時做 measurement assignment
    每個 EKF 用 assigned measurement update

計算 RMSE
畫圖
```

如果你看到某一行不懂，先問它屬於哪一類：

- 幾何？
- 軌跡？
- 量測？
- EKF？
- handover？
- 畫圖或輸出？

這樣就不會被整個工程嚇到。

## 下一步應該怎麼學

建議你按這個順序手動改小範例：

1. 改 UAV 真實位置，觀察量測 `z` 怎麼變。
2. 改初始估計誤差，觀察 EKF 修正能力。
3. 把量測噪聲調大，觀察 update 後是否變差。
4. 只使用 PBS 的 4 個量測分量，觀察結果與 12 維量測差異。
5. 再回到 `main.py --scenario multi` 看完整多 UAV tracking。

