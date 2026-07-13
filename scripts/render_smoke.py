"""Render one inexpensive Cycles frame to verify volume/material compatibility."""

import os

import bpy

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 4
scene.cycles.use_denoising = False
scene.render.resolution_x = 320
scene.render.resolution_y = 240
scene.render.resolution_percentage = 100
scene.render.filepath = os.environ.get("BDP_SMOKE_OUTPUT", "/tmp/bdp_cycles_smoke.png")
bpy.ops.render.render(write_still=True)
print(f"Cycles smoke render saved to {scene.render.filepath}")
