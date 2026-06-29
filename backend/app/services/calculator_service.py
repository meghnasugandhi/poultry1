CALCULATORS: dict = {}


def _register(name: str, formula: str, inputs: list[str]):
    def decorator(fn):
        CALCULATORS[name] = {"name": name, "formula": formula, "inputs": inputs, "fn": fn}
        return fn

    return decorator


@_register("fcr", "FCR = Total Feed Consumed / Total Weight Gain", ["feed_consumed", "weight_gain"])
def fcr(inputs: dict) -> dict:
    feed = inputs["feed_consumed"]
    gain = inputs["weight_gain"]
    value = feed / gain if gain else 0
    return {
        "value": round(value, 3),
        "steps": [
            f"Total Feed Consumed = {feed} kg",
            f"Total Weight Gain = {gain} kg",
            f"FCR = {feed} / {gain} = {round(value, 3)}",
        ],
        "explanation": "Feed Conversion Ratio measures feed efficiency. Lower FCR means better efficiency.",
    }


@_register(
    "mortality_percentage",
    "Mortality % = (Dead Birds / Total Birds) × 100",
    ["dead_birds", "total_birds"],
)
def mortality(inputs: dict) -> dict:
    dead = inputs["dead_birds"]
    total = inputs["total_birds"]
    value = (dead / total * 100) if total else 0
    return {
        "value": round(value, 2),
        "steps": [
            f"Dead Birds = {dead}",
            f"Total Birds = {total}",
            f"Mortality % = ({dead} / {total}) × 100 = {round(value, 2)}%",
        ],
        "explanation": "Mortality percentage indicates flock health. Industry standard is below 5%.",
    }


@_register(
    "feed_consumption",
    "Daily Feed = Number of Birds × Feed per Bird",
    ["bird_count", "feed_per_bird"],
)
def feed_consumption(inputs: dict) -> dict:
    birds = inputs["bird_count"]
    per_bird = inputs["feed_per_bird"]
    value = birds * per_bird
    return {
        "value": round(value, 2),
        "steps": [
            f"Bird Count = {birds}",
            f"Feed per Bird = {per_bird} kg",
            f"Daily Feed = {birds} × {per_bird} = {round(value, 2)} kg",
        ],
        "explanation": "Total daily feed requirement for the flock.",
    }


@_register(
    "production_cost",
    "Cost per Bird = Total Production Cost / Number of Birds",
    ["total_cost", "bird_count"],
)
def production_cost(inputs: dict) -> dict:
    cost = inputs["total_cost"]
    birds = inputs["bird_count"]
    value = cost / birds if birds else 0
    return {
        "value": round(value, 2),
        "steps": [
            f"Total Production Cost = ₹{cost}",
            f"Number of Birds = {birds}",
            f"Cost per Bird = ₹{cost} / {birds} = ₹{round(value, 2)}",
        ],
        "explanation": "Average production cost per bird including feed, medicine, and labor.",
    }


@_register(
    "feed_cost_per_bird",
    "Feed Cost per Bird = Total Feed Cost / Number of Birds",
    ["feed_cost", "bird_count"],
)
def feed_cost_per_bird(inputs: dict) -> dict:
    cost = inputs["feed_cost"]
    birds = inputs["bird_count"]
    value = cost / birds if birds else 0
    return {
        "value": round(value, 2),
        "steps": [
            f"Total Feed Cost = ₹{cost}",
            f"Number of Birds = {birds}",
            f"Feed Cost per Bird = ₹{cost} / {birds} = ₹{round(value, 2)}",
        ],
        "explanation": "Feed cost per bird is a key profitability indicator.",
    }


@_register(
    "growth_rate",
    "Growth Rate = (Final Weight - Initial Weight) / Days",
    ["initial_weight", "final_weight", "days"],
)
def growth_rate(inputs: dict) -> dict:
    initial = inputs["initial_weight"]
    final = inputs["final_weight"]
    days = inputs["days"]
    value = (final - initial) / days if days else 0
    return {
        "value": round(value, 3),
        "steps": [
            f"Initial Weight = {initial} kg",
            f"Final Weight = {final} kg",
            f"Days = {days}",
            f"Growth Rate = ({final} - {initial}) / {days} = {round(value, 3)} kg/day",
        ],
        "explanation": "Average daily weight gain per bird.",
    }


@_register(
    "average_weight_gain",
    "Avg Weight Gain = Total Weight Gain / Number of Birds",
    ["total_weight_gain", "bird_count"],
)
def average_weight_gain(inputs: dict) -> dict:
    gain = inputs["total_weight_gain"]
    birds = inputs["bird_count"]
    value = gain / birds if birds else 0
    return {
        "value": round(value, 3),
        "steps": [
            f"Total Weight Gain = {gain} kg",
            f"Number of Birds = {birds}",
            f"Average Weight Gain = {gain} / {birds} = {round(value, 3)} kg/bird",
        ],
        "explanation": "Average weight gained per bird in the batch.",
    }


@_register(
    "break_even_cost",
    "Break-Even = Total Cost / Birds Sold",
    ["total_cost", "birds_sold"],
)
def break_even(inputs: dict) -> dict:
    cost = inputs["total_cost"]
    sold = inputs["birds_sold"]
    value = cost / sold if sold else 0
    return {
        "value": round(value, 2),
        "steps": [
            f"Total Cost = ₹{cost}",
            f"Birds Sold = {sold}",
            f"Break-Even Cost = ₹{cost} / {sold} = ₹{round(value, 2)} per bird",
        ],
        "explanation": "Minimum selling price per bird to cover all costs.",
    }
