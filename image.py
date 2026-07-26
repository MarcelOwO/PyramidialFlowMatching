#!/usr/bin/env uv run

import torch
from diffusers import WanPipeline
from diffusers.utils import export_to_video

pipe = WanPipeline.from_pretrained(
    "Wan-AI/Wan2.1-T2V-1.3B-Diffusers", torch_dtype=torch.bfloat16
).to(
    "mps"
)

prompt = "A cozy cabin in the snowy mountains, hyper-realistic, cinematic lighting, slow camera pan."j
video_frames = pipe(
    prompt=prompt, num_frames=81, guidance_scale=5.0
).frames[0]

export_to_video(video_frames, "generated_video.mp4", fps=16)

print("Video saved successfully as generated_video.mp4")
