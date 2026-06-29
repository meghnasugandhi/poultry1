"""Calculator MCP Server — poultry calculations."""

TOOLS = [
    {"name": "calculate_fcr", "description": "Feed Conversion Ratio", "parameters": {"feed_consumed": "number", "weight_gain": "number"}},
    {"name": "calculate_mortality", "description": "Mortality Percentage", "parameters": {"dead_birds": "number", "total_birds": "number"}},
    {"name": "calculate_feed_consumption", "description": "Daily Feed Consumption", "parameters": {"bird_count": "number", "feed_per_bird": "number"}},
    {"name": "calculate_production_cost", "description": "Production Cost per Bird", "parameters": {"total_cost": "number", "bird_count": "number"}},
    {"name": "calculate_break_even", "description": "Break-Even Cost", "parameters": {"total_cost": "number", "birds_sold": "number"}},
]
