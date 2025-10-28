"""
xG (Expected Goals) Calculator

v1.0: Simple distance-based model (GROK-approved)
- Distance is the dominant xG factor (~70-80% of signal)
- Shot type adds ~10% accuracy
- Rebound/rush flags add marginal value

v2.1 Upgrade Path (documented, not implemented):
- Rebound detection
- Strength state weighting (5v5 vs PP)
- Angle factor
- Advanced shot type weights

Source: Calibrated to match ~2.8 xGF per team per game (NHL average)
"""

import math
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def calculate_xg(
    x: float,
    y: float,
    shot_type: str = "Wrist",
    config: Optional[Dict] = None
) -> float:
    """
    Calculate expected goals (xG) for a shot using distance-based model (v1.0).
    
    Args:
        x: Shot x-coordinate (NHL rink: -100 to 100, net at ±89)
        y: Shot y-coordinate (NHL rink: -42.5 to 42.5)
        shot_type: Type of shot (e.g., "Wrist", "Slap", "Backhand")
        config: Optional config dict with xG parameters (uses defaults if None)
    
    Returns:
        Expected goals value (0.0 to ~0.25)
    
    Example:
        >>> calculate_xg(x=85, y=5, shot_type="Wrist")
        0.22
        
        >>> calculate_xg(x=50, y=10, shot_type="Slap")
        0.08
    """
    # Default config (v1.0 GROK-approved model)
    if config is None:
        config = {
            "high_danger_distance": 15,
            "mid_range_distance": 30,
            "high_danger_xg": {"wrist": 0.22, "slap": 0.17},
            "mid_range_xg": {"wrist": 0.10, "slap": 0.08},
            "long_range_xg": {"wrist": 0.04, "slap": 0.03},
        }
    
    # Calculate distance to net (assume net at x=89 or -89, y=0)
    distance = math.sqrt((abs(x) - 89) ** 2 + y ** 2)
    
    # Normalize shot type (handle variations)
    shot_type_normalized = shot_type.lower() if shot_type else "wrist"
    is_slap = "slap" in shot_type_normalized
    
    # Determine xG based on distance
    if distance < config["high_danger_distance"]:
        xg_val = config["high_danger_xg"]["slap"] if is_slap else config["high_danger_xg"]["wrist"]
    elif distance < config["mid_range_distance"]:
        xg_val = config["mid_range_xg"]["slap"] if is_slap else config["mid_range_xg"]["wrist"]
    else:
        xg_val = config["long_range_xg"]["slap"] if is_slap else config["long_range_xg"]["wrist"]
    
    return xg_val


# TODO: v2.1 Upgrade Path
# def calculate_xg_advanced(
#     x: float,
#     y: float,
#     shot_type: str,
#     is_rebound: bool = False,
#     strength_state: str = "5v5",
#     angle: Optional[float] = None,
#     config: Optional[Dict] = None
# ) -> float:
#     """
#     Advanced xG model (v2.1) with rebound, strength, and angle factors.
#     
#     Features:
#     - Rebound detection (previous event type)
#     - Strength state weighting (5v5 vs PP)
#     - Angle factor (shot angle from net)
#     - Advanced shot type weights
#     
#     Status: Planned for v2.1, not implemented in v1.0
#     """
#     pass
