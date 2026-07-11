import numpy as np
import math
import matplotlib.pyplot as plt
from scipy import constants
from scipy.constants import pi, c, minute, degree
# at scipy any length is according in meters (inch: one inch in meters)
plt.style.use("ggplot")
plt.rcParams.update(
     {
         "text.usetex": True,
         "font.family": "typeface",
     }
 ) 

def sph2cart(d, theta, phi):
    x = d * np.cos(phi) * np.cos(theta)
    y = d * np.cos(phi) * np.sin(theta)
    z = d * np.sin(phi)

def dist(a, b):
    return np.linalg.norm(a - b)

D_BS = 200 * math.sqrt(3)
H_BS = 15
BS1 = np.array([0, 0, H_BS])
BS2 = np.array([D_BS * np.cos(-30 * degree), D_BS * np.sin(-30 * degree), H_BS])
BS3 = np.array([D_BS * np.cos(30 * degree), D_BS * np.sin(30 * degree), H_BS])

print(np.cos(pi))
print(BS1, BS2, BS3)
print(dist(BS1, BS2), dist(BS2, BS3), dist(BS1, BS3))

array = np.array([[1, 2, 3],
                  [4, 5, 6]], dtype=int)
a = np.linspace(1, 10, 100).reshape((10, 10))
print(array)
print(array.ndim)
print("shape:", array.shape)
print("size:", array.size)
print("dtype:", array.dtype)
print(a)

random_n = np.random.normal(0, 1, 10000)
random_u = np.random.uniform(-1, 1, 10000)
plt.figure(figsize=(10, 4))

plt.subplot(1, 2, 1)
plt.hist(random_n, bins=50, density=True)
plt.title("Normal distribution")

plt.subplot(1, 2, 2)
plt.hist(random_u, bins=50, density=True)
plt.title("uniform distribution")

plt.show()

a = np.deg2rad(np.arange(0, 360+60 , 60))
print(a)   
def rays_from_bs(cx, cy, L=200):
    angles = np.deg2rad([0, 120, 240])
    for a in angles:
        x = [cx, cx + L * np.cos(a)]
        y = [cy, cy + L * np.sin(a)]
        plt.plot(x, y, "b--")

#for bs in [BS1, BS2, BS3]:
    rays_from_bs(bs[0], bs[1], L=200)

plt.show()