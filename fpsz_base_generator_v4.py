"""
FPSZ Procedural Base Generator v4 - Form-First Approach
=========================================================
Generates Tribes-style bases by starting with the EXTERIOR FORM
and carving interior spaces, rather than assembling boxes.

Key Tribes base characteristics:
- Tapered/sloped exterior walls (pyramidal forms)
- Central open atrium with platforms at multiple levels
- Integrated ramps (interior and exterior)
- Balconies and overhangs
- One unified structure, not separate rooms

Run in Blender 4.x with Alt+P
"""

import bpy
import bmesh
from mathutils import Vector
import math
import random
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum


# =============================================================================
# CONFIGURATION
# =============================================================================

class BaseStyle(Enum):
    """Different Tribes base architectural styles."""
    PYRAMID = "pyramid"           # Classic tapered pyramid
    STEPPED_PYRAMID = "stepped"   # Stepped/terraced pyramid
    TOWER_ON_BASE = "tower"       # Tower sitting on wider base
    BUNKER = "bunker"             # Low, wide, fortified


@dataclass
class Config:
    """Base generation configuration."""
    
    # Overall size
    base_width: float = 64.0          # Base footprint width
    base_depth: float = 64.0          # Base footprint depth
    base_height: float = 48.0         # Total height
    
    # Taper (0 = vertical walls, 0.5 = 45 degree slope)
    wall_taper: float = 0.3           # How much walls slope inward
    
    # Interior
    wall_thickness: float = 4.0       # Thickness of exterior walls
    floor_thickness: float = 1.0
    
    # Levels
    num_levels: int = 4               # Interior floor levels
    level_height: float = 10.0        # Height per level
    
    # Central atrium (open vertical space)
    atrium_width: float = 20.0
    atrium_depth: float = 20.0
    
    # Platforms/balconies
    platform_width: float = 8.0
    platform_depth: float = 12.0
    
    # Ramps
    ramp_width: float = 8.0
    ramp_angle: float = 30.0          # Degrees
    
    # Doorways
    doorway_width: float = 8.0
    doorway_height: float = 9.0
    
    # Entrances
    num_entrances: int = 2
    entrance_width: float = 10.0
    entrance_height: float = 10.0
    
    # Style
    style: BaseStyle = BaseStyle.PYRAMID
    
    # Random seed
    seed: int = 42


# =============================================================================
# MESH BUILDER WITH CSG-LIKE OPERATIONS
# =============================================================================

class MeshBuilder:
    """Builds base geometry using additive/subtractive approach."""
    
    def __init__(self, name: str):
        self.name = name
        self.bm = bmesh.new()
    
    # =========================================================================
    # PRIMITIVE SHAPES
    # =========================================================================
    
    def add_tapered_box(self, 
                        base_width: float, base_depth: float,
                        top_width: float, top_depth: float,
                        height: float,
                        center: Vector = None,
                        base_z: float = 0.0) -> List:
        """
        Add a tapered box (frustum) - wider at bottom, narrower at top.
        This is the core shape for Tribes-style sloped walls.
        """
        if center is None:
            center = Vector((0, 0, 0))
        
        cx, cy = center.x, center.y
        z0 = base_z
        z1 = base_z + height
        
        # Bottom vertices (wider)
        bw, bd = base_width / 2, base_depth / 2
        # Top vertices (narrower)
        tw, td = top_width / 2, top_depth / 2
        
        # Create vertices
        v_bottom = [
            self.bm.verts.new((cx - bw, cy - bd, z0)),
            self.bm.verts.new((cx + bw, cy - bd, z0)),
            self.bm.verts.new((cx + bw, cy + bd, z0)),
            self.bm.verts.new((cx - bw, cy + bd, z0)),
        ]
        
        v_top = [
            self.bm.verts.new((cx - tw, cy - td, z1)),
            self.bm.verts.new((cx + tw, cy - td, z1)),
            self.bm.verts.new((cx + tw, cy + td, z1)),
            self.bm.verts.new((cx - tw, cy + td, z1)),
        ]
        
        # Bottom face
        self.bm.faces.new(v_bottom[::-1])
        
        # Top face
        self.bm.faces.new(v_top)
        
        # Side faces (sloped walls)
        for i in range(4):
            ni = (i + 1) % 4
            self.bm.faces.new([v_bottom[i], v_bottom[ni], v_top[ni], v_top[i]])
        
        return v_bottom + v_top
    
    def add_platform(self, 
                     x: float, y: float, z: float,
                     width: float, depth: float, 
                     thickness: float = 1.0):
        """Add a horizontal platform/floor section."""
        hw, hd = width / 2, depth / 2
        
        # Top surface
        verts_top = [
            self.bm.verts.new((x - hw, y - hd, z)),
            self.bm.verts.new((x + hw, y - hd, z)),
            self.bm.verts.new((x + hw, y + hd, z)),
            self.bm.verts.new((x - hw, y + hd, z)),
        ]
        self.bm.faces.new(verts_top)
        
        # Bottom surface
        z_bot = z - thickness
        verts_bot = [
            self.bm.verts.new((x - hw, y + hd, z_bot)),
            self.bm.verts.new((x + hw, y + hd, z_bot)),
            self.bm.verts.new((x + hw, y - hd, z_bot)),
            self.bm.verts.new((x - hw, y - hd, z_bot)),
        ]
        self.bm.faces.new(verts_bot)
        
        # Side faces
        for i in range(4):
            ni = (i + 1) % 4
            self.bm.faces.new([
                verts_top[i], verts_top[ni],
                verts_bot[3-ni], verts_bot[3-i]
            ])
    
    def add_ramp(self,
                 start_x: float, start_y: float, start_z: float,
                 end_x: float, end_y: float, end_z: float,
                 width: float,
                 thickness: float = 0.5):
        """Add a ramp between two points."""
        
        # Direction vector
        dx = end_x - start_x
        dy = end_y - start_y
        length = math.sqrt(dx*dx + dy*dy)
        
        if length < 0.01:
            return
        
        # Perpendicular for width
        px, py = -dy / length * width / 2, dx / length * width / 2
        
        # Top surface vertices
        v_top = [
            self.bm.verts.new((start_x - px, start_y - py, start_z)),
            self.bm.verts.new((start_x + px, start_y + py, start_z)),
            self.bm.verts.new((end_x + px, end_y + py, end_z)),
            self.bm.verts.new((end_x - px, end_y - py, end_z)),
        ]
        self.bm.faces.new(v_top)
        
        # Bottom surface
        v_bot = [
            self.bm.verts.new((start_x - px, start_y - py, start_z - thickness)),
            self.bm.verts.new((start_x + px, start_y + py, start_z - thickness)),
            self.bm.verts.new((end_x + px, end_y + py, end_z - thickness)),
            self.bm.verts.new((end_x - px, end_y - py, end_z - thickness)),
        ]
        self.bm.faces.new(v_bot[::-1])
        
        # Side walls
        # Left side
        self.bm.faces.new([v_top[0], v_top[3], v_bot[3], v_bot[0]])
        # Right side
        self.bm.faces.new([v_top[1], v_bot[1], v_bot[2], v_top[2]])
        # Start cap
        self.bm.faces.new([v_top[0], v_bot[0], v_bot[1], v_top[1]])
        # End cap
        self.bm.faces.new([v_top[2], v_bot[2], v_bot[3], v_top[3]])
    
    def add_wall_section(self,
                         x1: float, y1: float, z1: float,
                         x2: float, y2: float, z2: float,
                         height: float,
                         thickness: float = 0.5):
        """Add a wall section (can be sloped in XY and/or Z)."""
        
        # Direction in XY
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        
        if length < 0.01:
            return
        
        # Perpendicular for thickness
        nx, ny = -dy / length * thickness / 2, dx / length * thickness / 2
        
        # Four corners at bottom
        v_b1 = self.bm.verts.new((x1 - nx, y1 - ny, z1))
        v_b2 = self.bm.verts.new((x1 + nx, y1 + ny, z1))
        v_b3 = self.bm.verts.new((x2 + nx, y2 + ny, z2))
        v_b4 = self.bm.verts.new((x2 - nx, y2 - ny, z2))
        
        # Four corners at top
        v_t1 = self.bm.verts.new((x1 - nx, y1 - ny, z1 + height))
        v_t2 = self.bm.verts.new((x1 + nx, y1 + ny, z1 + height))
        v_t3 = self.bm.verts.new((x2 + nx, y2 + ny, z2 + height))
        v_t4 = self.bm.verts.new((x2 - nx, y2 - ny, z2 + height))
        
        # Faces
        self.bm.faces.new([v_b1, v_b2, v_b3, v_b4])  # Bottom
        self.bm.faces.new([v_t4, v_t3, v_t2, v_t1])  # Top
        self.bm.faces.new([v_b1, v_b4, v_t4, v_t1])  # Outer
        self.bm.faces.new([v_b2, v_t2, v_t3, v_b3])  # Inner
        self.bm.faces.new([v_b1, v_t1, v_t2, v_b2])  # Start
        self.bm.faces.new([v_b3, v_t3, v_t4, v_b4])  # End
    
    def add_column(self, x: float, y: float, z_base: float, z_top: float, radius: float, sides: int = 8):
        """Add a column/pillar."""
        verts_bottom = []
        verts_top = []
        
        for i in range(sides):
            angle = 2 * math.pi * i / sides
            px = x + radius * math.cos(angle)
            py = y + radius * math.sin(angle)
            
            verts_bottom.append(self.bm.verts.new((px, py, z_base)))
            verts_top.append(self.bm.verts.new((px, py, z_top)))
        
        # Bottom cap
        self.bm.faces.new(verts_bottom[::-1])
        # Top cap
        self.bm.faces.new(verts_top)
        
        # Sides
        for i in range(sides):
            ni = (i + 1) % sides
            self.bm.faces.new([
                verts_bottom[i], verts_bottom[ni],
                verts_top[ni], verts_top[i]
            ])
    
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
# BASE GENERATOR - FORM FIRST APPROACH
# =============================================================================

class TribesBaseGenerator:
    """
    Generates Tribes-style bases using a form-first approach:
    1. Create exterior shell with sloped walls
    2. Create interior atrium space
    3. Add platforms at multiple levels
    4. Add ramps connecting levels
    5. Add entrances
    """
    
    def __init__(self, cfg: Config = None):
        self.cfg = cfg or Config()
        self.collection = None
        random.seed(self.cfg.seed)
    
    def generate(self):
        """Generate the complete base."""
        print("\n" + "="*60)
        print("FPSZ BASE GENERATOR v4 - Form First")
        print(f"Style: {self.cfg.style.value}")
        print("="*60)
        
        self._setup_collection()
        
        if self.cfg.style == BaseStyle.PYRAMID:
            self._generate_pyramid_base()
        elif self.cfg.style == BaseStyle.STEPPED_PYRAMID:
            self._generate_stepped_base()
        elif self.cfg.style == BaseStyle.TOWER_ON_BASE:
            self._generate_tower_base()
        else:
            self._generate_bunker_base()
        
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
    
    # =========================================================================
    # PYRAMID STYLE
    # =========================================================================
    
    def _generate_pyramid_base(self):
        """Generate classic pyramid-style base with sloped walls."""
        cfg = self.cfg
        
        print("\n1. Creating exterior shell...")
        mb_exterior = MeshBuilder("Base_Exterior")
        
        # Calculate top dimensions based on taper
        taper_amount = cfg.base_height * cfg.wall_taper
        top_width = cfg.base_width - taper_amount * 2
        top_depth = cfg.base_depth - taper_amount * 2
        
        # Exterior tapered shell
        mb_exterior.add_tapered_box(
            cfg.base_width, cfg.base_depth,
            top_width, top_depth,
            cfg.base_height,
            base_z=0
        )
        
        exterior_obj = mb_exterior.finalize(self.collection)
        self._apply_material(exterior_obj, "Exterior", (0.45, 0.47, 0.5))
        
        print("2. Creating interior spaces...")
        mb_interior = MeshBuilder("Base_Interior")
        
        # Interior floors at each level
        interior_width = cfg.base_width - cfg.wall_thickness * 2
        interior_depth = cfg.base_depth - cfg.wall_thickness * 2
        
        for level in range(cfg.num_levels):
            z = level * cfg.level_height + cfg.floor_thickness
            
            # Calculate interior size at this height (accounting for taper)
            height_ratio = z / cfg.base_height
            taper_at_level = taper_amount * height_ratio
            level_width = interior_width - taper_at_level * 2
            level_depth = interior_depth - taper_at_level * 2
            
            # Don't create floor for atrium area in center
            # Instead, create floor sections around the perimeter
            
            # Platform depth (how far from wall)
            platform_d = (level_depth - cfg.atrium_depth) / 2
            platform_w = (level_width - cfg.atrium_width) / 2
            
            if platform_d > 2 and platform_w > 2:
                # North platform
                mb_interior.add_platform(
                    0, level_depth/2 - platform_d/2, z,
                    level_width, platform_d, cfg.floor_thickness
                )
                
                # South platform
                mb_interior.add_platform(
                    0, -(level_depth/2 - platform_d/2), z,
                    level_width, platform_d, cfg.floor_thickness
                )
                
                # East platform (connecting north-south)
                mb_interior.add_platform(
                    level_width/2 - platform_w/2, 0, z,
                    platform_w, cfg.atrium_depth, cfg.floor_thickness
                )
                
                # West platform (connecting north-south)
                mb_interior.add_platform(
                    -(level_width/2 - platform_w/2), 0, z,
                    platform_w, cfg.atrium_depth, cfg.floor_thickness
                )
        
        # Ground floor (solid)
        mb_interior.add_platform(0, 0, cfg.floor_thickness, 
                                 interior_width * 0.9, interior_depth * 0.9, 
                                 cfg.floor_thickness)
        
        interior_obj = mb_interior.finalize(self.collection)
        self._apply_material(interior_obj, "Floor", (0.35, 0.38, 0.4))
        
        print("3. Creating ramps...")
        self._add_interior_ramps(cfg)
        
        print("4. Creating entrances...")
        self._add_entrances_pyramid(cfg, taper_amount)
        
        print("5. Adding details...")
        self._add_columns(cfg)
    
    def _add_interior_ramps(self, cfg: Config):
        """Add ramps connecting levels inside."""
        mb_ramps = MeshBuilder("Base_Ramps")
        
        ramp_rise = cfg.level_height
        ramp_run = ramp_rise / math.tan(math.radians(cfg.ramp_angle))
        
        for level in range(cfg.num_levels - 1):
            z_start = (level + 1) * cfg.level_height + cfg.floor_thickness
            z_end = z_start + ramp_rise
            
            # Alternate ramp positions
            if level % 2 == 0:
                # Ramp on east side going north
                start_x = cfg.atrium_width / 2 + 2
                start_y = -ramp_run / 2
                end_y = ramp_run / 2
                mb_ramps.add_ramp(start_x, start_y, z_start,
                                  start_x, end_y, z_end,
                                  cfg.ramp_width)
            else:
                # Ramp on west side going south
                start_x = -(cfg.atrium_width / 2 + 2)
                start_y = ramp_run / 2
                end_y = -ramp_run / 2
                mb_ramps.add_ramp(start_x, start_y, z_start,
                                  start_x, end_y, z_end,
                                  cfg.ramp_width)
        
        ramps_obj = mb_ramps.finalize(self.collection)
        self._apply_material(ramps_obj, "Ramp", (0.5, 0.45, 0.35))
    
    def _add_entrances_pyramid(self, cfg: Config, taper_amount: float):
        """Add entrance ramps to pyramid base."""
        mb_entrance = MeshBuilder("Base_Entrances")
        
        # Entrance height (slightly above ground)
        entrance_z = cfg.level_height * 0.5
        
        # Calculate wall position at entrance height
        taper_at_entrance = taper_amount * (entrance_z / cfg.base_height)
        wall_offset = cfg.base_depth / 2 - taper_at_entrance
        
        # Ramp from ground to entrance
        ramp_length = entrance_z / math.tan(math.radians(cfg.ramp_angle))
        
        # South entrance ramp
        mb_entrance.add_ramp(
            0, -(wall_offset + ramp_length), 0,
            0, -wall_offset, entrance_z,
            cfg.entrance_width, 1.0
        )
        
        # North entrance ramp
        mb_entrance.add_ramp(
            0, wall_offset + ramp_length, 0,
            0, wall_offset, entrance_z,
            cfg.entrance_width, 1.0
        )
        
        # Entrance platforms
        mb_entrance.add_platform(0, -(wall_offset - 2), entrance_z,
                                 cfg.entrance_width + 4, 6, 1.0)
        mb_entrance.add_platform(0, wall_offset - 2, entrance_z,
                                 cfg.entrance_width + 4, 6, 1.0)
        
        entrance_obj = mb_entrance.finalize(self.collection)
        self._apply_material(entrance_obj, "Entrance", (0.5, 0.45, 0.35))
    
    def _add_columns(self, cfg: Config):
        """Add decorative/structural columns."""
        mb_columns = MeshBuilder("Base_Columns")
        
        # Columns at corners of atrium
        col_positions = [
            (cfg.atrium_width/2 + 1, cfg.atrium_depth/2 + 1),
            (cfg.atrium_width/2 + 1, -(cfg.atrium_depth/2 + 1)),
            (-(cfg.atrium_width/2 + 1), cfg.atrium_depth/2 + 1),
            (-(cfg.atrium_width/2 + 1), -(cfg.atrium_depth/2 + 1)),
        ]
        
        for x, y in col_positions:
            mb_columns.add_column(x, y, cfg.floor_thickness, 
                                  cfg.base_height - 4, 1.5, 8)
        
        columns_obj = mb_columns.finalize(self.collection)
        self._apply_material(columns_obj, "Column", (0.3, 0.32, 0.35))
    
    # =========================================================================
    # STEPPED PYRAMID STYLE
    # =========================================================================
    
    def _generate_stepped_base(self):
        """Generate stepped/terraced pyramid base."""
        cfg = self.cfg
        
        print("\n1. Creating stepped exterior...")
        mb_exterior = MeshBuilder("Base_Exterior")
        
        # Create multiple tiers
        num_tiers = 4
        tier_height = cfg.base_height / num_tiers
        
        for tier in range(num_tiers):
            # Each tier is smaller than the one below
            scale = 1.0 - (tier * 0.2)
            tier_width = cfg.base_width * scale
            tier_depth = cfg.base_depth * scale
            
            # Slight taper within each tier
            top_scale = scale - 0.05
            top_width = cfg.base_width * top_scale
            top_depth = cfg.base_depth * top_scale
            
            z_base = tier * tier_height
            
            mb_exterior.add_tapered_box(
                tier_width, tier_depth,
                top_width, top_depth,
                tier_height,
                base_z=z_base
            )
        
        exterior_obj = mb_exterior.finalize(self.collection)
        self._apply_material(exterior_obj, "Exterior", (0.45, 0.47, 0.5))
        
        print("2. Creating interior...")
        self._create_stepped_interior(cfg, num_tiers, tier_height)
        
        print("3. Creating ramps...")
        self._add_interior_ramps(cfg)
        
        print("4. Adding entrance ramps...")
        self._add_stepped_entrances(cfg, tier_height)
    
    def _create_stepped_interior(self, cfg: Config, num_tiers: int, tier_height: float):
        """Create interior for stepped base."""
        mb_interior = MeshBuilder("Base_Interior")
        
        for tier in range(num_tiers):
            scale = 1.0 - (tier * 0.2)
            tier_width = (cfg.base_width - cfg.wall_thickness * 2) * scale
            tier_depth = (cfg.base_depth - cfg.wall_thickness * 2) * scale
            z = tier * tier_height + cfg.floor_thickness
            
            # Ring platform around atrium
            platform_width = (tier_width - cfg.atrium_width) / 2
            
            if platform_width > 3:
                # Create perimeter platforms
                # North
                mb_interior.add_platform(
                    0, tier_depth/2 - platform_width/2, z,
                    tier_width, platform_width, cfg.floor_thickness
                )
                # South
                mb_interior.add_platform(
                    0, -(tier_depth/2 - platform_width/2), z,
                    tier_width, platform_width, cfg.floor_thickness
                )
                # East
                mb_interior.add_platform(
                    tier_width/2 - platform_width/2, 0, z,
                    platform_width, cfg.atrium_depth, cfg.floor_thickness
                )
                # West
                mb_interior.add_platform(
                    -(tier_width/2 - platform_width/2), 0, z,
                    platform_width, cfg.atrium_depth, cfg.floor_thickness
                )
        
        interior_obj = mb_interior.finalize(self.collection)
        self._apply_material(interior_obj, "Floor", (0.35, 0.38, 0.4))
    
    def _add_stepped_entrances(self, cfg: Config, tier_height: float):
        """Add entrances for stepped base."""
        mb_entrance = MeshBuilder("Base_Entrances")
        
        # External ramp on first tier
        ramp_length = tier_height / math.tan(math.radians(25))
        
        mb_entrance.add_ramp(
            0, -(cfg.base_depth/2 + ramp_length), 0,
            0, -cfg.base_depth/2 + 4, tier_height,
            cfg.entrance_width, 1.0
        )
        
        mb_entrance.add_ramp(
            0, cfg.base_depth/2 + ramp_length, 0,
            0, cfg.base_depth/2 - 4, tier_height,
            cfg.entrance_width, 1.0
        )
        
        entrance_obj = mb_entrance.finalize(self.collection)
        self._apply_material(entrance_obj, "Entrance", (0.5, 0.45, 0.35))
    
    # =========================================================================
    # TOWER ON BASE STYLE
    # =========================================================================
    
    def _generate_tower_base(self):
        """Generate tower-on-base style."""
        cfg = self.cfg
        
        print("\n1. Creating base platform...")
        mb_base = MeshBuilder("Base_Platform")
        
        # Wide base platform
        base_height = cfg.base_height * 0.3
        mb_base.add_tapered_box(
            cfg.base_width, cfg.base_depth,
            cfg.base_width * 0.9, cfg.base_depth * 0.9,
            base_height,
            base_z=0
        )
        
        base_obj = mb_base.finalize(self.collection)
        self._apply_material(base_obj, "BasePlatform", (0.4, 0.42, 0.45))
        
        print("2. Creating tower...")
        mb_tower = MeshBuilder("Base_Tower")
        
        # Narrower tower on top
        tower_width = cfg.base_width * 0.5
        tower_depth = cfg.base_depth * 0.5
        tower_height = cfg.base_height * 0.7
        
        mb_tower.add_tapered_box(
            tower_width, tower_depth,
            tower_width * 0.85, tower_depth * 0.85,
            tower_height,
            base_z=base_height
        )
        
        tower_obj = mb_tower.finalize(self.collection)
        self._apply_material(tower_obj, "Tower", (0.5, 0.52, 0.55))
        
        print("3. Creating interior...")
        self._create_tower_interior(cfg, base_height, tower_width, tower_depth, tower_height)
        
        print("4. Creating entrances...")
        self._add_tower_entrances(cfg, base_height)
    
    def _create_tower_interior(self, cfg: Config, base_height: float,
                               tower_width: float, tower_depth: float, tower_height: float):
        """Create interior for tower base."""
        mb_interior = MeshBuilder("Base_Interior")
        
        # Base platform interior
        mb_interior.add_platform(0, 0, cfg.floor_thickness,
                                 cfg.base_width - cfg.wall_thickness * 2,
                                 cfg.base_depth - cfg.wall_thickness * 2,
                                 cfg.floor_thickness)
        
        # Tower levels
        tower_levels = 3
        level_height = tower_height / tower_levels
        
        for level in range(tower_levels):
            z = base_height + level * level_height + cfg.floor_thickness
            
            interior_w = tower_width - cfg.wall_thickness * 2
            interior_d = tower_depth - cfg.wall_thickness * 2
            
            # Perimeter platform with central opening
            platform_w = (interior_w - cfg.atrium_width * 0.6) / 2
            
            if platform_w > 2:
                mb_interior.add_platform(
                    0, interior_d/2 - platform_w/2, z,
                    interior_w, platform_w, cfg.floor_thickness
                )
                mb_interior.add_platform(
                    0, -(interior_d/2 - platform_w/2), z,
                    interior_w, platform_w, cfg.floor_thickness
                )
        
        interior_obj = mb_interior.finalize(self.collection)
        self._apply_material(interior_obj, "Floor", (0.35, 0.38, 0.4))
        
        # Tower ramps
        mb_ramps = MeshBuilder("Tower_Ramps")
        ramp_rise = level_height
        ramp_run = ramp_rise / math.tan(math.radians(cfg.ramp_angle))
        
        for level in range(tower_levels - 1):
            z_start = base_height + (level + 1) * level_height + cfg.floor_thickness
            z_end = z_start + ramp_rise
            
            side = 1 if level % 2 == 0 else -1
            mb_ramps.add_ramp(
                side * (cfg.atrium_width * 0.2), -ramp_run/2, z_start,
                side * (cfg.atrium_width * 0.2), ramp_run/2, z_end,
                cfg.ramp_width * 0.8
            )
        
        ramps_obj = mb_ramps.finalize(self.collection)
        self._apply_material(ramps_obj, "Ramp", (0.5, 0.45, 0.35))
    
    def _add_tower_entrances(self, cfg: Config, base_height: float):
        """Add entrances for tower base."""
        mb_entrance = MeshBuilder("Base_Entrances")
        
        # Ramps up to base platform
        ramp_length = base_height / math.tan(math.radians(20))
        
        mb_entrance.add_ramp(
            0, -(cfg.base_depth/2 + ramp_length), 0,
            0, -cfg.base_depth/2 + 2, base_height,
            cfg.entrance_width, 1.0
        )
        
        mb_entrance.add_ramp(
            0, cfg.base_depth/2 + ramp_length, 0,
            0, cfg.base_depth/2 - 2, base_height,
            cfg.entrance_width, 1.0
        )
        
        entrance_obj = mb_entrance.finalize(self.collection)
        self._apply_material(entrance_obj, "Entrance", (0.5, 0.45, 0.35))
    
    # =========================================================================
    # BUNKER STYLE
    # =========================================================================
    
    def _generate_bunker_base(self):
        """Generate low, wide bunker style."""
        cfg = self.cfg
        
        print("\n1. Creating bunker shell...")
        mb_exterior = MeshBuilder("Base_Exterior")
        
        # Wide, low profile
        bunker_height = cfg.base_height * 0.4
        
        mb_exterior.add_tapered_box(
            cfg.base_width * 1.2, cfg.base_depth * 1.2,
            cfg.base_width, cfg.base_depth,
            bunker_height,
            base_z=0
        )
        
        exterior_obj = mb_exterior.finalize(self.collection)
        self._apply_material(exterior_obj, "Exterior", (0.4, 0.42, 0.4))
        
        print("2. Creating interior...")
        mb_interior = MeshBuilder("Base_Interior")
        
        # Two level interior
        interior_w = cfg.base_width - cfg.wall_thickness * 2
        interior_d = cfg.base_depth - cfg.wall_thickness * 2
        
        # Ground floor
        mb_interior.add_platform(0, 0, cfg.floor_thickness,
                                 interior_w, interior_d, cfg.floor_thickness)
        
        # Upper balconies along walls
        balcony_z = bunker_height * 0.5
        balcony_width = 6
        
        mb_interior.add_platform(0, interior_d/2 - balcony_width/2, balcony_z,
                                 interior_w * 0.8, balcony_width, cfg.floor_thickness)
        mb_interior.add_platform(0, -(interior_d/2 - balcony_width/2), balcony_z,
                                 interior_w * 0.8, balcony_width, cfg.floor_thickness)
        
        interior_obj = mb_interior.finalize(self.collection)
        self._apply_material(interior_obj, "Floor", (0.35, 0.38, 0.4))
        
        print("3. Creating ramps...")
        mb_ramps = MeshBuilder("Base_Ramps")
        
        # Ramps to balconies
        ramp_rise = balcony_z - cfg.floor_thickness
        ramp_run = ramp_rise / math.tan(math.radians(cfg.ramp_angle))
        
        mb_ramps.add_ramp(
            interior_w/2 - 4, interior_d/2 - balcony_width - ramp_run, cfg.floor_thickness,
            interior_w/2 - 4, interior_d/2 - balcony_width, balcony_z,
            cfg.ramp_width
        )
        
        mb_ramps.add_ramp(
            -(interior_w/2 - 4), -(interior_d/2 - balcony_width - ramp_run), cfg.floor_thickness,
            -(interior_w/2 - 4), -(interior_d/2 - balcony_width), balcony_z,
            cfg.ramp_width
        )
        
        ramps_obj = mb_ramps.finalize(self.collection)
        self._apply_material(ramps_obj, "Ramp", (0.5, 0.45, 0.35))
        
        print("4. Creating entrances...")
        mb_entrance = MeshBuilder("Base_Entrances")
        
        # Ground level entrances
        entrance_y = cfg.base_depth * 0.6
        
        mb_entrance.add_platform(0, -entrance_y, cfg.floor_thickness,
                                 cfg.entrance_width + 4, 8, cfg.floor_thickness)
        mb_entrance.add_platform(0, entrance_y, cfg.floor_thickness,
                                 cfg.entrance_width + 4, 8, cfg.floor_thickness)
        
        entrance_obj = mb_entrance.finalize(self.collection)
        self._apply_material(entrance_obj, "Entrance", (0.5, 0.45, 0.35))
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def _apply_material(self, obj: bpy.types.Object, name: str, color: Tuple[float, float, float]):
        """Apply or create a material."""
        mat_name = f"FPSZ_{name}"
        mat = bpy.data.materials.get(mat_name)
        
        if not mat:
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes.get('Principled BSDF')
            if bsdf:
                bsdf.inputs['Base Color'].default_value = (*color, 1.0)
                bsdf.inputs['Roughness'].default_value = 0.7
        
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)


# =============================================================================
# MAIN
# =============================================================================

def generate_base(style: str = "pyramid", seed: int = None, **kwargs):
    """
    Generate a Tribes-style base.
    
    Args:
        style: "pyramid", "stepped", "tower", or "bunker"
        seed: Random seed for reproducibility
        **kwargs: Override any Config parameter
    """
    cfg = Config()
    
    # Set style
    style_map = {
        "pyramid": BaseStyle.PYRAMID,
        "stepped": BaseStyle.STEPPED_PYRAMID,
        "tower": BaseStyle.TOWER_ON_BASE,
        "bunker": BaseStyle.BUNKER,
    }
    cfg.style = style_map.get(style.lower(), BaseStyle.PYRAMID)
    
    # Set seed
    if seed is not None:
        cfg.seed = seed
    else:
        import time
        cfg.seed = int(time.time()) % 10000
    
    # Apply any overrides
    for key, value in kwargs.items():
        if hasattr(cfg, key):
            setattr(cfg, key, value)
    
    print(f"Using seed: {cfg.seed}")
    
    generator = TribesBaseGenerator(cfg)
    generator.generate()


if __name__ == "__main__":
    # Generate random style
    import time
    seed = int(time.time()) % 10000
    
    styles = ["pyramid", "stepped", "tower", "bunker"]
    style = random.choice(styles)
    
    print(f"\nGenerating {style} base...")
    generate_base(style=style, seed=seed)
