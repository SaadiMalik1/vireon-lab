# Tutorial 3: Validating an IDS

You can use VIREON to benchmark your own Intrusion Detection System (IDS).

## 1. Generating Baseline Data
Run `vireon validate` to test the default Spectral Anomaly Detector against normal dataset data. Note the false-positive rate.

## 2. Plugging in Your IDS
Replace the default `SecurityEngine` call in `coordinator.py` with your own machine learning model.
```python
# Assuming you have a custom MyModel class
my_ids = MyModel()
coordinator.set_security_engine(my_ids)
```

## 3. Measuring Performance
Run `vireon validate` again. Compare the detection latency and true-positive rate against the benchmark files in `docs/benchmarks/`.
