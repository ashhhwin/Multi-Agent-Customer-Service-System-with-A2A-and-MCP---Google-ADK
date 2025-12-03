"""
a2a_patch.py: Compatibility Fix
This file applies a necessary patch to the A2A client module
to ensure proper functionality of the A2ACardResolver.
"""
import sys
import a2a.client.client as original_client_module
from a2a.client.card_resolver import A2ACardResolver

class ModifiedClientWrapper:
    """Wrapper class to patch in A2ACardResolver."""
    def __init__(self, original_module) -> None:
        # Copy all non-private attributes from the original module
        for attribute_name in dir(original_module):
            if not attribute_name.startswith('_'):
                setattr(self, attribute_name, getattr(original_module, attribute_name))
        
        # Explicitly set the A2ACardResolver
        self.A2ACardResolver = A2ACardResolver

# Apply the patch
modified_module = ModifiedClientWrapper(original_client_module)
sys.modules['a2a.client.client'] = modified_module