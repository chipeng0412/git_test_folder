import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from scipy.integrate import solve_ivp

# =========================
# 1. 定义单摆参数
# =========================
g = 9.81          # 重力加速度 (m/s^2)
L = 1.0           # 摆长 (m)
m = 1.0           # 摆球质量 (kg)，本例中动力学方程未直接用到
b = 0.1           # 阻尼系数

# =========================
# 2. 定义单摆动力学方程
# 状态变量 x = [theta, omega]
# theta: 角度
# omega: 角速度
# =========================
def pendulum_dynamics(t, x):
    theta = x[0]
    omega = x[1]

    dtheta = omega
    domega = -(g / L) * np.sin(theta) - b * omega

    return [dtheta, domega]

# =========================
# 3. 设置初始条件与仿真时间
# =========================
theta0 = np.pi / 3       # 初始角度 (rad)
omega0 = 0.0             # 初始角速度 (rad/s)
x0 = [theta0, omega0]

t_start = 0.0
t_end = 10.0
num_points = 500
t_eval = np.linspace(t_start, t_end, num_points)

# =========================
# 4. 数值求解动力学方程
# =========================
sol = solve_ivp(
    pendulum_dynamics,
    [t_start, t_end],
    x0,
    t_eval=t_eval,
    rtol=1e-8,
    atol=1e-8
)

t = sol.t
theta = sol.y[0]
omega = sol.y[1]

# =========================
# 5. 将角度转换为摆球位置
# 这里采用：
# x = L * sin(theta)
# y = -L * cos(theta)
# 使得 theta = 0 时摆球位于正下方
# =========================
px = L * np.sin(theta)
py = -L * np.cos(theta)

# =========================
# 6. 创建图形窗口
# 左图：单摆动画
# 右图：状态变化曲线
# =========================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# -------------------------
# 左图：单摆动画
# -------------------------
ax1.set_aspect('equal')
ax1.set_xlim(-1.2 * L, 1.2 * L)
ax1.set_ylim(-1.2 * L, 0.2 * L)
ax1.set_title("Single Pendulum Animation")
ax1.set_xlabel("x (m)")
ax1.set_ylabel("y (m)")
ax1.grid(True)

# 支点
ax1.plot(0, 0, 'ko', markersize=6)

# 摆杆、摆球、轨迹、文字
rod, = ax1.plot([], [], 'b-', linewidth=2)
bob, = ax1.plot([], [], 'ro', markersize=10)
trace, = ax1.plot([], [], 'g--', linewidth=1)
txt = ax1.text(-1.1 * L, 0.05 * L, '', fontsize=10, verticalalignment='top')

# -------------------------
# 右图：状态变化曲线
# -------------------------
ax2.set_title("State Trajectories")
ax2.set_xlabel("Time (s)")
ax2.set_ylabel("States")
ax2.grid(True)
ax2.set_xlim(t[0], t[-1])

y_min = min(np.min(theta), np.min(omega))
y_max = max(np.max(theta), np.max(omega))
margin = 0.1 * (y_max - y_min + 1e-6)
ax2.set_ylim(y_min - margin, y_max + margin)

theta_line, = ax2.plot([], [], label=r'$\theta(t)$')
omega_line, = ax2.plot([], [], label=r'$\omega(t)$')
time_marker_theta, = ax2.plot([], [], 'o', markersize=6)
time_marker_omega, = ax2.plot([], [], 'o', markersize=6)
ax2.legend()

# =========================
# 7. 初始化函数
# =========================
def init():
    rod.set_data([], [])
    bob.set_data([], [])
    trace.set_data([], [])
    txt.set_text('')

    theta_line.set_data([], [])
    omega_line.set_data([], [])
    time_marker_theta.set_data([], [])
    time_marker_omega.set_data([], [])

    return rod, bob, trace, txt, theta_line, omega_line, time_marker_theta, time_marker_omega

# =========================
# 8. 动画更新函数
# =========================
def update(k):
    # 左图：更新摆杆、摆球、轨迹
    rod.set_data([0, px[k]], [0, py[k]])
    bob.set_data([px[k]], [py[k]])
    trace.set_data(px[:k+1], py[:k+1])

    line1 = f't = {t[k]:.2f} s'
    line2 = f'theta = {theta[k]:.3f} rad'
    line3 = f'omega = {omega[k]:.3f} rad/s'
    txt.set_text(f'{line1}\n{line2}\n{line3}')

    # 右图：更新状态曲线
    theta_line.set_data(t[:k+1], theta[:k+1])
    omega_line.set_data(t[:k+1], omega[:k+1])

    time_marker_theta.set_data([t[k]], [theta[k]])
    time_marker_omega.set_data([t[k]], [omega[k]])

    return rod, bob, trace, txt, theta_line, omega_line, time_marker_theta, time_marker_omega

# =========================
# 9. 创建动画
# interval 单位为毫秒
# =========================
ani = FuncAnimation(
    fig,
    update,
    frames=len(t),
    init_func=init,
    blit=True,
    interval=20
)

plt.tight_layout()
plt.show()