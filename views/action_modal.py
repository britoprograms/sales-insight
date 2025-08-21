# views/action_modal.py - Modal for selecting and confirming AI-generated actions

from __future__ import annotations
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.widgets import Button, Label, Checkbox, Static
from typing import List, Callable, Optional
from models.actions import get_action_store
import re


class ActionSelectionModal(ModalScreen[None]):
    """Modal for selecting AI-generated actions to implement."""
    
    DEFAULT_CSS = """
    ActionSelectionModal { align: center middle; }
    #action_modal { 
        width: 80%; 
        height: 70%;
        border: round white; 
        padding: 1; 
        background: $panel;
    }
    #title { 
        text-align: center; 
        padding: 0 0 1 0;
        color: $primary;
    }
    #actions_container {
        height: 1fr;
        border: solid $primary;
        padding: 1;
    }
    .action_item {
        margin: 0 0 1 0;
        padding: 1;
        border: solid $surface;
    }
    .action_text {
        margin: 0 0 1 0;
        padding: 0 1;
        text-wrap: auto;
    }
    
    /* Theme-specific styling for action text visibility */
    .theme-mono .action_text { 
        color: #FFFFFF !important; 
        background: transparent;
    }
    .theme-matrix .action_text { 
        color: #FFFFFF !important; 
        background: transparent;
    }
    .theme-light .action_text { 
        color: #111111 !important; 
        background: transparent;
    }
    
    /* Fallback styling if theme isn't applied */
    ActionSelectionModal .action_text {
        color: #FFFFFF;
    }
    #button_bar {
        height: 3;
        margin: 1 0 0 0;
    }
    """
    
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "confirm", "Confirm Selected"),
    ]
    
    def __init__(
        self, 
        customer_id: str, 
        actions_text: str, 
        on_confirm: Optional[Callable[[List[str]], None]] = None
    ):
        super().__init__()
        self.customer_id = customer_id
        self.actions_text = actions_text
        self.on_confirm = on_confirm
        self.action_checkboxes: List[Checkbox] = []
        self.parsed_actions = self._parse_actions(actions_text)
    
    def _parse_actions(self, actions_text: str) -> List[str]:
        """Parse AI-generated actions text into individual action items."""
        # Debug: Log what we received
        print(f"DEBUG: Received actions_text: '{actions_text}'")
        print(f"DEBUG: Text length: {len(actions_text)}")
        
        # Debug: Add fallback for empty/malformed text
        if not actions_text or not actions_text.strip():
            return ["No actions generated", "Check AI service connection", "Try again"]
            
        # Try simpler parsing first - split on numbered items
        lines = actions_text.strip().split('\n')
        actions = []
        
        # Method 1: Look for numbered lines (1., 2., etc.)
        for line in lines:
            line = line.strip()
            if re.match(r'^\d+\.', line):
                # Remove the number and add to actions
                action_text = re.sub(r'^\d+\.\s*', '', line).strip()
                if action_text:
                    actions.append(action_text)
        
        # Method 2: If no numbered items found, try bullet points or dashes
        if not actions:
            for line in lines:
                line = line.strip()
                if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                    action_text = re.sub(r'^[•\-\*]\s*', '', line).strip()
                    if action_text:
                        actions.append(action_text)
        
        # Method 3: If still no actions, try to split by sentence/line
        if not actions:
            for line in lines:
                line = line.strip()
                if line and len(line) > 10:  # Skip very short lines
                    actions.append(line)
        
        # Filter out empty actions (more lenient)
        actions = [action.strip() for action in actions if action and action.strip() and len(action.strip()) > 5]
        
        # If no valid actions found, add debugging info
        if not actions:
            actions = [f"Raw AI Response: {actions_text[:100]}...", "No valid actions parsed", "Check AI prompt format"]
        
        print(f"DEBUG: Final parsed actions: {actions}")
        return actions[:6]  # Limit to 6 actions max
    
    def on_mount(self) -> None:
        """Apply theme when modal is mounted."""
        try:
            # Get current theme from parent app and apply to modal
            theme_name = getattr(self.app, 'theme_name', 'mono')
            self.add_class(f"theme-{theme_name}")
        except Exception:
            # Fallback to mono theme if theme detection fails
            self.add_class("theme-mono")
    
    def compose(self) -> ComposeResult:
        with Vertical(id="action_modal"):
            yield Label(f"Recommended Actions for {self.customer_id}", id="title")
            
            with ScrollableContainer(id="actions_container"):
                for i, action in enumerate(self.parsed_actions):
                    with Vertical(classes="action_item"):
                        checkbox = Checkbox(
                            f"Action {i+1}", 
                            value=False,  # Default to unselected - user chooses
                            id=f"action_{i}"
                        )
                        self.action_checkboxes.append(checkbox)
                        yield checkbox
                        # Ensure we have text content for the label
                        action_text = str(action) if action else f"Action {i+1} - No description"
                        yield Static(action_text, classes="action_text")
            
            with Horizontal(id="button_bar"):
                yield Button("Confirm Selected", variant="success", id="btn_confirm")
                yield Button("Cancel", variant="default", id="btn_cancel")
                
            if not self.parsed_actions:
                yield Static("No valid actions could be parsed from AI response.", id="error_msg")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_confirm":
            self.action_confirm()
        elif event.button.id == "btn_cancel":
            self.action_cancel()
    
    def action_confirm(self) -> None:
        """Confirm selected actions and add to tracking."""
        selected_actions = []
        
        for i, checkbox in enumerate(self.action_checkboxes):
            if checkbox.value and i < len(self.parsed_actions):
                selected_actions.append(self.parsed_actions[i])
        
        if selected_actions:
            # Add actions to tracking system
            action_store = get_action_store()
            for action_desc in selected_actions:
                action_store.add_action(self.customer_id, action_desc)
            
            # Notify callback if provided
            if self.on_confirm:
                self.on_confirm(selected_actions)
                
            self.dismiss(len(selected_actions))
        else:
            # No actions selected
            self.dismiss(0)
    
    def action_cancel(self) -> None:
        """Cancel action selection."""
        self.dismiss(None)
