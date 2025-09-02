# views/leader_menu.py - Neovim-style leader key menu

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, Label
from textual.timer import Timer
from typing import List, Tuple, Optional
from key_registry import get_key_registry

class LeaderKeyMenu(ModalScreen[None]):
    """
    Neovim-style leader key menu that appears in bottom-left corner.
    Shows contextual key bindings based on current view.
    """
    
    DEFAULT_CSS = """
    LeaderKeyMenu {
        align: left bottom;
        margin: 0 0 2 2;        /* Bottom and left margins */
    }
    
    #leader_container {
        width: auto;
        height: auto;
        min-width: 25;
        max-width: 45;
        border: round $primary;
        background: $surface;
        padding: 1;
    }
    
    #leader_title {
        text-align: center;
        color: $primary;
        margin: 0 0 1 0;
    }
    
    .key_row {
        height: 1;
        margin: 0;
    }
    
    .key_binding {
        color: $accent;
        min-width: 10;
        max-width: 10;
    }
    
    .key_description {
        color: $text;
        margin: 0 0 0 1;
    }
    
    /* Theme-specific overrides */
    .theme-mono #leader_container {
        border: round #FFFFFF;
        background: #333333;
    }
    
    .theme-mono #leader_title {
        color: #FFFFFF;
    }
    
    .theme-mono .key_binding {
        color: #FFFFFF;
    }
    
    .theme-mono .key_description {
        color: #AAAAAA;
    }
    
    .theme-matrix #leader_container {
        border: round #00FF7F;
        background: #001a0a;
    }
    
    .theme-matrix #leader_title {
        color: #00FF7F;
    }
    
    .theme-matrix .key_binding {
        color: #00FF7F;
    }
    
    .theme-matrix .key_description {
        color: #00995a;
    }
    
    .theme-light #leader_container {
        border: round #333333;
        background: #F5F5F5;
    }
    
    .theme-light #leader_title {
        color: #333333;
    }
    
    .theme-light .key_binding {
        color: #111111;
    }
    
    .theme-light .key_description {
        color: #777777;
    }
    """
    
    BINDINGS = [
        ("escape", "dismiss", ""),
        ("space", "dismiss", ""),  # Pressing space again dismisses
    ]
    
    def __init__(self, view_id: str = "global", theme_name: str = "mono"):
        super().__init__()
        self.view_id = view_id
        self.theme_name = theme_name
        self._auto_dismiss_timer: Optional[Timer] = None
        
        # Get key bindings for current context
        registry = get_key_registry()
        self.menu_items = registry.get_leader_menu_items(view_id)
    
    def compose(self) -> ComposeResult:
        with Vertical(id="leader_container"):
            yield Static("Leader Keys", id="leader_title")
            
            # Add key bindings
            for key, description in self.menu_items:
                with Horizontal(classes="key_row"):
                    # Format key display (pad for alignment with wider layout)
                    key_display = f"{key:<8}" if len(key) <= 8 else key
                    yield Static(key_display, classes="key_binding")
                    yield Static(description, classes="key_description")
    
    def on_mount(self) -> None:
        """Apply theme and set auto-dismiss timer"""
        # Apply current theme
        self.add_class(f"theme-{self.theme_name}")
        
        # Set auto-dismiss timer (3 seconds)
        self._auto_dismiss_timer = self.set_timer(8.0, self._auto_dismiss)
    
    def on_unmount(self) -> None:
        """Clean up timer"""
        if self._auto_dismiss_timer:
            self._auto_dismiss_timer.stop()
            self._auto_dismiss_timer = None
    
    def _auto_dismiss(self) -> None:
        """Auto-dismiss the menu after timeout"""
        self.dismiss()
    
    def on_key(self, event) -> None:
        """Handle any key press to dismiss menu and pass through"""
        # Stop the auto-dismiss timer since user is interacting
        if self._auto_dismiss_timer:
            self._auto_dismiss_timer.stop()
            self._auto_dismiss_timer = None
        
        # Don't consume the key event - let it pass through to the app
        if event.key in ["space", "escape"]:
            # Only consume space and escape to dismiss
            self.dismiss()
        else:
            # For other keys, dismiss but don't consume the event
            self.dismiss()
            # The key will be handled by the underlying app
    
    def action_dismiss(self) -> None:
        """Dismiss the menu"""
        self.dismiss()


class LeaderMenuManager:
    """Manager class to handle leader menu creation and lifecycle"""
    
    @staticmethod
    def show_leader_menu(app, current_view_id: str = "global") -> None:
        """Show the leader menu for the current context"""
        try:
            # Get current theme from app
            theme_name = getattr(app, 'theme_name', 'mono')
            
            # Create and show menu
            menu = LeaderKeyMenu(current_view_id, theme_name)
            app.push_screen(menu)
            
        except Exception as e:
            # Fallback: just show a status message
            if hasattr(app, '_status'):
                app._status(f"Leader menu error: {e}")
    
    @staticmethod
    def update_key_registry_for_view(view_id: str, additional_keys: List[Tuple[str, str]] = None):
        """Update key registry with view-specific keys if needed"""
        if additional_keys:
            registry = get_key_registry()
            for key, description in additional_keys:
                # This could be used to dynamically add keys per view
                pass
