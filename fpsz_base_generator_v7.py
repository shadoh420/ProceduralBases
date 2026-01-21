"""
FPSZ Procedural Base Generator v7 - Variable Layouts
=====================================================
Actually uses seed and settings to generate different bases!
- Different corridor configurations based on seed
- Variable room placement
- Randomized detail placement
- Style affects overall structure

Run in Blender 4.x with Alt+P to register the UI panel.
"""

import bpy
import bmesh
from mathutils import Vector
import math
import random
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum

bl_info = {
    "name": "FPSZ Base Generator",
    "author": "Procedural",
    "version": (7, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > FPSZ Generator",
    "description": "Generate varied Tribes-style FPS bases",
    "category": "Object",
}


# =============================================================================
# CONFIGURATION
# =============================================================================

class BaseStyle(Enum):
    PYRAMID = "pyramid"
    STEPPED = "stepped"
    TOWER = "tower"


@dataclass
class Config:
    base_width: float = 80.0
    base_depth: float = 80.0
    base_height: float = 60.0
    wall_taper: float = 0.2
    exterior_wall_thickness: float = 4.0
    interior_wall_thickness: float = 1.5
    floor_thickness: float = 1.5
    num_levels: int = 4
    level_height: float = 14.0
    trim_height: float = 0.8
    trim_inset: float = 0.3
    column_width: float = 3.0
    platform_edge_height: float = 0.6
    doorway_width: float = 8.0
    doorway_height: float = 10.0
    ramp_width: float = 8.0
    atrium_width: float = 28.0
    atrium_depth: float = 28.0
    style: BaseStyle = BaseStyle.PYRAMID
    seed: int = 42


# =============================================================================
# MESH BUILDER
# =============================================================================

class MeshBuilder:
    def __init__(self, name: str):
        self.name = name
        self.bm = bmesh.new()
    
    def add_box(self, x, y, z, w, d, h):
        hw, hd = w / 2, d / 2
        vb = [self.bm.verts.new((x-hw, y-hd, z)), self.bm.verts.new((x+hw, y-hd, z)),
              self.bm.verts.new((x+hw, y+hd, z)), self.bm.verts.new((x-hw, y+hd, z))]
        vt = [self.bm.verts.new((x-hw, y-hd, z+h)), self.bm.verts.new((x+hw, y-hd, z+h)),
              self.bm.verts.new((x+hw, y+hd, z+h)), self.bm.verts.new((x-hw, y+hd, z+h))]
        self.bm.faces.new(vb[::-1])
        self.bm.faces.new(vt)
        for i in range(4):
            self.bm.faces.new([vb[i], vb[(i+1)%4], vt[(i+1)%4], vt[i]])
    
    def add_platform(self, x, y, z, w, d, thick=1.5, edge_h=0.5, edge_w=0.4):
        self.add_box(x, y, z - thick, w, d, thick)
        hw, hd = w/2, d/2
        self.add_box(x, y+hd-edge_w/2, z, w, edge_w, edge_h)
        self.add_box(x, y-hd+edge_w/2, z, w, edge_w, edge_h)
        self.add_box(x+hw-edge_w/2, y, z, edge_w, d-edge_w*2, edge_h)
        self.add_box(x-hw+edge_w/2, y, z, edge_w, d-edge_w*2, edge_h)
    
    def add_column(self, x, y, z_base, z_top, width=3.0):
        base_h = 1.5
        cap_h = 1.0
        shaft_h = z_top - z_base - base_h - cap_h
        self.add_box(x, y, z_base, width*1.4, width*1.4, base_h)
        self.add_box(x, y, z_base + base_h, width, width, shaft_h)
        self.add_box(x, y, z_top - cap_h, width*1.3, width*1.3, cap_h)
    
    def add_wall_with_trim(self, x1, y1, x2, y2, z, height, thick=1.5, num_bands=3):
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length < 0.01:
            return
        trim_h = 0.8
        spacing = height / (num_bands + 1)
        
        for i in range(num_bands + 1):
            sec_z = z + i * spacing
            sec_h = spacing - trim_h if i < num_bands else spacing
            if sec_h > 0:
                self._wall_section(x1, y1, x2, y2, sec_z, sec_h, thick)
        
        for i in range(1, num_bands + 1):
            trim_z = z + i * spacing - trim_h
            self._wall_section(x1, y1, x2, y2, trim_z, trim_h, thick + 0.6)
    
    def _wall_section(self, x1, y1, x2, y2, z, h, thick):
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length < 0.01 or h < 0.01:
            return
        px, py = -dy/length * thick/2, dx/length * thick/2
        vb = [self.bm.verts.new((x1-px, y1-py, z)), self.bm.verts.new((x1+px, y1+py, z)),
              self.bm.verts.new((x2+px, y2+py, z)), self.bm.verts.new((x2-px, y2-py, z))]
        vt = [self.bm.verts.new((x1-px, y1-py, z+h)), self.bm.verts.new((x1+px, y1+py, z+h)),
              self.bm.verts.new((x2+px, y2+py, z+h)), self.bm.verts.new((x2-px, y2-py, z+h))]
        self.bm.faces.new(vb[::-1])
        self.bm.faces.new(vt)
        self.bm.faces.new([vb[0], vb[3], vt[3], vt[0]])
        self.bm.faces.new([vb[1], vt[1], vt[2], vb[2]])
        self.bm.faces.new([vb[0], vt[0], vt[1], vb[1]])
        self.bm.faces.new([vb[2], vt[2], vt[3], vb[3]])
    
    def add_ramp(self, x1, y1, z1, x2, y2, z2, width, edge_h=0.5):
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length < 0.01:
            return
        px, py = -dy/length * width/2, dx/length * width/2
        thick = 0.5
        
        vt = [self.bm.verts.new((x1-px, y1-py, z1)), self.bm.verts.new((x1+px, y1+py, z1)),
              self.bm.verts.new((x2+px, y2+py, z2)), self.bm.verts.new((x2-px, y2-py, z2))]
        self.bm.faces.new(vt)
        vb = [self.bm.verts.new((x1-px, y1-py, z1-thick)), self.bm.verts.new((x1+px, y1+py, z1-thick)),
              self.bm.verts.new((x2+px, y2+py, z2-thick)), self.bm.verts.new((x2-px, y2-py, z2-thick))]
        self.bm.faces.new(vb[::-1])
        self.bm.faces.new([vt[0], vt[3], vb[3], vb[0]])
        self.bm.faces.new([vt[1], vb[1], vb[2], vt[2]])
        self.bm.faces.new([vt[0], vb[0], vb[1], vt[1]])
        self.bm.faces.new([vt[2], vb[2], vb[3], vt[3]])
        
        # Edge rails
        ew = 0.4
        epx, epy = -dy/length * ew/2, dx/length * ew/2
        for side in [-1, 1]:
            rx1 = x1 + side*(px - epx)
            ry1 = y1 + side*(py - epy)
            rx2 = x2 + side*(px - epx)
            ry2 = y2 + side*(py - epy)
            self.add_box((rx1+rx2)/2, (ry1+ry2)/2, (z1+z2)/2, ew, length, edge_h)
    
    def add_balcony(self, x, y, z, w, d, open_side='south'):
        self.add_platform(x, y, z, w, d, 1.5, 0.4, 0.3)
        rail_h = 3.0
        rt = 0.4
        
        if open_side == 'south':
            ry = y - d/2 + rt/2
            for i in range(5):
                px = x - w/2 + i * w/4
                self.add_box(px, ry, z, rt, rt, rail_h)
            self.add_box(x, ry, z + rail_h - rt/2, w, rt, rt)
        elif open_side == 'north':
            ry = y + d/2 - rt/2
            for i in range(5):
                px = x - w/2 + i * w/4
                self.add_box(px, ry, z, rt, rt, rail_h)
            self.add_box(x, ry, z + rail_h - rt/2, w, rt, rt)
        elif open_side == 'east':
            rx = x + w/2 - rt/2
            for i in range(5):
                py = y - d/2 + i * d/4
                self.add_box(rx, py, z, rt, rt, rail_h)
            self.add_box(rx, y, z + rail_h - rt/2, rt, d, rt)
        elif open_side == 'west':
            rx = x - w/2 + rt/2
            for i in range(5):
                py = y - d/2 + i * d/4
                self.add_box(rx, py, z, rt, rt, rail_h)
            self.add_box(rx, y, z + rail_h - rt/2, rt, d, rt)
    
    def add_tapered_shell(self, base_w, base_d, top_w, top_d, height, thick, z_base=0):
        bw, bd = base_w/2, base_d/2
        tw, td = top_w/2, top_d/2
        z0, z1 = z_base, z_base + height
        
        vob = [self.bm.verts.new((-bw,-bd,z0)), self.bm.verts.new((bw,-bd,z0)),
               self.bm.verts.new((bw,bd,z0)), self.bm.verts.new((-bw,bd,z0))]
        vot = [self.bm.verts.new((-tw,-td,z1)), self.bm.verts.new((tw,-td,z1)),
               self.bm.verts.new((tw,td,z1)), self.bm.verts.new((-tw,td,z1))]
        self.bm.faces.new(vob[::-1])
        self.bm.faces.new(vot)
        for i in range(4):
            self.bm.faces.new([vob[i], vob[(i+1)%4], vot[(i+1)%4], vot[i]])
        
        ibw, ibd = bw - thick, bd - thick
        itw, itd = tw - thick, td - thick
        vib = [self.bm.verts.new((-ibw,-ibd,z0)), self.bm.verts.new((ibw,-ibd,z0)),
               self.bm.verts.new((ibw,ibd,z0)), self.bm.verts.new((-ibw,ibd,z0))]
        vit = [self.bm.verts.new((-itw,-itd,z1)), self.bm.verts.new((itw,-itd,z1)),
               self.bm.verts.new((itw,itd,z1)), self.bm.verts.new((-itw,itd,z1))]
        self.bm.faces.new(vib)
        self.bm.faces.new(vit[::-1])
        for i in range(4):
            self.bm.faces.new([vib[(i+1)%4], vib[i], vit[i], vit[(i+1)%4]])
    
    def finalize(self, collection):
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=0.01)
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        mesh = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(mesh)
        self.bm.free()
        obj = bpy.data.objects.new(self.name, mesh)
        collection.objects.link(obj)
        return obj


# =============================================================================
# PROCEDURAL LAYOUT GENERATOR
# =============================================================================

class LayoutGenerator:
    """Generates varied layouts based on seed."""
    
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.rng = random.Random(cfg.seed)
        
        # Generate layout choices based on seed
        self.corridor_config = self.rng.choice(['cross', 'T_north', 'T_south', 'L_ne', 'L_sw', 'H'])
        self.has_center_platform = self.rng.choice([True, True, False])
        self.column_pattern = self.rng.choice(['corners', 'sides', 'ring', 'minimal'])
        self.ramp_style = self.rng.choice(['spiral', 'opposing', 'central', 'corner'])
        self.balcony_config = self.rng.choice(['full_ring', 'opposing', 'single', 'corners'])
        self.num_side_rooms = self.rng.randint(0, 4)
        self.entrance_config = self.rng.choice(['north_south', 'all_sides', 'single', 'diagonal'])
        
        print(f"   Layout: corridors={self.corridor_config}, columns={self.column_pattern}")
        print(f"   Ramps: {self.ramp_style}, balconies={self.balcony_config}")
    
    def get_corridor_endpoints(self):
        """Return which directions have corridors."""
        cfg = self.cfg
        hall_w, hall_d = cfg.atrium_width / 2, cfg.atrium_depth / 2
        ext_w = cfg.base_width / 2 - cfg.exterior_wall_thickness - 2
        ext_d = cfg.base_depth / 2 - cfg.exterior_wall_thickness - 2
        
        corridors = []
        
        if self.corridor_config == 'cross':
            corridors = ['north', 'south', 'east', 'west']
        elif self.corridor_config == 'T_north':
            corridors = ['north', 'east', 'west']
        elif self.corridor_config == 'T_south':
            corridors = ['south', 'east', 'west']
        elif self.corridor_config == 'L_ne':
            corridors = ['north', 'east']
        elif self.corridor_config == 'L_sw':
            corridors = ['south', 'west']
        elif self.corridor_config == 'H':
            corridors = ['north', 'south']
        
        return corridors
    
    def get_column_positions(self, z, avail_w, avail_d):
        """Return column positions for this level."""
        positions = []
        offset_w = avail_w / 2 - self.cfg.column_width - 2
        offset_d = avail_d / 2 - self.cfg.column_width - 2
        mid_w = avail_w / 4
        mid_d = avail_d / 4
        
        if self.column_pattern == 'corners':
            positions = [(offset_w, offset_d), (offset_w, -offset_d),
                        (-offset_w, offset_d), (-offset_w, -offset_d)]
        elif self.column_pattern == 'sides':
            positions = [(offset_w, 0), (-offset_w, 0), (0, offset_d), (0, -offset_d)]
        elif self.column_pattern == 'ring':
            positions = [(offset_w, offset_d), (offset_w, -offset_d),
                        (-offset_w, offset_d), (-offset_w, -offset_d),
                        (offset_w, 0), (-offset_w, 0)]
        elif self.column_pattern == 'minimal':
            positions = [(offset_w, offset_d), (-offset_w, -offset_d)]
        
        return positions
    
    def get_ramp_positions(self, level, num_levels):
        """Return ramp start/end for this level."""
        cfg = self.cfg
        ramp_rise = cfg.level_height
        ramp_run = ramp_rise / math.tan(math.radians(28))
        z_start = (level + 1) * cfg.level_height + cfg.floor_thickness
        z_end = z_start + ramp_rise
        
        offset = cfg.atrium_width / 2 - 6
        
        if self.ramp_style == 'spiral':
            # Rotate around the atrium
            dirs = [(offset, -ramp_run/2, offset, ramp_run/2),      # East going north
                    (-ramp_run/2, offset, ramp_run/2, offset),      # North going east  
                    (-offset, ramp_run/2, -offset, -ramp_run/2),    # West going south
                    (ramp_run/2, -offset, -ramp_run/2, -offset)]    # South going west
            idx = level % 4
            x1, y1, x2, y2 = dirs[idx]
            return (x1, y1, z_start, x2, y2, z_end)
        
        elif self.ramp_style == 'opposing':
            # Alternate east/west
            if level % 2 == 0:
                return (offset, -ramp_run/2, z_start, offset, ramp_run/2, z_end)
            else:
                return (-offset, ramp_run/2, z_start, -offset, -ramp_run/2, z_end)
        
        elif self.ramp_style == 'central':
            # All ramps in center, alternating direction
            if level % 2 == 0:
                return (0, -ramp_run/2, z_start, 0, ramp_run/2, z_end)
            else:
                return (0, ramp_run/2, z_start, 0, -ramp_run/2, z_end)
        
        elif self.ramp_style == 'corner':
            # Ramps in corners
            corners = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
            cx, cy = corners[level % 4]
            corner_offset = offset * 0.7
            return (cx * corner_offset, cy * corner_offset - cy*ramp_run/2, z_start,
                    cx * corner_offset, cy * corner_offset + cy*ramp_run/2, z_end)
        
        return None
    
    def get_balcony_config(self, level, avail_w, avail_d):
        """Return balcony positions for this level."""
        balconies = []
        platform_w = (avail_w - self.cfg.atrium_width) / 2 - 2
        platform_d = (avail_d - self.cfg.atrium_depth) / 2 - 2
        
        if platform_w < 4 or platform_d < 4:
            return balconies
        
        py = avail_d / 2 - platform_d / 2
        px = avail_w / 2 - platform_w / 2
        
        if self.balcony_config == 'full_ring':
            balconies = [
                (0, py, avail_w * 0.6, platform_d, 'south'),
                (0, -py, avail_w * 0.6, platform_d, 'north'),
                (px, 0, platform_w, self.cfg.atrium_depth * 0.5, 'west'),
                (-px, 0, platform_w, self.cfg.atrium_depth * 0.5, 'east'),
            ]
        elif self.balcony_config == 'opposing':
            if level % 2 == 0:
                balconies = [
                    (0, py, avail_w * 0.6, platform_d, 'south'),
                    (0, -py, avail_w * 0.6, platform_d, 'north'),
                ]
            else:
                balconies = [
                    (px, 0, platform_w, self.cfg.atrium_depth * 0.5, 'west'),
                    (-px, 0, platform_w, self.cfg.atrium_depth * 0.5, 'east'),
                ]
        elif self.balcony_config == 'single':
            sides = ['south', 'north', 'west', 'east']
            side = sides[level % 4]
            if side == 'south':
                balconies = [(0, py, avail_w * 0.6, platform_d, 'south')]
            elif side == 'north':
                balconies = [(0, -py, avail_w * 0.6, platform_d, 'north')]
            elif side == 'west':
                balconies = [(px, 0, platform_w, self.cfg.atrium_depth * 0.5, 'west')]
            else:
                balconies = [(-px, 0, platform_w, self.cfg.atrium_depth * 0.5, 'east')]
        elif self.balcony_config == 'corners':
            corner_size = min(platform_w, platform_d) * 0.8
            balconies = [
                (px * 0.8, py * 0.8, corner_size, corner_size, 'south'),
                (-px * 0.8, py * 0.8, corner_size, corner_size, 'south'),
                (px * 0.8, -py * 0.8, corner_size, corner_size, 'north'),
                (-px * 0.8, -py * 0.8, corner_size, corner_size, 'north'),
            ]
        
        return balconies
    
    def get_entrance_positions(self):
        """Return entrance ramp positions."""
        cfg = self.cfg
        entrance_z = cfg.level_height * 0.35
        taper = cfg.base_height * cfg.wall_taper * (entrance_z / cfg.base_height)
        wall_d = cfg.base_depth / 2 - taper
        wall_w = cfg.base_width / 2 - taper
        ramp_len = entrance_z / math.tan(math.radians(20))
        
        entrances = []
        
        if self.entrance_config == 'north_south':
            entrances = [
                (0, -(wall_d + ramp_len), 0, 0, -wall_d + 5, entrance_z, 'south'),
                (0, wall_d + ramp_len, 0, 0, wall_d - 5, entrance_z, 'north'),
            ]
        elif self.entrance_config == 'all_sides':
            entrances = [
                (0, -(wall_d + ramp_len), 0, 0, -wall_d + 5, entrance_z, 'south'),
                (0, wall_d + ramp_len, 0, 0, wall_d - 5, entrance_z, 'north'),
                (-(wall_w + ramp_len), 0, 0, -wall_w + 5, 0, entrance_z, 'west'),
                (wall_w + ramp_len, 0, 0, wall_w - 5, 0, entrance_z, 'east'),
            ]
        elif self.entrance_config == 'single':
            entrances = [
                (0, -(wall_d + ramp_len), 0, 0, -wall_d + 5, entrance_z, 'south'),
            ]
        elif self.entrance_config == 'diagonal':
            entrances = [
                (0, -(wall_d + ramp_len), 0, 0, -wall_d + 5, entrance_z, 'south'),
                (wall_w + ramp_len, 0, 0, wall_w - 5, 0, entrance_z, 'east'),
            ]
        
        return entrances


# =============================================================================
# BASE GENERATOR
# =============================================================================

class TribesBaseGenerator:
    def __init__(self, cfg: Config = None):
        self.cfg = cfg or Config()
        self.collection = None
        self.layout = None
    
    def generate(self):
        print("\n" + "="*60)
        print("FPSZ BASE GENERATOR v7 - Variable Layouts")
        print(f"Style: {self.cfg.style.value}, Seed: {self.cfg.seed}")
        print("="*60)
        
        self._setup_collection()
        self.layout = LayoutGenerator(self.cfg)
        
        print("\n1. Building exterior...")
        self._build_exterior()
        
        print("2. Building main hall...")
        self._build_main_hall()
        
        print("3. Building corridors...")
        self._build_corridors()
        
        print("4. Building upper levels...")
        self._build_upper_levels()
        
        print("5. Building ramps...")
        self._build_ramps()
        
        print("6. Building entrances...")
        self._build_entrances()
        
        print("\n" + "="*60)
        print("Generation complete!")
        print("="*60 + "\n")
    
    def _setup_collection(self):
        col_name = "FPSZ_Generated_Base"
        if col_name in bpy.data.collections:
            col = bpy.data.collections[col_name]
            for obj in list(col.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(col)
        col = bpy.data.collections.new(col_name)
        bpy.context.scene.collection.children.link(col)
        self.collection = col
    
    def _build_exterior(self):
        cfg = self.cfg
        mb = MeshBuilder("Base_Exterior")
        
        taper = cfg.base_height * cfg.wall_taper
        top_w = cfg.base_width - taper * 2
        top_d = cfg.base_depth - taper * 2
        
        if cfg.style == BaseStyle.PYRAMID:
            mb.add_tapered_shell(cfg.base_width, cfg.base_depth, top_w, top_d,
                                cfg.base_height, cfg.exterior_wall_thickness)
        
        elif cfg.style == BaseStyle.STEPPED:
            tiers = 4
            tier_h = cfg.base_height / tiers
            for t in range(tiers):
                scale = 1.0 - t * 0.18
                tw = cfg.base_width * scale
                td = cfg.base_depth * scale
                top_scale = scale - 0.04
                mb.add_tapered_shell(tw, td, cfg.base_width * top_scale, cfg.base_depth * top_scale,
                                    tier_h, cfg.exterior_wall_thickness, t * tier_h)
        
        elif cfg.style == BaseStyle.TOWER:
            base_h = cfg.base_height * 0.35
            mb.add_tapered_shell(cfg.base_width * 1.2, cfg.base_depth * 1.2,
                                cfg.base_width * 1.1, cfg.base_depth * 1.1,
                                base_h, cfg.exterior_wall_thickness)
            mb.add_tapered_shell(cfg.base_width * 0.6, cfg.base_depth * 0.6,
                                cfg.base_width * 0.5, cfg.base_depth * 0.5,
                                cfg.base_height * 0.65, cfg.exterior_wall_thickness, base_h)
        
        obj = mb.finalize(self.collection)
        self._apply_material(obj, "Exterior", (0.38, 0.40, 0.42))
    
    def _build_main_hall(self):
        cfg = self.cfg
        mb = MeshBuilder("Main_Hall")
        z = cfg.floor_thickness
        
        # Main floor
        mb.add_platform(0, 0, z, cfg.atrium_width, cfg.atrium_depth, cfg.floor_thickness)
        
        # Center platform (if enabled)
        if self.layout.has_center_platform:
            center_size = self.layout.rng.uniform(8, 14)
            center_h = self.layout.rng.uniform(1.5, 3.0)
            mb.add_platform(0, 0, z + center_h, center_size, center_size, 1.0, 0.5, 0.3)
            
            # Steps
            step_w = center_size + 2
            for i in range(3):
                step_y = -(center_size/2 + 1 + i * 2)
                mb.add_box(0, step_y, z + i * center_h/3, step_w, 2, center_h/3)
                mb.add_box(0, -step_y, z + i * center_h/3, step_w, 2, center_h/3)
        
        # Columns based on pattern
        col_positions = self.layout.get_column_positions(z, cfg.atrium_width, cfg.atrium_depth)
        col_height = cfg.level_height * 2
        
        for cx, cy in col_positions:
            mb.add_column(cx, cy, z, z + col_height, cfg.column_width)
        
        obj = mb.finalize(self.collection)
        self._apply_material(obj, "Floor", (0.32, 0.35, 0.38))
    
    def _build_corridors(self):
        cfg = self.cfg
        mb = MeshBuilder("Corridors")
        z = cfg.floor_thickness
        
        corridors = self.layout.get_corridor_endpoints()
        corridor_w = 10.0
        
        for direction in corridors:
            if direction == 'north':
                length = (cfg.base_depth - cfg.atrium_depth) / 2 - cfg.exterior_wall_thickness
                corr_y = cfg.atrium_depth / 2 + length / 2
                mb.add_platform(0, corr_y, z, corridor_w, length, cfg.floor_thickness, 0.4, 0.3)
                
                wall_x = corridor_w / 2
                wall_y1 = cfg.atrium_depth / 2
                wall_y2 = cfg.atrium_depth / 2 + length
                mb.add_wall_with_trim(-wall_x, wall_y1, -wall_x, wall_y2, z, cfg.level_height)
                mb.add_wall_with_trim(wall_x, wall_y1, wall_x, wall_y2, z, cfg.level_height)
            
            elif direction == 'south':
                length = (cfg.base_depth - cfg.atrium_depth) / 2 - cfg.exterior_wall_thickness
                corr_y = -(cfg.atrium_depth / 2 + length / 2)
                mb.add_platform(0, corr_y, z, corridor_w, length, cfg.floor_thickness, 0.4, 0.3)
                
                wall_x = corridor_w / 2
                wall_y1 = -cfg.atrium_depth / 2
                wall_y2 = -(cfg.atrium_depth / 2 + length)
                mb.add_wall_with_trim(-wall_x, wall_y1, -wall_x, wall_y2, z, cfg.level_height)
                mb.add_wall_with_trim(wall_x, wall_y1, wall_x, wall_y2, z, cfg.level_height)
            
            elif direction == 'east':
                length = (cfg.base_width - cfg.atrium_width) / 2 - cfg.exterior_wall_thickness
                corr_x = cfg.atrium_width / 2 + length / 2
                mb.add_platform(corr_x, 0, z, length, corridor_w, cfg.floor_thickness, 0.4, 0.3)
                
                wall_y = corridor_w / 2
                wall_x1 = cfg.atrium_width / 2
                wall_x2 = cfg.atrium_width / 2 + length
                mb.add_wall_with_trim(wall_x1, -wall_y, wall_x2, -wall_y, z, cfg.level_height)
                mb.add_wall_with_trim(wall_x1, wall_y, wall_x2, wall_y, z, cfg.level_height)
            
            elif direction == 'west':
                length = (cfg.base_width - cfg.atrium_width) / 2 - cfg.exterior_wall_thickness
                corr_x = -(cfg.atrium_width / 2 + length / 2)
                mb.add_platform(corr_x, 0, z, length, corridor_w, cfg.floor_thickness, 0.4, 0.3)
                
                wall_y = corridor_w / 2
                wall_x1 = -cfg.atrium_width / 2
                wall_x2 = -(cfg.atrium_width / 2 + length)
                mb.add_wall_with_trim(wall_x1, -wall_y, wall_x2, -wall_y, z, cfg.level_height)
                mb.add_wall_with_trim(wall_x1, wall_y, wall_x2, wall_y, z, cfg.level_height)
        
        obj = mb.finalize(self.collection)
        self._apply_material(obj, "Corridor", (0.30, 0.32, 0.35))
    
    def _build_upper_levels(self):
        cfg = self.cfg
        mb = MeshBuilder("Upper_Levels")
        
        for level in range(1, cfg.num_levels):
            z = level * cfg.level_height + cfg.floor_thickness
            
            height_ratio = z / cfg.base_height
            taper = cfg.base_height * cfg.wall_taper * height_ratio
            avail_w = cfg.base_width - cfg.exterior_wall_thickness * 2 - taper * 2
            avail_d = cfg.base_depth - cfg.exterior_wall_thickness * 2 - taper * 2
            
            # Balconies based on config
            balconies = self.layout.get_balcony_config(level, avail_w, avail_d)
            for bx, by, bw, bd, open_side in balconies:
                mb.add_balcony(bx, by, z, bw, bd, open_side)
            
            # Columns on upper levels
            if level < cfg.num_levels - 1:
                col_positions = self.layout.get_column_positions(z, avail_w, avail_d)
                for cx, cy in col_positions:
                    # Scale down columns on upper levels
                    scale = 1.0 - level * 0.15
                    mb.add_column(cx * scale, cy * scale, z, z + cfg.level_height, 
                                 cfg.column_width * scale)
        
        obj = mb.finalize(self.collection)
        self._apply_material(obj, "Upper", (0.33, 0.36, 0.39))
    
    def _build_ramps(self):
        cfg = self.cfg
        mb = MeshBuilder("Ramps")
        
        for level in range(cfg.num_levels - 1):
            ramp_data = self.layout.get_ramp_positions(level, cfg.num_levels)
            if ramp_data:
                x1, y1, z1, x2, y2, z2 = ramp_data
                mb.add_ramp(x1, y1, z1, x2, y2, z2, cfg.ramp_width)
        
        obj = mb.finalize(self.collection)
        self._apply_material(obj, "Ramp", (0.40, 0.38, 0.32))
    
    def _build_entrances(self):
        cfg = self.cfg
        mb = MeshBuilder("Entrances")
        
        entrances = self.layout.get_entrance_positions()
        
        for x1, y1, z1, x2, y2, z2, direction in entrances:
            mb.add_ramp(x1, y1, z1, x2, y2, z2, cfg.ramp_width + 2)
            
            # Landing platform
            if direction == 'south':
                mb.add_platform(x2, y2 + 3, z2, cfg.ramp_width + 6, 8, 1.0, 0.5, 0.3)
            elif direction == 'north':
                mb.add_platform(x2, y2 - 3, z2, cfg.ramp_width + 6, 8, 1.0, 0.5, 0.3)
            elif direction == 'east':
                mb.add_platform(x2 - 3, y2, z2, 8, cfg.ramp_width + 6, 1.0, 0.5, 0.3)
            elif direction == 'west':
                mb.add_platform(x2 + 3, y2, z2, 8, cfg.ramp_width + 6, 1.0, 0.5, 0.3)
        
        obj = mb.finalize(self.collection)
        self._apply_material(obj, "Entrance", (0.40, 0.38, 0.32))
    
    def _apply_material(self, obj, name, color):
        mat_name = f"FPSZ_{name}"
        mat = bpy.data.materials.get(mat_name)
        if not mat:
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes.get('Principled BSDF')
            if bsdf:
                bsdf.inputs['Base Color'].default_value = (*color, 1.0)
                bsdf.inputs['Roughness'].default_value = 0.75
        obj.data.materials.append(mat)


# =============================================================================
# PUBLIC API
# =============================================================================

def generate_base(style: str = "pyramid", seed: int = None, num_levels: int = 4, **kwargs):
    cfg = Config()
    
    style_map = {"pyramid": BaseStyle.PYRAMID, "stepped": BaseStyle.STEPPED, "tower": BaseStyle.TOWER}
    cfg.style = style_map.get(style.lower(), BaseStyle.PYRAMID)
    
    if seed is not None:
        cfg.seed = seed
    else:
        import time
        cfg.seed = int(time.time()) % 100000
    
    cfg.num_levels = max(2, min(6, num_levels))
    cfg.base_height = cfg.num_levels * cfg.level_height + 8
    
    for key, value in kwargs.items():
        if hasattr(cfg, key):
            setattr(cfg, key, value)
    
    generator = TribesBaseGenerator(cfg)
    generator.generate()


# =============================================================================
# BLENDER UI
# =============================================================================

class FPSZ_OT_GenerateBase(bpy.types.Operator):
    bl_idname = "fpsz.generate_base"
    bl_label = "Generate Base"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        props = context.scene.fpsz_props
        seed = int(random.random() * 100000) if props.use_random_seed else props.seed
        generate_base(style=props.style, seed=seed, num_levels=props.num_levels,
                     base_width=props.base_width, base_depth=props.base_depth,
                     wall_taper=props.wall_taper)
        props.seed = seed
        self.report({'INFO'}, f"Generated {props.style} base, seed {seed}")
        return {'FINISHED'}


class FPSZ_OT_RandomGenerate(bpy.types.Operator):
    bl_idname = "fpsz.random_generate"
    bl_label = "Random"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        props = context.scene.fpsz_props
        seed = int(random.random() * 100000)
        style = random.choice(['pyramid', 'stepped', 'tower'])
        levels = random.randint(3, 5)
        generate_base(style=style, seed=seed, num_levels=levels)
        props.style = style
        props.seed = seed
        props.num_levels = levels
        self.report({'INFO'}, f"Random: {style}, {levels} levels, seed {seed}")
        return {'FINISHED'}


class FPSZ_OT_ClearGenerated(bpy.types.Operator):
    bl_idname = "fpsz.clear_generated"
    bl_label = "Clear"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        col_name = "FPSZ_Generated_Base"
        if col_name in bpy.data.collections:
            col = bpy.data.collections[col_name]
            for obj in list(col.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(col)
        return {'FINISHED'}


class FPSZ_Properties(bpy.types.PropertyGroup):
    style: bpy.props.EnumProperty(name="Style", items=[
        ('pyramid', 'Pyramid', ''), ('stepped', 'Stepped', ''), ('tower', 'Tower', '')
    ], default='pyramid')
    seed: bpy.props.IntProperty(name="Seed", default=12345, min=0, max=99999)
    use_random_seed: bpy.props.BoolProperty(name="Random Seed", default=True)
    num_levels: bpy.props.IntProperty(name="Levels", default=4, min=2, max=6)
    base_width: bpy.props.FloatProperty(name="Width", default=80.0, min=50.0, max=120.0)
    base_depth: bpy.props.FloatProperty(name="Depth", default=80.0, min=50.0, max=120.0)
    wall_taper: bpy.props.FloatProperty(name="Wall Taper", default=0.2, min=0.0, max=0.4)


class FPSZ_PT_MainPanel(bpy.types.Panel):
    bl_label = "FPSZ Generator v7"
    bl_idname = "FPSZ_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FPSZ Generator'
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.fpsz_props
        
        box = layout.box()
        box.prop(props, "style")
        
        box = layout.box()
        row = box.row(align=True)
        row.prop(props, "seed")
        row.prop(props, "use_random_seed", text="", icon='FILE_REFRESH')
        box.prop(props, "num_levels")
        box.prop(props, "base_width")
        box.prop(props, "base_depth")
        box.prop(props, "wall_taper", slider=True)
        
        layout.separator()
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator("fpsz.generate_base", text="Generate", icon='PLAY')
        row.operator("fpsz.random_generate", text="Random", icon='QUESTION')
        layout.operator("fpsz.clear_generated", text="Clear", icon='TRASH')


classes = (FPSZ_Properties, FPSZ_OT_GenerateBase, FPSZ_OT_RandomGenerate, 
           FPSZ_OT_ClearGenerated, FPSZ_PT_MainPanel)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.fpsz_props = bpy.props.PointerProperty(type=FPSZ_Properties)
    print("FPSZ Generator v7: Registered - different seeds now create different layouts!")

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.fpsz_props

if __name__ == "__main__":
    register()
