
filepath = '/home/ronin/Documents/n2/vireon/core/twin.py'
with open(filepath, 'r') as f:
    content = f.read()

# Replace locks definition
content = content.replace(
"""        self.hardware_lock = threading.Lock()
        self.clinical_lock = threading.Lock()
        self.therapy_lock = threading.Lock()""",
"""        self._lock = threading.RLock()"""
)

# Replace ITwin injection
content = content.replace('class DigitalTwin:\n', 'from vireon.core.interfaces import ITwin\n\nclass DigitalTwin(ITwin):\n')

# Replace lock usages
content = content.replace('with self.hardware_lock, self.clinical_lock, self.therapy_lock:', 'with self._lock:')
content = content.replace('with self.hardware_lock, self.clinical_lock:', 'with self._lock:')
content = content.replace('with self.hardware_lock:', 'with self._lock:')
content = content.replace('with self.clinical_lock:', 'with self._lock:')
content = content.replace('with self.therapy_lock:', 'with self._lock:')

# Fix history pop
content = content.replace(
"""        self.history.append(state_copy)
        if len(self.history) > 5000:
            self.history.pop(0)""",
"""        self.history.append(state_copy)"""
)

with open(filepath, 'w') as f:
    f.write(content)

print("twin.py fixed")
