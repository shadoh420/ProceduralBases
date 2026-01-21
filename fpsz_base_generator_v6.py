"""
FPSZ Procedural Base Generator v6 - Architectural Detail
=========================================================
Focuses on making interiors feel cohesive like real Tribes bases:
- Horizontal trim bands on walls
- Recessed wall panels
- Platform edges with trim
- Substantial columns with bases
- Ceiling details (skylights, angled panels)
- Symmetrical layouts
- Long corridors with repeated elements

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
    "version": (6, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > FPSZ Generator",
    "description": "Generate Tribes-style FPS bases with detailed interiors",
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
    """Base generation configuration with architectural detail settings."""
    
    # Overall size
    base_width: float = 80.0
    base_depth: float = 80.0
    base_height: float = 60.0
    
    # Taper
    wall_taper: float = 0.2
    
    # Structure
    exterior_wall_thickness: float = 4.0
    interior_wall_thickness: float = 1.5
    floor_thickness: float = 1.5
    
    # Levels
    num_levels: int = 4
    level_height: float = 14.0
    
    # Architectural details
    trim_height: float = 0.8           # Height of horizontal trim bands
    trim_inset: float = 0.3            # How much trim sticks out
    panel_depth: float = 0.5           # Depth of wall panel recesses
    
    # Columns
    column_width: float = 3.0
    column_base_height: float = 1.5
    column_cap_height: float = 1.0
    
    # Platform edges
    platform_edge_height: float = 0.6
    platform_edge_width: float = 0.4
    
    # Doorways
    doorway_width: float = 8.0
    doorway_height: float = 10.0
    
    # Ramps
    ramp_width: float = 8.0
    ramp_edge_height: float = 0.5
    
    # Skylights
    skylight_size: float = 4.0
    skylight_depth: float = 1.0
    
    # Central atrium
    atrium_width: float = 28.0
    atrium_depth: float = 28.0
    
    # Style
    style: BaseStyle = BaseStyle.PYRAMID
    
    # Seed
    seed: int = 42


# =============================================================================
# MESH BUILDER WITH ARCHITECTURAL DETAILS
# =============================================================================

class DetailedMeshBuilder:
    """Builds geometry with architectural detailing."""
    
    def __init__(self, name: str):
        self.name = name
        self.bm = bmesh.new()
    
    # =========================================================================
    # BASIC PRIMITIVES
    # =========================================================================
    
    def add_box(self, x: float, y: float, z: float, 
                w: float, d: float, h: float):
        """Add a simple box."""
        hw, hd = w / 2, d / 2
        
        verts_bot = [
            self.bm.verts.new((x - hw, y - hd, z)),
            self.bm.verts.new((x + hw, y - hd, z)),
            self.bm.verts.new((x + hw, y + hd, z)),
            self.bm.verts.new((x - hw, y + hd, z)),
        ]
        
        verts_top = [
            self.bm.verts.new((x - hw, y - hd, z + h)),
            self.bm.verts.new((x + hw, y - hd, z + h)),
            self.bm.verts.new((x + hw, y + hd, z + h)),
            self.bm.verts.new((x - hw, y + hd, z + h)),
        ]
        
        # Faces
        self.bm.faces.new(verts_bot[::-1])  # Bottom
        self.bm.faces.new(verts_top)         # Top
        for i in range(4):
            ni = (i + 1) % 4
            self.bm.faces.new([verts_bot[i], verts_bot[ni], verts_top[ni], verts_top[i]])
    
    def add_floor_slab(self, x: float, y: float, z: float,
                       w: float, d: float, thickness: float):
        """Add a floor slab."""
        self.add_box(x, y, z - thickness, w, d, thickness)
    
    # =========================================================================
    # DETAILED PLATFORM WITH EDGES
    # =========================================================================
    
    def add_detailed_platform(self, x: float, y: float, z: float,
                              w: float, d: float, 
                              floor_thick: float = 1.5,
                              edge_height: float = 0.6,
                              edge_width: float = 0.4):
        """
        Platform with raised edges like Tribes bases.
        Creates a floor slab with raised trim around the perimeter.
        """
        hw, hd = w / 2, d / 2
        
        # Main floor slab
        self.add_floor_slab(x, y, z, w, d, floor_thick)
        
        # Raised edge trim around perimeter
        # North edge
        self.add_box(x, y + hd - edge_width/2, z, w, edge_width, edge_height)
        # South edge
        self.add_box(x, y - hd + edge_width/2, z, w, edge_width, edge_height)
        # East edge
        self.add_box(x + hw - edge_width/2, y, z, edge_width, d - edge_width*2, edge_height)
        # West edge
        self.add_box(x - hw + edge_width/2, y, z, edge_width, d - edge_width*2, edge_height)
    
    # =========================================================================
    # DETAILED COLUMN WITH BASE AND CAP
    # =========================================================================
    
    def add_detailed_column(self, x: float, y: float, z_base: float, z_top: float,
                            width: float = 3.0,
                            base_height: float = 1.5,
                            cap_height: float = 1.0):
        """
        Column with wider base and cap like Tribes architecture.
        """
        shaft_height = z_top - z_base - base_height - cap_height
        
        # Base (wider)
        base_width = width * 1.4
        self.add_box(x, y, z_base, base_width, base_width, base_height)
        
        # Shaft
        self.add_box(x, y, z_base + base_height, width, width, shaft_height)
        
        # Cap (wider)
        cap_width = width * 1.3
        self.add_box(x, y, z_top - cap_height, cap_width, cap_width, cap_height)
    
    # =========================================================================
    # WALL WITH TRIM BANDS
    # =========================================================================
    
    def add_wall_with_trim(self, x1: float, y1: float, x2: float, y2: float,
                           z_base: float, height: float,
                           thickness: float = 1.5,
                           trim_height: float = 0.8,
                           trim_inset: float = 0.3,
                           num_trim_bands: int = 3):
        """
        Wall with horizontal trim bands at regular intervals.
        This creates the characteristic Tribes interior look.
        """
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length < 0.01:
            return
        
        # Normalize direction
        nx, ny = dx / length, dy / length
        # Perpendicular for thickness
        px, py = -ny * thickness / 2, nx * thickness / 2
        
        # Calculate trim positions
        trim_spacing = height / (num_trim_bands + 1)
        
        # Main wall sections between trim bands
        for i in range(num_trim_bands + 1):
            section_z = z_base + i * trim_spacing
            if i < num_trim_bands:
                section_h = trim_spacing - trim_height
            else:
                section_h = trim_spacing
            
            if section_h > 0:
                self._add_wall_section(x1, y1, x2, y2, section_z, section_h, thickness)
        
        # Trim bands (slightly protruding)
        trim_thick = thickness + trim_inset * 2
        for i in range(1, num_trim_bands + 1):
            trim_z = z_base + i * trim_spacing - trim_height
            self._add_wall_section(x1, y1, x2, y2, trim_z, trim_height, trim_thick)
    
    def _add_wall_section(self, x1: float, y1: float, x2: float, y2: float,
                          z: float, h: float, thickness: float):
        """Add a wall section between two points."""
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length < 0.01 or h < 0.01:
            return
        
        px, py = -dy / length * thickness / 2, dx / length * thickness / 2
        
        v_bot = [
            self.bm.verts.new((x1 - px, y1 - py, z)),
            self.bm.verts.new((x1 + px, y1 + py, z)),
            self.bm.verts.new((x2 + px, y2 + py, z)),
            self.bm.verts.new((x2 - px, y2 - py, z)),
        ]
        
        v_top = [
            self.bm.verts.new((x1 - px, y1 - py, z + h)),
            self.bm.verts.new((x1 + px, y1 + py, z + h)),
            self.bm.verts.new((x2 + px, y2 + py, z + h)),
            self.bm.verts.new((x2 - px, y2 - py, z + h)),
        ]
        
        self.bm.faces.new(v_bot[::-1])
        self.bm.faces.new(v_top)
        self.bm.faces.new([v_bot[0], v_bot[3], v_top[3], v_top[0]])  # Outer
        self.bm.faces.new([v_bot[1], v_top[1], v_top[2], v_bot[2]])  # Inner
        self.bm.faces.new([v_bot[0], v_top[0], v_top[1], v_bot[1]])  # Start
        self.bm.faces.new([v_bot[2], v_top[2], v_top[3], v_bot[3]])  # End
    
    # =========================================================================
    # RECESSED WALL PANEL
    # =========================================================================
    
    def add_wall_panel(self, x: float, y: float, z: float,
                       w: float, h: float,
                       facing: str = 'north',
                       recess_depth: float = 0.5,
                       frame_width: float = 0.5):
        """
        Recessed wall panel with frame - adds visual depth to walls.
        facing: 'north', 'south', 'east', 'west'
        """
        # Frame (outer rectangle)
        inner_w = w - frame_width * 2
        inner_h = h - frame_width * 2
        
        if facing in ['north', 'south']:
            sign = 1 if facing == 'north' else -1
            
            # Frame pieces
            # Top
            self.add_box(x, y + sign * recess_depth/2, z + h - frame_width/2,
                        w, recess_depth, frame_width)
            # Bottom
            self.add_box(x, y + sign * recess_depth/2, z + frame_width/2,
                        w, recess_depth, frame_width)
            # Left
            self.add_box(x - w/2 + frame_width/2, y + sign * recess_depth/2, z + h/2,
                        frame_width, recess_depth, inner_h)
            # Right
            self.add_box(x + w/2 - frame_width/2, y + sign * recess_depth/2, z + h/2,
                        frame_width, recess_depth, inner_h)
            
            # Recessed back panel
            self.add_box(x, y, z + h/2, inner_w, 0.2, inner_h)
        
        else:  # east/west
            sign = 1 if facing == 'east' else -1
            
            # Top
            self.add_box(x + sign * recess_depth/2, y, z + h - frame_width/2,
                        recess_depth, w, frame_width)
            # Bottom
            self.add_box(x + sign * recess_depth/2, y, z + frame_width/2,
                        recess_depth, w, frame_width)
            # Front
            self.add_box(x + sign * recess_depth/2, y - w/2 + frame_width/2, z + h/2,
                        recess_depth, frame_width, inner_h)
            # Back
            self.add_box(x + sign * recess_depth/2, y + w/2 - frame_width/2, z + h/2,
                        recess_depth, frame_width, inner_h)
            
            # Recessed panel
            self.add_box(x, y, z + h/2, 0.2, inner_w, inner_h)
    
    # =========================================================================
    # CEILING WITH SKYLIGHTS
    # =========================================================================
    
    def add_ceiling_with_skylights(self, x: float, y: float, z: float,
                                   w: float, d: float,
                                   thickness: float = 1.0,
                                   skylight_size: float = 4.0,
                                   skylight_depth: float = 1.5,
                                   num_skylights_x: int = 2,
                                   num_skylights_y: int = 2):
        """
        Ceiling slab with recessed skylight areas.
        """
        hw, hd = w / 2, d / 2
        
        # Main ceiling
        self.add_box(x, y, z, w, d, thickness)
        
        # Skylight recesses
        spacing_x = w / (num_skylights_x + 1)
        spacing_y = d / (num_skylights_y + 1)
        
        for ix in range(num_skylights_x):
            for iy in range(num_skylights_y):
                sx = x - hw + spacing_x * (ix + 1)
                sy = y - hd + spacing_y * (iy + 1)
                
                # Angled recess (like a skylight well)
                self._add_skylight_well(sx, sy, z, skylight_size, skylight_depth)
    
    def _add_skylight_well(self, x: float, y: float, z: float,
                           size: float, depth: float):
        """Add an angled skylight well."""
        hs = size / 2
        top_hs = hs * 0.6  # Smaller at top
        
        # Four angled sides of the well
        verts_bottom = [
            self.bm.verts.new((x - hs, y - hs, z)),
            self.bm.verts.new((x + hs, y - hs, z)),
            self.bm.verts.new((x + hs, y + hs, z)),
            self.bm.verts.new((x - hs, y + hs, z)),
        ]
        
        verts_top = [
            self.bm.verts.new((x - top_hs, y - top_hs, z + depth)),
            self.bm.verts.new((x + top_hs, y - top_hs, z + depth)),
            self.bm.verts.new((x + top_hs, y + top_hs, z + depth)),
            self.bm.verts.new((x - top_hs, y + top_hs, z + depth)),
        ]
        
        # Angled walls of well
        for i in range(4):
            ni = (i + 1) % 4
            self.bm.faces.new([verts_bottom[i], verts_top[i], verts_top[ni], verts_bottom[ni]])
        
        # Top opening
        self.bm.faces.new(verts_top)
    
    # =========================================================================
    # RAMP WITH EDGE RAILS
    # =========================================================================
    
    def add_detailed_ramp(self, x1: float, y1: float, z1: float,
                          x2: float, y2: float, z2: float,
                          width: float,
                          thickness: float = 0.5,
                          edge_height: float = 0.5):
        """Ramp with raised edges on both sides."""
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length < 0.01:
            return
        
        # Perpendicular for width
        px, py = -dy / length * width / 2, dx / length * width / 2
        
        # Main ramp surface
        v_top = [
            self.bm.verts.new((x1 - px, y1 - py, z1)),
            self.bm.verts.new((x1 + px, y1 + py, z1)),
            self.bm.verts.new((x2 + px, y2 + py, z2)),
            self.bm.verts.new((x2 - px, y2 - py, z2)),
        ]
        self.bm.faces.new(v_top)
        
        # Bottom
        v_bot = [
            self.bm.verts.new((x1 - px, y1 - py, z1 - thickness)),
            self.bm.verts.new((x1 + px, y1 + py, z1 - thickness)),
            self.bm.verts.new((x2 + px, y2 + py, z2 - thickness)),
            self.bm.verts.new((x2 - px, y2 - py, z2 - thickness)),
        ]
        self.bm.faces.new(v_bot[::-1])
        
        # Sides
        self.bm.faces.new([v_top[0], v_top[3], v_bot[3], v_bot[0]])
        self.bm.faces.new([v_top[1], v_bot[1], v_bot[2], v_top[2]])
        self.bm.faces.new([v_top[0], v_bot[0], v_bot[1], v_top[1]])
        self.bm.faces.new([v_top[2], v_bot[2], v_bot[3], v_top[3]])
        
        # Edge rails
        edge_w = 0.4
        edge_px, edge_py = -dy / length * edge_w / 2, dx / length * edge_w / 2
        
        # Left rail
        left_x, left_y = x1 - px + edge_px, y1 - py + edge_py
        left_x2, left_y2 = x2 - px + edge_px, y2 - py + edge_py
        self._add_ramp_rail(left_x, left_y, z1, left_x2, left_y2, z2, edge_w, edge_height)
        
        # Right rail
        right_x, right_y = x1 + px - edge_px, y1 + py - edge_py
        right_x2, right_y2 = x2 + px - edge_px, y2 + py - edge_py
        self._add_ramp_rail(right_x, right_y, z1, right_x2, right_y2, z2, edge_w, edge_height)
    
    def _add_ramp_rail(self, x1, y1, z1, x2, y2, z2, width, height):
        """Add a rail along a ramp edge."""
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length < 0.01:
            return
        
        px, py = -dy / length * width / 2, dx / length * width / 2
        
        v1 = [
            self.bm.verts.new((x1 - px, y1 - py, z1)),
            self.bm.verts.new((x1 + px, y1 + py, z1)),
            self.bm.verts.new((x1 + px, y1 + py, z1 + height)),
            self.bm.verts.new((x1 - px, y1 - py, z1 + height)),
        ]
        
        v2 = [
            self.bm.verts.new((x2 - px, y2 - py, z2)),
            self.bm.verts.new((x2 + px, y2 + py, z2)),
            self.bm.verts.new((x2 + px, y2 + py, z2 + height)),
            self.bm.verts.new((x2 - px, y2 - py, z2 + height)),
        ]
        
        # Connect
        self.bm.faces.new([v1[0], v1[1], v2[1], v2[0]])  # Bottom
        self.bm.faces.new([v1[3], v2[3], v2[2], v1[2]])  # Top
        self.bm.faces.new([v1[0], v2[0], v2[3], v1[3]])  # Outer
        self.bm.faces.new([v1[1], v1[2], v2[2], v2[1]])  # Inner
        self.bm.faces.new(v1)  # Start cap
        self.bm.faces.new(v2[::-1])  # End cap
    
    # =========================================================================
    # BALCONY OVERLOOK
    # =========================================================================
    
    def add_balcony_overlook(self, x: float, y: float, z: float,
                             w: float, d: float,
                             railing_height: float = 3.0,
                             railing_thickness: float = 0.5,
                             floor_thick: float = 1.5):
        """
        Balcony platform with railing on the open edge.
        Opens toward negative Y (looking into the main space).
        """
        # Floor with edges on 3 sides
        self.add_detailed_platform(x, y, z, w, d, floor_thick, 0.4, 0.3)
        
        # Railing on open edge (south)
        # Posts
        post_spacing = w / 4
        for i in range(5):
            post_x = x - w/2 + i * post_spacing
            self.add_box(post_x, y - d/2 + railing_thickness/2, z,
                        railing_thickness, railing_thickness, railing_height)
        
        # Top rail
        self.add_box(x, y - d/2 + railing_thickness/2, z + railing_height - railing_thickness/2,
                    w, railing_thickness, railing_thickness)
        
        # Mid rail
        self.add_box(x, y - d/2 + railing_thickness/2, z + railing_height * 0.5,
                    w, railing_thickness, railing_thickness * 0.8)
    
    # =========================================================================
    # FINALIZE
    # =========================================================================
    
    def finalize(self, collection) -> bpy.types.Object:
        """Create the Blender object."""
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=0.01)
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        
        mesh = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(mesh)
        self.bm.free()
        
        obj = bpy.data.objects.new(self.name, mesh)
        collection.objects.link(obj)
        return obj


# =============================================================================
# BASE GENERATOR WITH DETAILED INTERIORS
# =============================================================================

class TribesBaseGenerator:
    """Generates Tribes-style bases with architectural detail."""
    
    def __init__(self, cfg: Config = None):
        self.cfg = cfg or Config()
        self.collection = None
        random.seed(self.cfg.seed)
    
    def generate(self):
        """Generate the complete base."""
        print("\n" + "="*60)
        print("FPSZ BASE GENERATOR v6 - Architectural Detail")
        print(f"Style: {self.cfg.style.value}")
        print(f"Seed: {self.cfg.seed}")
        print("="*60)
        
        self._setup_collection()
        
        print("\n1. Building exterior shell...")
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
        
        print("\nGeneration complete!")
        print("="*60 + "\n")
    
    def _setup_collection(self):
        """Setup Blender collection."""
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
        """Build exterior shell."""
        cfg = self.cfg
        mb = DetailedMeshBuilder("Base_Exterior")
        
        taper = cfg.base_height * cfg.wall_taper
        top_w = cfg.base_width - taper * 2
        top_d = cfg.base_depth - taper * 2
        
        # Outer tapered shell
        self._add_tapered_shell(mb, 
            cfg.base_width, cfg.base_depth,
            top_w, top_d,
            cfg.base_height,
            cfg.exterior_wall_thickness,
            0)
        
        obj = mb.finalize(self.collection)
        self._apply_material(obj, "Exterior", (0.38, 0.40, 0.42))
    
    def _add_tapered_shell(self, mb, base_w, base_d, top_w, top_d, height, thick, z_base):
        """Add hollow tapered shell."""
        # Outer
        bw, bd = base_w / 2, base_d / 2
        tw, td = top_w / 2, top_d / 2
        z0, z1 = z_base, z_base + height
        
        v_ob = [
            mb.bm.verts.new((-bw, -bd, z0)),
            mb.bm.verts.new((bw, -bd, z0)),
            mb.bm.verts.new((bw, bd, z0)),
            mb.bm.verts.new((-bw, bd, z0)),
        ]
        v_ot = [
            mb.bm.verts.new((-tw, -td, z1)),
            mb.bm.verts.new((tw, -td, z1)),
            mb.bm.verts.new((tw, td, z1)),
            mb.bm.verts.new((-tw, td, z1)),
        ]
        
        mb.bm.faces.new(v_ob[::-1])
        mb.bm.faces.new(v_ot)
        for i in range(4):
            ni = (i + 1) % 4
            mb.bm.faces.new([v_ob[i], v_ob[ni], v_ot[ni], v_ot[i]])
        
        # Inner (smaller)
        ibw, ibd = bw - thick, bd - thick
        itw, itd = tw - thick, td - thick
        
        v_ib = [
            mb.bm.verts.new((-ibw, -ibd, z0)),
            mb.bm.verts.new((ibw, -ibd, z0)),
            mb.bm.verts.new((ibw, ibd, z0)),
            mb.bm.verts.new((-ibw, ibd, z0)),
        ]
        v_it = [
            mb.bm.verts.new((-itw, -itd, z1)),
            mb.bm.verts.new((itw, -itd, z1)),
            mb.bm.verts.new((itw, itd, z1)),
            mb.bm.verts.new((-itw, itd, z1)),
        ]
        
        mb.bm.faces.new(v_ib)
        mb.bm.faces.new(v_it[::-1])
        for i in range(4):
            ni = (i + 1) % 4
            mb.bm.faces.new([v_ib[ni], v_ib[i], v_it[i], v_it[ni]])
    
    def _build_main_hall(self):
        """Build the main central hall with architectural details."""
        cfg = self.cfg
        mb = DetailedMeshBuilder("Main_Hall")
        
        # Main hall dimensions
        hall_w = cfg.atrium_width
        hall_d = cfg.atrium_depth
        z = cfg.floor_thickness
        
        # Ground floor with detailed edges
        mb.add_detailed_platform(0, 0, z, hall_w, hall_d,
                                cfg.floor_thickness,
                                cfg.platform_edge_height,
                                cfg.platform_edge_width)
        
        # Raised central platform (for flag/objective)
        center_size = 10.0
        center_height = 2.0
        mb.add_detailed_platform(0, 0, z + center_height, center_size, center_size,
                                1.0, 0.5, 0.3)
        
        # Steps up to center platform
        step_w = center_size + 2
        step_d = 2.0
        step_h = center_height / 3
        for i in range(3):
            step_y = -(center_size/2 + 1 + i * step_d)
            mb.add_box(0, step_y, z + i * step_h, step_w, step_d, step_h)
            mb.add_box(0, -step_y, z + i * step_h, step_w, step_d, step_h)
        
        # Corner columns
        col_offset = hall_w / 2 - cfg.column_width
        col_height = cfg.level_height * 2
        for cx, cy in [(col_offset, col_offset), (col_offset, -col_offset),
                       (-col_offset, col_offset), (-col_offset, -col_offset)]:
            mb.add_detailed_column(cx, cy, z, z + col_height,
                                  cfg.column_width,
                                  cfg.column_base_height,
                                  cfg.column_cap_height)
        
        # Interior wall panels on perimeter
        panel_w = 6.0
        panel_h = 8.0
        panel_z = z + 2
        
        # North and South wall panels
        for px in [-hall_w/4, hall_w/4]:
            mb.add_wall_panel(px, hall_d/2 - 0.5, panel_z, panel_w, panel_h, 'south')
            mb.add_wall_panel(px, -hall_d/2 + 0.5, panel_z, panel_w, panel_h, 'north')
        
        obj = mb.finalize(self.collection)
        self._apply_material(obj, "Floor", (0.32, 0.35, 0.38))
    
    def _build_corridors(self):
        """Build corridors with walls and trim."""
        cfg = self.cfg
        mb = DetailedMeshBuilder("Corridors")
        
        z = cfg.floor_thickness
        corridor_w = 10.0
        corridor_length = (cfg.base_depth - cfg.atrium_depth) / 2 - cfg.exterior_wall_thickness
        
        # North corridor
        corr_y = cfg.atrium_depth / 2 + corridor_length / 2
        mb.add_detailed_platform(0, corr_y, z, corridor_w, corridor_length,
                                cfg.floor_thickness, 0.4, 0.3)
        
        # Corridor walls with trim
        wall_x = corridor_w / 2
        wall_y1 = cfg.atrium_depth / 2
        wall_y2 = cfg.atrium_depth / 2 + corridor_length
        
        mb.add_wall_with_trim(-wall_x, wall_y1, -wall_x, wall_y2, z, cfg.level_height,
                             cfg.interior_wall_thickness, cfg.trim_height, cfg.trim_inset, 3)
        mb.add_wall_with_trim(wall_x, wall_y1, wall_x, wall_y2, z, cfg.level_height,
                             cfg.interior_wall_thickness, cfg.trim_height, cfg.trim_inset, 3)
        
        # South corridor (mirror)
        corr_y = -(cfg.atrium_depth / 2 + corridor_length / 2)
        mb.add_detailed_platform(0, corr_y, z, corridor_w, corridor_length,
                                cfg.floor_thickness, 0.4, 0.3)
        
        wall_y1 = -cfg.atrium_depth / 2
        wall_y2 = -(cfg.atrium_depth / 2 + corridor_length)
        
        mb.add_wall_with_trim(-wall_x, wall_y1, -wall_x, wall_y2, z, cfg.level_height,
                             cfg.interior_wall_thickness, cfg.trim_height, cfg.trim_inset, 3)
        mb.add_wall_with_trim(wall_x, wall_y1, wall_x, wall_y2, z, cfg.level_height,
                             cfg.interior_wall_thickness, cfg.trim_height, cfg.trim_inset, 3)
        
        # East-West corridors
        side_corr_len = (cfg.base_width - cfg.atrium_width) / 2 - cfg.exterior_wall_thickness
        
        for side in [1, -1]:
            corr_x = side * (cfg.atrium_width / 2 + side_corr_len / 2)
            mb.add_detailed_platform(corr_x, 0, z, side_corr_len, corridor_w,
                                    cfg.floor_thickness, 0.4, 0.3)
        
        obj = mb.finalize(self.collection)
        self._apply_material(obj, "Corridor", (0.30, 0.32, 0.35))
    
    def _build_upper_levels(self):
        """Build upper level platforms with balconies."""
        cfg = self.cfg
        mb = DetailedMeshBuilder("Upper_Levels")
        
        for level in range(1, cfg.num_levels):
            z = level * cfg.level_height + cfg.floor_thickness
            
            # Calculate interior size at this height (accounting for taper)
            height_ratio = z / cfg.base_height
            taper = cfg.base_height * cfg.wall_taper * height_ratio
            avail_w = cfg.base_width - cfg.exterior_wall_thickness * 2 - taper * 2
            avail_d = cfg.base_depth - cfg.exterior_wall_thickness * 2 - taper * 2
            
            # Ring platforms around atrium
            platform_w = (avail_w - cfg.atrium_width) / 2 - 2
            platform_d = (avail_d - cfg.atrium_depth) / 2 - 2
            
            if platform_w > 4 and platform_d > 4:
                # North platform with balcony overlooking main hall
                py = avail_d / 2 - platform_d / 2
                mb.add_balcony_overlook(0, py, z, avail_w * 0.7, platform_d,
                                       3.0, 0.4, cfg.floor_thickness)
                
                # South platform
                mb.add_balcony_overlook(0, -py, z, avail_w * 0.7, platform_d,
                                       3.0, 0.4, cfg.floor_thickness)
                
                # East platform
                px = avail_w / 2 - platform_w / 2
                mb.add_detailed_platform(px, 0, z, platform_w, cfg.atrium_depth * 0.6,
                                        cfg.floor_thickness, 0.4, 0.3)
                
                # West platform
                mb.add_detailed_platform(-px, 0, z, platform_w, cfg.atrium_depth * 0.6,
                                        cfg.floor_thickness, 0.4, 0.3)
                
                # Corner columns continuing upward
                if level < cfg.num_levels - 1:
                    col_offset_w = avail_w / 2 - cfg.column_width - 2
                    col_offset_d = avail_d / 2 - cfg.column_width - 2
                    
                    for cx, cy in [(col_offset_w, col_offset_d), (col_offset_w, -col_offset_d),
                                   (-col_offset_w, col_offset_d), (-col_offset_w, -col_offset_d)]:
                        mb.add_detailed_column(cx, cy, z, z + cfg.level_height,
                                              cfg.column_width * 0.8,
                                              cfg.column_base_height * 0.7,
                                              cfg.column_cap_height * 0.7)
            
            # Ceiling with skylights on top level
            if level == cfg.num_levels - 1:
                ceiling_z = z + cfg.level_height - 2
                mb.add_ceiling_with_skylights(0, 0, ceiling_z, 
                                             cfg.atrium_width * 0.8, 
                                             cfg.atrium_depth * 0.8,
                                             1.5, cfg.skylight_size, cfg.skylight_depth,
                                             3, 3)
        
        obj = mb.finalize(self.collection)
        self._apply_material(obj, "Upper", (0.33, 0.36, 0.39))
    
    def _build_ramps(self):
        """Build ramps with edge rails."""
        cfg = self.cfg
        mb = DetailedMeshBuilder("Ramps")
        
        ramp_rise = cfg.level_height
        ramp_run = ramp_rise / math.tan(math.radians(28))
        
        for level in range(cfg.num_levels - 1):
            z_start = (level + 1) * cfg.level_height + cfg.floor_thickness
            z_end = z_start + ramp_rise
            
            # Alternate positions and directions
            if level % 4 == 0:
                # East side, going north
                x = cfg.atrium_width / 2 - 6
                y_start = -ramp_run / 2
                y_end = ramp_run / 2
                mb.add_detailed_ramp(x, y_start, z_start, x, y_end, z_end,
                                    cfg.ramp_width, 0.5, cfg.ramp_edge_height)
            elif level % 4 == 1:
                # West side, going south
                x = -(cfg.atrium_width / 2 - 6)
                y_start = ramp_run / 2
                y_end = -ramp_run / 2
                mb.add_detailed_ramp(x, y_start, z_start, x, y_end, z_end,
                                    cfg.ramp_width, 0.5, cfg.ramp_edge_height)
            elif level % 4 == 2:
                # North side, going east
                y = cfg.atrium_depth / 2 - 6
                x_start = -ramp_run / 2
                x_end = ramp_run / 2
                mb.add_detailed_ramp(x_start, y, z_start, x_end, y, z_end,
                                    cfg.ramp_width, 0.5, cfg.ramp_edge_height)
            else:
                # South side, going west
                y = -(cfg.atrium_depth / 2 - 6)
                x_start = ramp_run / 2
                x_end = -ramp_run / 2
                mb.add_detailed_ramp(x_start, y, z_start, x_end, y, z_end,
                                    cfg.ramp_width, 0.5, cfg.ramp_edge_height)
        
        obj = mb.finalize(self.collection)
        self._apply_material(obj, "Ramp", (0.40, 0.38, 0.32))
    
    def _build_entrances(self):
        """Build entrance ramps."""
        cfg = self.cfg
        mb = DetailedMeshBuilder("Entrances")
        
        entrance_z = cfg.level_height * 0.35
        taper_at_entrance = cfg.base_height * cfg.wall_taper * (entrance_z / cfg.base_height)
        wall_offset = cfg.base_depth / 2 - taper_at_entrance
        
        ramp_length = entrance_z / math.tan(math.radians(20))
        
        # South entrance
        mb.add_detailed_ramp(
            0, -(wall_offset + ramp_length), 0,
            0, -wall_offset + 5, entrance_z,
            cfg.ramp_width + 2, 1.0, cfg.ramp_edge_height
        )
        
        # Landing platform
        mb.add_detailed_platform(0, -wall_offset + 8, entrance_z,
                                cfg.ramp_width + 6, 8, 1.0, 0.5, 0.3)
        
        # North entrance
        mb.add_detailed_ramp(
            0, wall_offset + ramp_length, 0,
            0, wall_offset - 5, entrance_z,
            cfg.ramp_width + 2, 1.0, cfg.ramp_edge_height
        )
        
        mb.add_detailed_platform(0, wall_offset - 8, entrance_z,
                                cfg.ramp_width + 6, 8, 1.0, 0.5, 0.3)
        
        obj = mb.finalize(self.collection)
        self._apply_material(obj, "Entrance", (0.40, 0.38, 0.32))
    
    def _apply_material(self, obj, name: str, color: Tuple[float, float, float]):
        """Apply material."""
        mat_name = f"FPSZ_{name}"
        mat = bpy.data.materials.get(mat_name)
        
        if not mat:
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes.get('Principled BSDF')
            if bsdf:
                bsdf.inputs['Base Color'].default_value = (*color, 1.0)
                bsdf.inputs['Roughness'].default_value = 0.75
        
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)


# =============================================================================
# PUBLIC API
# =============================================================================

def generate_base(style: str = "pyramid", seed: int = None, num_levels: int = 4, **kwargs):
    """Generate a Tribes-style base."""
    cfg = Config()
    
    style_map = {
        "pyramid": BaseStyle.PYRAMID,
        "stepped": BaseStyle.STEPPED,
        "tower": BaseStyle.TOWER,
    }
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
    """Generate a new procedural base"""
    bl_idname = "fpsz.generate_base"
    bl_label = "Generate Base"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        props = context.scene.fpsz_props
        
        if props.use_random_seed:
            import time
            seed = int(time.time()) % 100000
        else:
            seed = props.seed
        
        generate_base(
            style=props.style,
            seed=seed,
            num_levels=props.num_levels,
            base_width=props.base_width,
            base_depth=props.base_depth,
            wall_taper=props.wall_taper,
        )
        
        props.seed = seed
        self.report({'INFO'}, f"Generated {props.style} base with seed {seed}")
        return {'FINISHED'}


class FPSZ_OT_RandomGenerate(bpy.types.Operator):
    """Generate with random settings"""
    bl_idname = "fpsz.random_generate"
    bl_label = "Random Generate"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        props = context.scene.fpsz_props
        
        import time
        seed = int(time.time()) % 100000
        styles = ['pyramid', 'stepped', 'tower']
        style = random.choice(styles)
        levels = random.randint(3, 5)
        
        generate_base(style=style, seed=seed, num_levels=levels)
        
        props.style = style
        props.seed = seed
        props.num_levels = levels
        
        self.report({'INFO'}, f"Random: {style}, {levels} levels, seed {seed}")
        return {'FINISHED'}


class FPSZ_OT_ClearGenerated(bpy.types.Operator):
    """Remove generated base"""
    bl_idname = "fpsz.clear_generated"
    bl_label = "Clear Generated"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        col_name = "FPSZ_Generated_Base"
        
        if col_name in bpy.data.collections:
            col = bpy.data.collections[col_name]
            for obj in list(col.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(col)
            self.report({'INFO'}, "Cleared generated base")
        else:
            self.report({'WARNING'}, "No generated base found")
        
        return {'FINISHED'}


class FPSZ_Properties(bpy.types.PropertyGroup):
    style: bpy.props.EnumProperty(
        name="Style",
        items=[
            ('pyramid', 'Pyramid', 'Tapered pyramid'),
            ('stepped', 'Stepped', 'Terraced pyramid'),
            ('tower', 'Tower', 'Tower on base'),
        ],
        default='pyramid'
    )
    
    seed: bpy.props.IntProperty(name="Seed", default=12345, min=0, max=99999)
    use_random_seed: bpy.props.BoolProperty(name="Random Seed", default=False)
    num_levels: bpy.props.IntProperty(name="Levels", default=4, min=2, max=6)
    base_width: bpy.props.FloatProperty(name="Width", default=80.0, min=50.0, max=120.0)
    base_depth: bpy.props.FloatProperty(name="Depth", default=80.0, min=50.0, max=120.0)
    wall_taper: bpy.props.FloatProperty(name="Wall Taper", default=0.2, min=0.0, max=0.4)


class FPSZ_PT_MainPanel(bpy.types.Panel):
    bl_label = "FPSZ Generator v6"
    bl_idname = "FPSZ_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FPSZ Generator'
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.fpsz_props
        
        box = layout.box()
        box.label(text="Style", icon='MESH_CUBE')
        box.prop(props, "style", text="")
        
        box = layout.box()
        box.label(text="Settings", icon='PREFERENCES')
        row = box.row(align=True)
        row.prop(props, "seed")
        row.prop(props, "use_random_seed", text="", icon='FILE_REFRESH')
        box.prop(props, "num_levels")
        col = box.column(align=True)
        col.prop(props, "base_width")
        col.prop(props, "base_depth")
        box.prop(props, "wall_taper", slider=True)
        
        layout.separator()
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator("fpsz.generate_base", text="Generate", icon='PLAY')
        row.operator("fpsz.random_generate", text="Random", icon='QUESTION')
        layout.operator("fpsz.clear_generated", text="Clear", icon='TRASH')


classes = (
    FPSZ_Properties,
    FPSZ_OT_GenerateBase,
    FPSZ_OT_RandomGenerate,
    FPSZ_OT_ClearGenerated,
    FPSZ_PT_MainPanel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.fpsz_props = bpy.props.PointerProperty(type=FPSZ_Properties)
    print("FPSZ Generator v6: Registered. Find panel in View3D > Sidebar > FPSZ Generator")


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.fpsz_props


if __name__ == "__main__":
    register()
