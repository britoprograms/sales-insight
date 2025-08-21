# models/actions.py - Action tracking data model and storage

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict
import uuid
import json
import os

class ActionStatus(Enum):
    """Status of a sales action."""
    WAITING = "Waiting for acceptance"
    IN_PROGRESS = "In-Progress" 
    COMPLETE = "Complete"

@dataclass
class Action:
    """Sales action tracking model."""
    action_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    customer_id: str = ""
    description: str = ""
    date_accepted: datetime = field(default_factory=datetime.now)
    review_date: datetime = field(init=False)  # Auto-calculated as 6 weeks from acceptance
    status: ActionStatus = ActionStatus.IN_PROGRESS
    
    def __post_init__(self):
        """Calculate review date as 6 weeks from acceptance date."""
        if not hasattr(self, 'review_date') or self.review_date is None:
            self.review_date = self.date_accepted + timedelta(weeks=6)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for display."""
        return {
            "action_id": self.action_id,
            "customer_id": self.customer_id,
            "description": self.description,
            "date_accepted": self.date_accepted.strftime("%Y-%m-%d"),
            "review_date": self.review_date.strftime("%Y-%m-%d"),
            "status": self.status.value
        }
    
    def mark_complete(self) -> None:
        """Mark action as complete."""
        self.status = ActionStatus.COMPLETE
    
    def is_overdue(self) -> bool:
        """Check if action review date has passed."""
        return datetime.now() > self.review_date and self.status != ActionStatus.COMPLETE

class ActionStore:
    """Persistent storage for actions using JSON file."""
    
    def __init__(self, filename: str = "actions.json"):
        self._filename = filename
        self._actions: List[Action] = []
        self._load_from_file()
    
    def add_action(self, customer_id: str, description: str) -> Action:
        """Add a new action for tracking."""
        action = Action(
            customer_id=customer_id,
            description=description,
            date_accepted=datetime.now()
        )
        self._actions.append(action)
        self._save_to_file()
        return action
    
    def get_all_actions(self) -> List[Action]:
        """Get all tracked actions."""
        return self._actions.copy()
    
    def get_actions_by_customer(self, customer_id: str) -> List[Action]:
        """Get all actions for a specific customer."""
        return [action for action in self._actions if action.customer_id == customer_id]
    
    def get_actions_by_status(self, status: ActionStatus) -> List[Action]:
        """Get all actions with specific status."""
        return [action for action in self._actions if action.status == status]
    
    def delete_action(self, action_id: str) -> bool:
        """Delete an action by ID."""
        for i, action in enumerate(self._actions):
            if action.action_id == action_id:
                del self._actions[i]
                self._save_to_file()
                return True
        return False
    
    def update_action_status(self, action_id: str, status: ActionStatus) -> bool:
        """Update status of an action."""
        for action in self._actions:
            if action.action_id == action_id:
                action.status = status
                self._save_to_file()
                return True
        return False
    
    def get_action_by_id(self, action_id: str) -> Optional[Action]:
        """Get specific action by ID."""
        for action in self._actions:
            if action.action_id == action_id:
                return action
        return None
    
    def get_overdue_actions(self) -> List[Action]:
        """Get all overdue actions."""
        return [action for action in self._actions if action.is_overdue()]
    
    def get_actions_count_by_status(self) -> Dict[str, int]:
        """Get count of actions by status."""
        counts = {}
        for status in ActionStatus:
            counts[status.value] = len(self.get_actions_by_status(status))
        return counts
    
    def _load_from_file(self) -> None:
        """Load actions from JSON file."""
        try:
            if os.path.exists(self._filename):
                with open(self._filename, 'r') as f:
                    data = json.load(f)
                    self._actions = []
                    for item in data:
                        action = Action(
                            action_id=item['action_id'],
                            customer_id=item['customer_id'],
                            description=item['description'],
                            date_accepted=datetime.fromisoformat(item['date_accepted']),
                            status=ActionStatus(item['status'])
                        )
                        action.review_date = datetime.fromisoformat(item['review_date'])
                        self._actions.append(action)
        except Exception:
            # If file is corrupted or any error, start with empty list
            self._actions = []
    
    def _save_to_file(self) -> None:
        """Save actions to JSON file."""
        try:
            data = []
            for action in self._actions:
                data.append({
                    'action_id': action.action_id,
                    'customer_id': action.customer_id,
                    'description': action.description,
                    'date_accepted': action.date_accepted.isoformat(),
                    'review_date': action.review_date.isoformat(),
                    'status': action.status.value
                })
            with open(self._filename, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            # Silently fail if save doesn't work
            pass

# Global action store instance
_action_store = None

def get_action_store() -> ActionStore:
    """Get singleton action store instance."""
    global _action_store
    if _action_store is None:
        _action_store = ActionStore()
    return _action_store