"""Water Level Task Prompts."""

import random

PROMPTS = {
    "default": [
        "Pour all water from container A into container B. Show the final water level in B.",
        "Transfer the water from the source container to the target. What will be the water level?",
        "If all water is moved from container A to B, predict and show the resulting water level.",
    ],
}

def get_prompt(task_type: str = "default") -> str:
    prompts = PROMPTS.get(task_type, PROMPTS["default"])
    return random.choice(prompts)

def get_all_prompts(task_type: str = "default") -> list[str]:
    return PROMPTS.get(task_type, PROMPTS["default"])
