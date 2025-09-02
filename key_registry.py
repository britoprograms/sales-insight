# key_registry.py - Centralized key binding registry for leader menu system

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

class KeyContext(Enum):
    """Different contexts where keys can be active"""
    GLOBAL = "global"           # Available everywhere
    DECLINERS = "decliners"     # Decliners view
    GROWERS = "growers"         # Growers view  
    ONEPAGER = "onepager"       # One-Pager view
    ACTIONS = "actions"         # Actions view
    DASHBOARD = "dashboard"     # Dashboard focus
    MODAL = "modal"             # When modal is open

@dataclass
class KeyBinding:
    """Represents a key binding with metadata"""
    key: str                    # The actual key (e.g., "t", "r", "/")
    action: str                 # Action name/description
    description: str            # Human-readable description
    contexts: List[KeyContext]  # Where this key is active
    priority: int = 0           # Display priority (higher = show first)

class KeyRegistry:
    """Central registry for all key bindings in the application"""
    
    def __init__(self):
        self._bindings: List[KeyBinding] = []
        self._setup_default_bindings()
    
    def _setup_default_bindings(self):
        """Setup all default key bindings"""
        
        # Global bindings (always available)
        self._bindings.extend([
            KeyBinding("t", "cycle_theme", "Cycle themes ", [KeyContext.GLOBAL], priority=10),
            KeyBinding("r", "refresh", "Refresh current view", [KeyContext.GLOBAL], priority=9),
            KeyBinding("f", "show_formulas", "Show formula reference", [KeyContext.GLOBAL], priority=8),
            KeyBinding("Esc", "quit", "Exit application", [KeyContext.GLOBAL], priority=1),
            KeyBinding("Tab", "cycle_tab", "Next navigation tab", [KeyContext.GLOBAL], priority=7),
            KeyBinding("Shift+Tab", "cycle_tab_reverse", "Previous navigation tab", [KeyContext.GLOBAL], priority=6),
        ])
        
        # Navigation/Table bindings
        table_contexts = [KeyContext.DECLINERS, KeyContext.GROWERS]
        self._bindings.extend([
            KeyBinding("/", "focus_search", "Search customer list", table_contexts, priority=15),
            KeyBinding("Enter", "open_selected", "Open customer details", table_contexts, priority=14),
            KeyBinding("↑/↓", "navigate", "Navigate table rows", table_contexts, priority=5),
        ])
        
        # One-Pager specific bindings
        self._bindings.extend([
            KeyBinding("b", "chart_browser", "Open chart in browser", [KeyContext.ONEPAGER], priority=13),
            KeyBinding("g", "generate_actions", "Generate AI actions", [KeyContext.ONEPAGER], priority=12),
        ])
        
        # Actions view bindings
        self._bindings.extend([
            KeyBinding("u", "update_status", "Update action status", [KeyContext.ACTIONS], priority=11),
            KeyBinding("Del", "delete_action", "Delete selected action", [KeyContext.ACTIONS], priority=4),
        ])
    
    def get_bindings_for_context(self, context: KeyContext, include_global: bool = True) -> List[KeyBinding]:
        """Get all key bindings for a specific context"""
        bindings = []
        
        for binding in self._bindings:
            if context in binding.contexts:
                bindings.append(binding)
            elif include_global and KeyContext.GLOBAL in binding.contexts:
                bindings.append(binding)
        
        # Sort by priority (highest first), then by key
        bindings.sort(key=lambda b: (-b.priority, b.key))
        return bindings
    
    def get_context_from_view_id(self, view_id: str) -> KeyContext:
        """Map view ID to key context"""
        context_map = {
            "decliners": KeyContext.DECLINERS,
            "growers": KeyContext.GROWERS,
            "onepager": KeyContext.ONEPAGER,
            "actions": KeyContext.ACTIONS,
            "dashboard": KeyContext.DASHBOARD,
        }
        return context_map.get(view_id, KeyContext.GLOBAL)
    
    def get_leader_menu_items(self, view_id: str) -> List[tuple]:
        """Get formatted menu items for the leader menu"""
        context = self.get_context_from_view_id(view_id)
        bindings = self.get_bindings_for_context(context, include_global=True)
        
        # Format as (key, description) tuples for display
        menu_items = []
        for binding in bindings:
            # Skip space and tab keys from leader menu (they're meta keys)
            if binding.key in ["Space", "Tab", "Shift+Tab"]:
                continue
            menu_items.append((binding.key, binding.description))
        
        return menu_items
    
    def register_binding(self, key: str, action: str, description: str, 
                        contexts: List[KeyContext], priority: int = 0):
        """Register a new key binding"""
        binding = KeyBinding(key, action, description, contexts, priority)
        self._bindings.append(binding)
    
    def remove_binding(self, key: str, context: Optional[KeyContext] = None):
        """Remove a key binding"""
        self._bindings = [b for b in self._bindings 
                         if not (b.key == key and (context is None or context in b.contexts))]

# Global registry instance
_key_registry = None

def get_key_registry() -> KeyRegistry:
    """Get singleton key registry instance"""
    global _key_registry
    if _key_registry is None:
        _key_registry = KeyRegistry()
    return _key_registry
