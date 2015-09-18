import json
import seaborn as sns
import matplotlib.pyplot as plt

with open('cool.json') as f:
  data = [x[-1] for x in json.load(f) if x[-1] > 0]

sns.distplot(data)
plt.show()
