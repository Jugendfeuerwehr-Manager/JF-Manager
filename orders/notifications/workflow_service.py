"""
Order workflow service for managing order status transitions.

This module handles order status workflow logic, including validation
of status transitions and workflow management.
"""

from typing import List, Dict, Set
import logging

from ..models import OrderStatus
from .base import BaseNotificationService

logger = logging.getLogger(__name__)


class OrderWorkflowService(BaseNotificationService):
    """
    Service for handling order status workflows and transitions.
    
    Manages the business logic for order status transitions, validation,
    and workflow enforcement.
    """
    
    # Define workflow transitions as a class constant for easy maintenance
    WORKFLOW_TRANSITIONS = {
        'pending': ['ordered', 'cancelled'],
        'ordered': ['received', 'cancelled'],
        'received': ['ready', 'defective'],
        'ready': ['delivered'],
        'delivered': [],  # Final state - no transitions allowed
        'cancelled': [],  # Final state - no transitions allowed
        'defective': ['ordered', 'cancelled'],  # Can reorder or cancel defective items
        
        # Legacy uppercase statuses (for backward compatibility)
        'ORDERED': ['RECEIVED', 'CANCELLED'],
        'RECEIVED': ['DELIVERED', 'CANCELLED'],
        'DELIVERED': [],
        'CANCELLED': []
    }
    
    # Define status categories for grouping and filtering
    STATUS_CATEGORIES = {
        'active': ['pending', 'ordered', 'received', 'ready'],
        'completed': ['delivered'],
        'terminated': ['cancelled', 'defective'],
        'actionable': ['pending', 'ordered', 'defective'],  # Statuses that require action
        'final': ['delivered', 'cancelled'],  # Statuses that end the workflow
    }
    
    @classmethod
    def get_available_transitions(cls, current_status) -> List[str]:
        """
        Get available status transitions from current status.
        
        Args:
            current_status: Current OrderStatus instance or status code string
            
        Returns:
            List of available status codes for transition
        """
        if hasattr(current_status, 'code'):
            status_code = current_status.code
        else:
            status_code = str(current_status)
        
        return cls.WORKFLOW_TRANSITIONS.get(status_code, [])
    
    @classmethod
    def can_transition_to(cls, current_status, target_status) -> bool:
        """
        Check if transition from current to target status is allowed.
        
        Args:
            current_status: Current OrderStatus instance or status code
            target_status: Target OrderStatus instance or status code
            
        Returns:
            True if transition is allowed, False otherwise
        """
        available_transitions = cls.get_available_transitions(current_status)
        
        if hasattr(target_status, 'code'):
            target_code = target_status.code
        else:
            target_code = str(target_status)
        
        return target_code in available_transitions
    
    @classmethod
    def get_next_statuses(cls, current_status) -> List[OrderStatus]:
        """
        Get OrderStatus objects for next possible statuses.
        
        Args:
            current_status: Current OrderStatus instance or status code
            
        Returns:
            List of OrderStatus instances that can be transitioned to
        """
        available_codes = cls.get_available_transitions(current_status)
        
        try:
            return list(
                OrderStatus.objects.filter(
                    code__in=available_codes, 
                    is_active=True
                ).order_by('display_order', 'name')
            )
        except Exception as e:
            logger.error(f"Failed to get next statuses: {e}")
            return []
    
    @classmethod
    def get_statuses_by_category(cls, category: str) -> List[str]:
        """
        Get status codes by category.
        
        Args:
            category: Status category ('active', 'completed', 'terminated', etc.)
            
        Returns:
            List of status codes in the specified category
        """
        return cls.STATUS_CATEGORIES.get(category, [])
    
    @classmethod
    def is_status_final(cls, status) -> bool:
        """
        Check if a status is a final state (no further transitions possible).
        
        Args:
            status: OrderStatus instance or status code
            
        Returns:
            True if status is final, False otherwise
        """
        if hasattr(status, 'code'):
            status_code = status.code
        else:
            status_code = str(status)
        
        return len(cls.get_available_transitions(status_code)) == 0
    
    @classmethod
    def is_status_actionable(cls, status) -> bool:
        """
        Check if a status requires action (is in actionable category).
        
        Args:
            status: OrderStatus instance or status code
            
        Returns:
            True if status requires action, False otherwise
        """
        if hasattr(status, 'code'):
            status_code = status.code.lower()
        else:
            status_code = str(status).lower()
        
        return status_code in cls.get_statuses_by_category('actionable')
    
    @classmethod
    def validate_bulk_transition(cls, order_items, target_status) -> Dict[str, any]:
        """
        Validate a bulk status transition for multiple order items.
        
        Args:
            order_items: List of OrderItem instances
            target_status: Target OrderStatus instance or status code
            
        Returns:
            Dictionary with validation results:
            {
                'valid': bool,
                'allowed_items': [list of items that can transition],
                'blocked_items': [list of items that cannot transition],
                'errors': [list of error messages]
            }
        """
        if hasattr(target_status, 'code'):
            target_code = target_status.code
        else:
            target_code = str(target_status)
        
        allowed_items = []
        blocked_items = []
        errors = []
        
        for item in order_items:
            try:
                if cls.can_transition_to(item.status, target_code):
                    allowed_items.append(item)
                else:
                    blocked_items.append(item)
                    errors.append(
                        f"Item '{item.item.name}' cannot transition from "
                        f"'{item.status.name}' to '{target_code}'"
                    )
            except Exception as e:
                blocked_items.append(item)
                errors.append(f"Error validating item '{item.item.name}': {e}")
        
        return {
            'valid': len(blocked_items) == 0,
            'allowed_items': allowed_items,
            'blocked_items': blocked_items,
            'errors': errors
        }
    
    @classmethod
    def get_workflow_diagram_data(cls) -> Dict[str, any]:
        """
        Get workflow data suitable for creating workflow diagrams.
        
        Returns:
            Dictionary with nodes and edges for workflow visualization
        """
        # Get all unique statuses from transitions
        all_statuses = set()
        for status, transitions in cls.WORKFLOW_TRANSITIONS.items():
            if status.isupper():  # Skip legacy uppercase versions
                continue
            all_statuses.add(status)
            all_statuses.update(transitions)
        
        # Create nodes
        nodes = []
        for status in sorted(all_statuses):
            category = 'final' if cls.is_status_final(status) else 'active'
            nodes.append({
                'id': status,
                'label': status.title(),
                'category': category,
                'actionable': cls.is_status_actionable(status)
            })
        
        # Create edges
        edges = []
        for from_status, to_statuses in cls.WORKFLOW_TRANSITIONS.items():
            if from_status.isupper():  # Skip legacy uppercase versions
                continue
            for to_status in to_statuses:
                edges.append({
                    'from': from_status,
                    'to': to_status,
                    'label': f"{from_status} → {to_status}"
                })
        
        return {
            'nodes': nodes,
            'edges': edges,
            'categories': cls.STATUS_CATEGORIES
        }
    
    @classmethod
    def get_status_statistics(cls, order_items_queryset) -> Dict[str, any]:
        """
        Get statistics about order item statuses.
        
        Args:
            order_items_queryset: QuerySet of OrderItem instances
            
        Returns:
            Dictionary with status statistics
        """
        try:
            from collections import Counter
            
            # Count items by status
            status_counts = Counter()
            for item in order_items_queryset:
                status_counts[item.status.code] += item.quantity
            
            # Categorize statuses
            categorized_counts = {}
            for category, statuses in cls.STATUS_CATEGORIES.items():
                categorized_counts[category] = sum(
                    status_counts.get(status, 0) for status in statuses
                )
            
            total_items = sum(status_counts.values())
            
            return {
                'total_items': total_items,
                'status_counts': dict(status_counts),
                'category_counts': categorized_counts,
                'completion_rate': (
                    categorized_counts.get('completed', 0) / total_items * 100
                    if total_items > 0 else 0
                )
            }
        
        except Exception as e:
            logger.error(f"Failed to calculate status statistics: {e}")
            return {
                'total_items': 0,
                'status_counts': {},
                'category_counts': {},
                'completion_rate': 0
            }
