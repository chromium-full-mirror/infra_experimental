import yaml
import json

with open('kubernetes.yaml') as f:
  data = yaml.load(f)

with open('kubernetes.json', 'w') as f:
  json.dump(data, f)
