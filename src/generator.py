"""
Water Level Task Generator.

Generates water transfer scenarios between containers of different widths.
Task: Predict the water level when water is poured from one container to another.
"""

import random
import tempfile
import math
from pathlib import Path
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont

from core import BaseGenerator, TaskPair, ImageRenderer
from core.video_utils import VideoGenerator
from .config import TaskConfig
from .prompts import get_prompt


class TaskGenerator(BaseGenerator):
    """Water level prediction task generator."""
    
    def __init__(self, config: TaskConfig):
        super().__init__(config)
        self.renderer = ImageRenderer(image_size=config.image_size)
        
        self.video_generator = None
        if config.generate_videos and VideoGenerator.is_available():
            self.video_generator = VideoGenerator(fps=config.video_fps, output_format="mp4")
    
    def generate_task_pair(self, task_id: str) -> TaskPair:
        """Generate one task pair."""
        task_data = self._generate_task_data()
        
        first_image = self._render_initial_state(task_data)
        final_image = self._render_final_state(task_data)
        
        video_path = None
        if self.config.generate_videos and self.video_generator:
            video_path = self._generate_video(first_image, final_image, task_id, task_data)
        
        prompt = get_prompt(task_data.get("type", "default"))
        
        return TaskPair(
            task_id=task_id,
            domain=self.config.domain,
            prompt=prompt,
            first_image=first_image,
            final_image=final_image,
            ground_truth_video=video_path
        )
    
    def _generate_task_data(self) -> dict:
        """Generate container dimensions and water volume."""
        # Source container dimensions
        source_width = random.randint(self.config.min_container_width, self.config.max_container_width)
        source_height = self.config.container_height
        
        # Target container dimensions (different width)
        target_width = random.randint(self.config.min_container_width, self.config.max_container_width)
        # Ensure target is meaningfully different
        while abs(target_width - source_width) < 20:
            target_width = random.randint(self.config.min_container_width, self.config.max_container_width)
        target_height = self.config.container_height
        
        # Water fill ratio in source
        source_fill = random.uniform(self.config.min_fill_ratio, self.config.max_fill_ratio)
        source_water_height = int(source_height * source_fill)
        
        # Calculate water volume (cross-sectional area * height)
        water_volume = source_width * source_water_height
        
        # Calculate target water height (same volume, different width)
        target_water_height = water_volume / target_width
        
        # Ensure target water fits in container
        if target_water_height > target_height:
            # Water would overflow - cap it and recalculate
            target_water_height = target_height
            # Adjust source to match
            water_volume = target_width * target_water_height
            source_water_height = int(water_volume / source_width)
        
        target_water_height = int(target_water_height)
        
        return {
            "source_width": source_width,
            "source_height": source_height,
            "source_water_height": source_water_height,
            "target_width": target_width,
            "target_height": target_height,
            "target_water_height": target_water_height,
            "water_volume": water_volume,
            "type": "default",
        }
    
    def _draw_container(self, draw: ImageDraw.Draw, x: int, y: int, 
                        width: int, height: int, water_height: int, 
                        show_measurements: bool = True, label: str = None):
        """Draw a container with water and measurement markings."""
        # Container outline (open top)
        container_color = self.config.container_color
        wall_thickness = 4
        
        # Left wall
        draw.rectangle([x, y, x + wall_thickness, y + height + wall_thickness], fill=container_color)
        # Right wall  
        draw.rectangle([x + width, y, x + width + wall_thickness, y + height + wall_thickness], fill=container_color)
        # Bottom
        draw.rectangle([x, y + height, x + width + wall_thickness, y + height + wall_thickness], fill=container_color)
        
        # Water (inside container)
        if water_height > 0:
            water_y = y + height - water_height
            # Create water with transparency effect
            water_color = self.config.water_color[:3]  # RGB only for simple fill
            draw.rectangle(
                [x + wall_thickness, water_y, x + width, y + height],
                fill=water_color
            )
            # Add wave effect at top
            for i in range(0, width - wall_thickness, 10):
                wave_offset = int(3 * math.sin(i * 0.3))
                draw.ellipse(
                    [x + wall_thickness + i - 3, water_y + wave_offset - 3,
                     x + wall_thickness + i + 3, water_y + wave_offset + 3],
                    fill=water_color
                )
        
        # Measurement lines
        if show_measurements:
            num_marks = 5
            for i in range(num_marks + 1):
                mark_y = y + height - (i * height // num_marks)
                mark_length = 15 if i % 2 == 0 else 8
                # Left side marks
                draw.line([(x - mark_length, mark_y), (x, mark_y)], 
                         fill=(150, 150, 150), width=1)
        
        # Label
        if label:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            except:
                font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), label, font=font)
            text_width = bbox[2] - bbox[0]
            draw.text((x + width // 2 - text_width // 2, y + height + 15), 
                     label, fill=(100, 100, 100), font=font)
    
    def _draw_water_level_indicator(self, draw: ImageDraw.Draw, x: int, y: int, 
                                     width: int, height: int, water_height: int):
        """Draw an arrow pointing to the water level."""
        water_y = y + height - water_height
        
        # Arrow pointing to water level
        arrow_x = x + width + 30
        draw.line([(arrow_x, water_y), (arrow_x + 30, water_y)], 
                 fill=self.config.measurement_color, width=2)
        # Arrowhead
        draw.polygon([
            (arrow_x, water_y),
            (arrow_x + 8, water_y - 5),
            (arrow_x + 8, water_y + 5)
        ], fill=self.config.measurement_color)
        
        # Level text
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except:
            font = ImageFont.load_default()
        draw.text((arrow_x + 35, water_y - 10), f"{water_height}px", 
                 fill=self.config.measurement_color, font=font)
    
    def _render_initial_state(self, task_data: dict) -> Image.Image:
        """Render initial state with water in source container, empty target."""
        width, height = self.config.image_size
        img = Image.new('RGB', (width, height), self.config.bg_color)
        draw = ImageDraw.Draw(img)
        
        source_width = task_data["source_width"]
        source_height = task_data["source_height"]
        source_water_height = task_data["source_water_height"]
        target_width = task_data["target_width"]
        target_height = task_data["target_height"]
        
        # Position containers
        gap = 80
        total_width = source_width + target_width + gap
        start_x = (width - total_width) // 2
        container_y = (height - source_height) // 2
        
        # Draw source container with water
        self._draw_container(draw, start_x, container_y, source_width, source_height,
                           source_water_height, show_measurements=True, label="A (Source)")
        
        # Draw empty target container
        target_x = start_x + source_width + gap
        self._draw_container(draw, target_x, container_y, target_width, target_height,
                           0, show_measurements=True, label="B (Target)")
        
        # Draw arrow between containers
        arrow_y = container_y + source_height // 2
        arrow_start = start_x + source_width + 20
        arrow_end = target_x - 15
        draw.line([(arrow_start, arrow_y), (arrow_end, arrow_y)], fill=(100, 100, 100), width=3)
        draw.polygon([
            (arrow_end, arrow_y),
            (arrow_end - 10, arrow_y - 7),
            (arrow_end - 10, arrow_y + 7)
        ], fill=(100, 100, 100))
        
        # Draw question mark on target
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        except:
            font = ImageFont.load_default()
        draw.text((target_x + target_width // 2 - 15, container_y + target_height // 2 - 25),
                 "?", fill=(200, 200, 200), font=font)
        
        return img
    
    def _render_final_state(self, task_data: dict) -> Image.Image:
        """Render final state with water transferred to target container."""
        width, height = self.config.image_size
        img = Image.new('RGB', (width, height), self.config.bg_color)
        draw = ImageDraw.Draw(img)
        
        source_width = task_data["source_width"]
        source_height = task_data["source_height"]
        target_width = task_data["target_width"]
        target_height = task_data["target_height"]
        target_water_height = task_data["target_water_height"]
        
        # Position containers
        gap = 80
        total_width = source_width + target_width + gap
        start_x = (width - total_width) // 2
        container_y = (height - source_height) // 2
        
        # Draw empty source container
        self._draw_container(draw, start_x, container_y, source_width, source_height,
                           0, show_measurements=True, label="A (Empty)")
        
        # Draw target container with water
        target_x = start_x + source_width + gap
        self._draw_container(draw, target_x, container_y, target_width, target_height,
                           target_water_height, show_measurements=True, label="B (Filled)")
        
        # Draw water level indicator
        self._draw_water_level_indicator(draw, target_x, container_y, target_width, 
                                        target_height, target_water_height)
        
        return img
    
    def _generate_video(self, first_image: Image.Image, final_image: Image.Image,
                        task_id: str, task_data: dict) -> str:
        """Generate video showing water pouring animation."""
        temp_dir = Path(tempfile.gettempdir()) / f"{self.config.domain}_videos"
        temp_dir.mkdir(parents=True, exist_ok=True)
        video_path = temp_dir / f"{task_id}_ground_truth.mp4"
        
        frames = []
        hold_frames = 5
        animation_frames = 30
        
        # Hold initial
        for _ in range(hold_frames):
            frames.append(first_image.copy())
        
        # Animate water transfer
        source_water = task_data["source_water_height"]
        target_water = task_data["target_water_height"]
        
        for i in range(animation_frames):
            progress = i / (animation_frames - 1)
            # Ease out curve
            progress = 1 - (1 - progress) ** 2
            
            current_source = int(source_water * (1 - progress))
            current_target = int(target_water * progress)
            
            frame = self._render_transfer_frame(task_data, current_source, current_target, progress)
            frames.append(frame)
        
        # Hold final
        for _ in range(hold_frames * 2):
            frames.append(final_image.copy())
        
        result = self.video_generator.create_video_from_frames(frames, video_path)
        return str(result) if result else None
    
    def _render_transfer_frame(self, task_data: dict, source_water: int, 
                               target_water: int, progress: float) -> Image.Image:
        """Render a frame during water transfer."""
        width, height = self.config.image_size
        img = Image.new('RGB', (width, height), self.config.bg_color)
        draw = ImageDraw.Draw(img)
        
        source_width = task_data["source_width"]
        source_height = task_data["source_height"]
        target_width = task_data["target_width"]
        target_height = task_data["target_height"]
        
        # Position containers
        gap = 80
        total_width = source_width + target_width + gap
        start_x = (width - total_width) // 2
        container_y = (height - source_height) // 2
        
        # Draw source container
        self._draw_container(draw, start_x, container_y, source_width, source_height,
                           source_water, show_measurements=False, label="A")
        
        # Draw target container
        target_x = start_x + source_width + gap
        self._draw_container(draw, target_x, container_y, target_width, target_height,
                           target_water, show_measurements=False, label="B")
        
        # Draw pouring water stream (if in progress)
        if 0 < progress < 1:
            stream_start_x = start_x + source_width + 10
            stream_end_x = target_x - 5
            stream_y_start = container_y + source_height - source_water
            stream_y_end = container_y + target_height - target_water
            
            water_color = self.config.water_color[:3]
            # Draw curved stream
            for t in range(10):
                t_ratio = t / 9
                x = stream_start_x + (stream_end_x - stream_start_x) * t_ratio
                y = stream_y_start + (stream_y_end - stream_y_start) * t_ratio + 20 * math.sin(t_ratio * math.pi)
                draw.ellipse([x - 4, y - 4, x + 4, y + 4], fill=water_color)
        
        return img
