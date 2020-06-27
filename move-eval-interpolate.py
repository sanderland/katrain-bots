import numpy as np
from scipy.interpolate import PchipInterpolator
import matplotlib.pyplot as plt

testcase = np.loadtxt("test-est.csv", delimiter=",")
x = testcase[:, 0]
yB = testcase[:, 1]
yW = testcase[:, 2]
xn = np.arange(25, max(testcase[:, 0]))
fBn = PchipInterpolator(x, yB)
fWn = PchipInterpolator(x, yW)
yBn = fBn(xn)
yWn = fWn(xn)

plt.xlabel("Move #")
plt.ylabel("kyu rank")
plt.plot(x, yB, "ok", label="Black estimated kyu")
plt.plot(x, yW, "og", label="White estimated kyu")
plt.plot(xn, yBn, label="Black estimated kyu interpolated")
plt.plot(xn, yWn, label="White estimated kyu interpolated")

plt.legend()
plt.show()
