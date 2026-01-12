"""
Water Level Task Configuration.
"""

from pydantic import Field
from core import GenerationConfig


class TaskConfig(GenerationConfig):
    """
    Water Level task configuration.
    
    Task: Given water in one container, predict the water level
    when poured into a different-shaped container.
    """
    
    domain: str = Field(default="water_level")
    image_size: tuple[int, int] = Field(default=(512, 512))
    
    generate_videos: bool = Field(default=True)
    video_fps: int = Field(default=10)
    
    # Container settings
    min_container_width: int = Field(default=60, description="Minimum container width")
    max_container_width: int = Field(default=150, description="Maximum container width")
    container_height: int = Field(default=200, description="Container height")
    
    # Water settings
    min_fill_ratio: float = Field(default=0.3, description="Minimum fill ratio in source container")
    max_fill_ratio: float = Field(default=0.8, description="Maximum fill ratio in source container")
    
    # Colors
    bg_color: tuple[int, int, int] = Field(default=(255, 255, 255))
    container_color: tuple[int, int, int] = Field(default=(100, 100, 100))
    water_color: tuple[int, int, int, int] = Field(default=(50, 150, 255, 180))  # RGBA
    measurement_color: tuple[int, int, int] = Field(default=(200, 50, 50))
