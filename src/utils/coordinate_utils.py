"""
Coordinate Utilities for NHL Rink Analysis

NHL Rink Coordinates:
- X-axis: -100 to 100 (goal lines at ±100, nets at ±89)
- Y-axis: -42.5 to 42.5 (center ice at 0, boards at ±42.5)

High-Danger Zone: Within 15 ft of net AND between goal posts (±8.5 ft)
- Example: xCoord: 80, yCoord: 5 = right side, 9 ft from net (high-danger)
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def is_high_danger(
    x: float,
    y: float,
    config: Optional[Dict] = None
) -> bool:
    """
    Check if a shot is in the high-danger zone.
    
    High-danger zone is defined as:
    - Within 15 feet of the net (x-distance)
    - Between goal posts (±8.5 feet in y-direction)
    
    Args:
        x: Shot x-coordinate (NHL rink: -100 to 100)
        y: Shot y-coordinate (NHL rink: -42.5 to 42.5)
        config: Optional config dict with zone parameters
    
    Returns:
        True if shot is in high-danger zone, False otherwise
    
    Example:
        >>> is_high_danger(x=85, y=5)
        True  # 4 ft from net, 5 ft from center
        
        >>> is_high_danger(x=50, y=10)
        False  # 39 ft from net
    """
    # Default config (GROK-approved zone definition)
    if config is None:
        config = {
            "x_threshold": 15,      # feet from net
            "y_threshold": 8.5,     # feet from center (goal posts)
            "net_x": 89,            # net position
        }
    
    # Calculate distance from net (x-direction)
    x_dist = abs(x) - config["net_x"]
    
    # Calculate distance from center (y-direction)
    y_dist = abs(y)
    
    # Check if within high-danger zone
    in_high_danger = (
        x_dist < config["x_threshold"] and
        y_dist < config["y_threshold"]
    )
    
    return in_high_danger


def get_zone_name(x: float, y: float, config: Optional[Dict] = None) -> str:
    """
    Get the zone name for a given coordinate.
    
    Zones:
    - "high_danger": Inner slot (high-danger zone)
    - "mid_range": Between 15-30 ft from net
    - "perimeter": Beyond 30 ft from net
    - "behind_goal": Beyond goal line (x > 100 or x < -100)
    
    Args:
        x: Shot x-coordinate
        y: Shot y-coordinate
        config: Optional config dict
    
    Returns:
        Zone name as string
    """
    if config is None:
        config = {
            "x_threshold": 15,
            "net_x": 89,
        }
    
    x_dist = abs(x) - config["net_x"]
    
    if x_dist < 0:
        return "behind_goal"
    elif x_dist < config["x_threshold"]:
        return "high_danger"
    elif x_dist < 30:
        return "mid_range"
    else:
        return "perimeter"
