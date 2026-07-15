import os
import glob

# Files to update
files_to_update = [
    '/home/ronin/Documents/n2/vireon/dashboard/app.py',
    '/home/ronin/Documents/n2/vireon/plugins/reports/web_server.py',
    '/home/ronin/Documents/n2/vireon/core/validation.py',
    '/home/ronin/Documents/n2/vireon/core/authentication.py',
    '/home/ronin/Documents/n2/vireon/core/compliance.py',
    '/home/ronin/Documents/n2/vireon/core/coordinator.py',
    '/home/ronin/Documents/n2/vireon/core/plugin_registry.py',
    '/home/ronin/Documents/n2/tests/test_dynamic_ids.py',
    '/home/ronin/Documents/n2/tests/test_adversarial_mitigations.py',
    '/home/ronin/Documents/n2/tests/test_bci_paradox_solvers.py',
    '/home/ronin/Documents/n2/tests/test_security_layer.py',
    '/home/ronin/Documents/n2/vireon/core/data/stride_threats.json',
]

def replace_in_file(filepath):
    if not os.path.exists(filepath):
        return
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Python imports
    content = content.replace('from vireon.core.security import DeepAutoencoderIDS', 'from vireon.core.detection import DeepAutoencoderIDS')
    content = content.replace('from vireon.core.security import SecurityEngine, NeuroIPS', 'from vireon.core.detection import SecurityEngine\nfrom vireon.core.clinical import NeuroIPS')
    # Use spaces instead of \n for some nested imports that might be indented
    content = content.replace('from vireon.core.security import SecurityEngine, calculate_spectral_features', 'from vireon.core.detection import SecurityEngine, calculate_spectral_features')
    content = content.replace('from vireon.core.security import SecurityEngine', 'from vireon.core.detection import SecurityEngine')
    content = content.replace('from vireon.core.security import calculate_spectral_features', 'from vireon.core.detection import calculate_spectral_features')
    
    content = content.replace('from vireon.core.security import SecurityEngine, NeuroIPS, BLELinkGuard', 'from vireon.core.detection import SecurityEngine\nfrom vireon.core.clinical import NeuroIPS, BLELinkGuard')
    content = content.replace('    from vireon.core.security import SecurityEngine, NeuroIPS, BLELinkGuard', '    from vireon.core.detection import SecurityEngine\n    from vireon.core.clinical import NeuroIPS, BLELinkGuard')
    content = content.replace('                    from vireon.core.security import SecurityEngine, NeuroIPS', '                    from vireon.core.detection import SecurityEngine\n                    from vireon.core.clinical import NeuroIPS')
    
    # JSON strings & metadata
    content = content.replace('vireon.core.security.BLELinkGuard', 'vireon.core.clinical.BLELinkGuard')
    content = content.replace('vireon.core.security.NeuroIPS', 'vireon.core.clinical.NeuroIPS')
    content = content.replace('vireon.core.security.SecurityEngine', 'vireon.core.detection.SecurityEngine')
    content = content.replace('vireon.core.security.LinearAutoencoderIDS', 'vireon.core.detection.LinearAutoencoderIDS')
    
    with open(filepath, 'w') as f:
        f.write(content)

for f in files_to_update:
    replace_in_file(f)

# Also remove security.py
os.remove('/home/ronin/Documents/n2/vireon/core/security.py')
print("Imports updated and security.py deleted")
