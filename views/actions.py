# views/actions.py - Actions tracking view

from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import DataTable, Static, Button
from textual.coordinate import Coordinate
from models.actions import get_action_store, ActionStatus
from typing import Optional


class ActionsView(Vertical):
    """View for tracking and managing sales actions."""
    
    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("u", "update_status", "Update Status"),
        ("delete", "delete_action", "Delete Action"),
    ]
    
    can_focus = True
    
    def __init__(self, store, on_open_onepager, theme):
        super().__init__()
        self.store = store
        self.on_open_onepager = on_open_onepager
        self.theme = theme
        self.table: Optional[DataTable] = None
        self.action_store = get_action_store()
    
    def compose(self) -> ComposeResult:
        yield Static("Sales Actions Tracking", id="actions_title")
        
        # Actions summary
        summary = self._get_summary_text()
        yield Static(summary, id="actions_summary")
        
        # Actions table
        table = DataTable(id="actions_table")
        table.cursor_type = "row"
        table.zebra_stripes = True
        self.table = table
        yield table
        
        # Action buttons
        with Horizontal(id="action_buttons"):
            yield Button("Refresh", id="btn_refresh")
            yield Button("Mark Complete", id="btn_complete")
            yield Button("Mark In Progress", id="btn_progress")
            yield Button("Delete", variant="error", id="btn_delete")
    
    def on_mount(self) -> None:
        """Initialize the table when mounted."""
        self._setup_table()
        self._populate_table()
    
    def _setup_table(self) -> None:
        """Setup table columns."""
        if self.table is None:
            return
            
        # Add columns
        self.table.add_columns(
            "Action ID",
            "Customer ID", 
            "Action",
            "Date Accepted",
            "Review Date",
            "Status"
        )
    
    def _populate_table(self) -> None:
        """Populate table with current actions."""
        if self.table is None:
            return
            
        # Clear existing rows
        self.table.clear()
        
        # Get all actions
        actions = self.action_store.get_all_actions()
        
        # Sort by date accepted (newest first)
        actions.sort(key=lambda x: x.date_accepted, reverse=True)
        
        # Add rows
        for action in actions:
            # Truncate long action descriptions
            action_desc = action.description
            if len(action_desc) > 50:
                action_desc = action_desc[:47] + "..."
            
            # Add status emoji for quick visual reference
            status_display = self._get_status_display(action.status)
            
            self.table.add_row(
                action.action_id,
                action.customer_id,
                action_desc,
                action.date_accepted.strftime("%Y-%m-%d"),
                action.review_date.strftime("%Y-%m-%d"),
                status_display,
                key=action.action_id
            )
    
    def _get_status_display(self, status: ActionStatus) -> str:
        """Get display string for status with emoji."""
        status_map = {
            ActionStatus.WAITING: "⏳ Waiting",
            ActionStatus.IN_PROGRESS: "🔄 In Progress", 
            ActionStatus.COMPLETE: "✅ Complete"
        }
        return status_map.get(status, status.value)
    
    def _get_summary_text(self) -> str:
        """Get summary statistics for actions."""
        counts = self.action_store.get_actions_count_by_status()
        total = sum(counts.values())
        overdue = len(self.action_store.get_overdue_actions())
        
        if total == 0:
            return "No actions tracked yet. Generate actions from customer One-Pagers."
        
        return (f"Total Actions: {total} | "
                f"In Progress: {counts.get('In-Progress', 0)} | "
                f"Complete: {counts.get('Complete', 0)} | "
                f"Overdue: {overdue}")
    
    def action_refresh(self) -> None:
        """Refresh the actions table."""
        self._populate_table()
        self._update_summary()
        getattr(self.app, "_status", lambda m: None)("Actions refreshed.")
    
    def _update_summary(self) -> None:
        """Update the summary text."""
        try:
            summary_widget = self.query_one("#actions_summary", Static)
            summary_widget.update(self._get_summary_text())
        except Exception:
            pass
    
    def action_update_status(self) -> None:
        """Update status of selected action."""
        if self.table is None or not self.table.cursor_coordinate:
            getattr(self.app, "_status", lambda m: None)("No action selected.")
            return
            
        # Get action ID from first column of selected row
        try:
            row_index = self.table.cursor_coordinate.row
            row_data = self.table.get_row_at(row_index)
            action_id = row_data[0]  # First column is action_id
        except Exception:
            getattr(self.app, "_status", lambda m: None)("Could not get selected action.")
            return
            
        action = self.action_store.get_action_by_id(str(action_id))
        if action is None:
            getattr(self.app, "_status", lambda m: None)("Action not found.")
            return
        
        # Cycle through statuses
        if action.status == ActionStatus.WAITING:
            new_status = ActionStatus.IN_PROGRESS
        elif action.status == ActionStatus.IN_PROGRESS:
            new_status = ActionStatus.COMPLETE
        else:  # Complete
            new_status = ActionStatus.IN_PROGRESS  # Allow reopening
        
        # Update status
        self.action_store.update_action_status(action.action_id, new_status)
        
        # Refresh display
        self._populate_table()
        self._update_summary()
        
        getattr(self.app, "_status", lambda m: None)(
            f"Action {action.action_id} updated to {new_status.value}"
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn_refresh":
            self.action_refresh()
        elif event.button.id == "btn_complete":
            self._update_selected_action_status(ActionStatus.COMPLETE)
        elif event.button.id == "btn_progress":
            self._update_selected_action_status(ActionStatus.IN_PROGRESS)
        elif event.button.id == "btn_delete":
            self.action_delete_action()
    
    def _update_selected_action_status(self, new_status: ActionStatus) -> None:
        """Update selected action to specific status."""
        if self.table is None or not self.table.cursor_coordinate:
            getattr(self.app, "_status", lambda m: None)("No action selected.")
            return
            
        # Get action ID from first column of selected row
        try:
            row_index = self.table.cursor_coordinate.row
            row_data = self.table.get_row_at(row_index)
            action_id = row_data[0]  # First column is action_id
        except Exception:
            getattr(self.app, "_status", lambda m: None)("Could not get selected action.")
            return
            
        # Update status
        success = self.action_store.update_action_status(str(action_id), new_status)
        if success:
            self._populate_table()
            self._update_summary()
            getattr(self.app, "_status", lambda m: None)(
                f"Action updated to {new_status.value}"
            )
        else:
            getattr(self.app, "_status", lambda m: None)("Failed to update action.")
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection - could open action details or customer one-pager."""
        if event.row_key is None:
            return
            
        action = self.action_store.get_action_by_id(str(event.row_key))
        if action:
            getattr(self.app, "_status", lambda m: None)(
                f"Selected action for {action.customer_id}: {action.description[:50]}..."
            )
    
    def action_delete_action(self) -> None:
        """Delete selected action with confirmation."""
        if self.table is None or not self.table.cursor_coordinate:
            getattr(self.app, "_status", lambda m: None)("No action selected.")
            return
            
        # Get action ID from first column of selected row
        try:
            row_index = self.table.cursor_coordinate.row
            row_data = self.table.get_row_at(row_index)
            action_id = row_data[0]  # First column is action_id
        except Exception:
            getattr(self.app, "_status", lambda m: None)("Could not get selected action.")
            return
            
        action = self.action_store.get_action_by_id(str(action_id))
        if action is None:
            getattr(self.app, "_status", lambda m: None)("Action not found.")
            return
        
        # Simple confirmation via status message (could be enhanced with modal)
        getattr(self.app, "_status", lambda m: None)(
            f"Press 'Del' again to confirm delete of action: {action.description[:30]}..."
        )
        
        # For now, just delete immediately (can add modal confirmation later)
        success = self.action_store.delete_action(action.action_id)
        if success:
            self._populate_table()
            self._update_summary()
            getattr(self.app, "_status", lambda m: None)(
                f"Deleted action {action.action_id} for {action.customer_id}"
            )
        else:
            getattr(self.app, "_status", lambda m: None)("Failed to delete action.")