import pytest
from vireon.plugins.sdk import VireonPluginSDK

class DummyPlugin(VireonPluginSDK):
    def start(self):
        self._is_running = True
    def stop(self):
        self._is_running = False

def test_vireon_sdk():
    plugin = DummyPlugin("dummy", "1.0", "desc")
    assert plugin.name == "dummy"
    assert plugin.version == "1.0"
    assert plugin.description == "desc"
    
    plugin.initialize(None, None)
    assert plugin.twin is None
    assert plugin.event_bus is None
    
    assert not plugin.is_running()
    
    plugin.start()
    assert plugin.is_running()
    
    meta = plugin.get_metadata()
    assert meta["name"] == "dummy"
    assert meta["running"] == True
    
    plugin.stop()
    assert not plugin.is_running()
