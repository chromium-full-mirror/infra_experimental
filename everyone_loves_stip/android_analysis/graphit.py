import json
import seaborn as sns
import numpy as np
import matplotlib.pyplot as plt

with open('real_cool.json') as f:
  data = [x[-1] for x in json.load(f)]

filt_data = [x for x in data if x > 0]
total = len(data)
filt = len(filt_data)

print 'percentage long pole', (100.0 * filt) / total
print 'median / 75 / 90 / 95: %f, %f, %f, %f' % (
    np.percentile(filt_data, 50),
    np.percentile(filt_data, 75),
    np.percentile(filt_data, 90),
    np.percentile(filt_data, 95))

sns.distplot(filt_data)
plt.show()
