import numpy as np
import matplotlib.pyplot as plt

# 生成一些随机数据
np.random.seed(42)
n_points = 100

# 使用 Beta 分布生成更密集的真实值
a, b = 2, 2  # Beta 分布的参数，这样生成的数在0到0.2之间会更密集
true_values = np.random.beta(a, b, n_points)

# 预测相对准确的数据
predicted_values_accurate = true_values + np.random.normal(0, 0.05, n_points)
predicted_values_accurate = np.clip(predicted_values_accurate, 0, 1)

# 预测不准确的数据
predicted_values_inaccurate = true_values + np.random.normal(0, 0.35, n_points)
predicted_values_inaccurate = np.clip(predicted_values_inaccurate, 0, 1)

# 创建子图
fig, ax = plt.subplots(1, 2, figsize=(6, 3))

# 第一个点图：预测相对准确
ax[0].scatter(predicted_values_accurate, true_values, c='blue', alpha=0.5)
ax[0].plot([0, 1], [0, 1], 'r--')  # y=x 参考线
ax[0].set_title('Using feature for prediction')
ax[0].set_xlabel('predicted value')
ax[0].set_ylabel('true value')
ax[0].set_xlim(0, 1)
ax[0].set_ylim(0, 1)

# 第二个点图：预测不准确
ax[1].scatter(predicted_values_inaccurate, true_values, c='red', alpha=0.5)
ax[1].plot([0, 1], [0, 1], 'r--')  # y=x 参考线
ax[1].set_title('Using original parameters for prediction')
ax[1].set_xlabel('predicted value')
ax[1].set_ylabel('true value')
ax[1].set_xlim(0, 1)
ax[1].set_ylim(0, 1)

plt.tight_layout()
plt.show()
