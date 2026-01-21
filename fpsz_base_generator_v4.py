"""
FPSZ Procedural Base Generator v5 - Complex Interiors
======================================================
Keeps the tapered exterior forms from v4 but generates
much more complex interior spaces:
- Multiple rooms at each level
- Corridors connecting rooms
- Side chambers and alcoves
- Equipment/objective rooms
- Multiple routes through the base

Run in Blender 4.x with Alt+P
"""

import bpy
import bmesh
from mathutils import Vector
import math
import random
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


# =============================================================================
# CONFIGURATION
# =============================================================================

class BaseStyle(Enum):
    PYRAMID = "pyramid"
    STEPPED_PYRAMID = "stepped"
    TOWER_ON_BASE = "tower"


class RoomType(Enum):
    MAIN_HALL = "main_hall"          # Large central space
    CORRIDOR = "corridor"             # Connecting passage
    SIDE_CHAMBER = "side_chamber"     # Medium room off main areas
    EQUIPMENT_ROOM = "equipment"      # Small equipment/objective room
    STAIRWELL = "stairwell"           # Vertical connection space
    BALCONY = "balcony"               # Overlook area


@dataclass
class Room:
    """Interior room definition."""
    id: int
    room_type: RoomType
    x: float
    y: float
    z: float
    width: float
    depth: float
    height: float
    level: int
    connections: List[int] = field(default_factory=list)


@dataclass
class Config:
    """Base generation configuration."""
    
    # Overall size
    base_width: float = 70.0
    base_depth: float = 70.0
    base_height: float = 55.0
    
    # Taper
    wall_taper: float = 0.25
    
    # Structure
    wall_thickness: float = 3.0
    floor_thickness: float = 1.0
    interior_wall_thickness: float = 1.5
    
    # Levels
    num_levels: int = 4
    level_height: float = 12.0
    
    # Rooms per level
    rooms_per_level: int = 4
    
    # Room sizes (from Tribes analysis)
    main_hall_size: Tuple[float, float] = (24.0, 24.0)
    corridor_width: float = 8.0
    corridor_length: float = 16.0
    side_chamber_size: Tuple[float, float] = (14.0, 12.0)
    equipment_room_size: Tuple[float, float] = (8.0, 8.0)
    
    # Doorways
    doorway_width: float = 6.0
    doorway_height: float = 8.0
    
    # Ramps
    ramp_width: float = 6.0
    ramp_angle: float = 28.0
    
    # Entrances
    num_entrances: int = 2
    entrance_width: float = 10.0
    entrance_height: float = 10.0
    
    # Style
    style: BaseStyle = BaseStyle.PYRAMID
    
    # Seed
    seed: int = 42


# =============================================================================
# INTERIOR LAYOUT GENERATOR
# =============================================================================

class InteriorLayout:
    """Generates complex interior room layouts."""
    
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.rooms: List[Room] = []
        self.room_id_counter = 0
        self.rng = random.Random(cfg.seed)
    
    def generate_layout(self) -> List[Room]:
        """Generate complete interior layout."""
        
        for level in range(self.cfg.num_levels):
            self._generate_level(level)
        
        self._create_vertical_connections()
        
        return self.rooms
    
    def _generate_level(self, level: int):
        """Generate rooms for one level."""
        z = level * self.cfg.level_height + self.cfg.floor_thickness
        
        # Calculate available interior space at this level
        height_ratio = z / self.cfg.base_height
        taper = self.cfg.base_height * self.cfg.wall_taper * height_ratio
        
        available_width = self.cfg.base_width - self.cfg.wall_thickness * 2 - taper * 2
        available_depth = self.cfg.base_depth - self.cfg.wall_thickness * 2 - taper * 2
        
        if level == 0:
            # Ground floor: main hall + side rooms + corridors
            self._generate_ground_floor(z, available_width, available_depth, level)
        elif level == self.cfg.num_levels - 1:
            # Top floor: smaller control room + balconies
            self._generate_top_floor(z, available_width, available_depth, level)
        else:
            # Middle floors: varied room layouts
            self._generate_middle_floor(z, available_width, available_depth, level)
    
    def _generate_ground_floor(self, z: float, avail_w: float, avail_d: float, level: int):
        """Ground floor with main hall and branching corridors."""
        
        # Central main hall
        hall_w, hall_d = self.cfg.main_hall_size
        main_hall = self._add_room(
            RoomType.MAIN_HALL, 0, 0, z,
            hall_w, hall_d, self.cfg.level_height - 1,
            level
        )
        
        # North corridor
        corridor_n = self._add_room(
            RoomType.CORRIDOR, 0, hall_d/2 + self.cfg.corridor_length/2, z,
            self.cfg.corridor_width, self.cfg.corridor_length, self.cfg.level_height - 1,
            level
        )
        main_hall.connections.append(corridor_n.id)
        corridor_n.connections.append(main_hall.id)
        
        # South corridor
        corridor_s = self._add_room(
            RoomType.CORRIDOR, 0, -(hall_d/2 + self.cfg.corridor_length/2), z,
            self.cfg.corridor_width, self.cfg.corridor_length, self.cfg.level_height - 1,
            level
        )
        main_hall.connections.append(corridor_s.id)
        corridor_s.connections.append(main_hall.id)
        
        # East side chamber
        chamber_e = self._add_room(
            RoomType.SIDE_CHAMBER, 
            hall_w/2 + self.cfg.side_chamber_size[0]/2 + 2, 0, z,
            self.cfg.side_chamber_size[0], self.cfg.side_chamber_size[1], 
            self.cfg.level_height - 1,
            level
        )
        main_hall.connections.append(chamber_e.id)
        chamber_e.connections.append(main_hall.id)
        
        # West side chamber
        chamber_w = self._add_room(
            RoomType.SIDE_CHAMBER,
            -(hall_w/2 + self.cfg.side_chamber_size[0]/2 + 2), 0, z,
            self.cfg.side_chamber_size[0], self.cfg.side_chamber_size[1],
            self.cfg.level_height - 1,
            level
        )
        main_hall.connections.append(chamber_w.id)
        chamber_w.connections.append(main_hall.id)
        
        # Equipment rooms at corridor ends
        equip_n = self._add_room(
            RoomType.EQUIPMENT_ROOM,
            0, hall_d/2 + self.cfg.corridor_length + self.cfg.equipment_room_size[1]/2 + 1, z,
            self.cfg.equipment_room_size[0], self.cfg.equipment_room_size[1],
            self.cfg.level_height - 2,
            level
        )
        corridor_n.connections.append(equip_n.id)
        equip_n.connections.append(corridor_n.id)
        
        equip_s = self._add_room(
            RoomType.EQUIPMENT_ROOM,
            0, -(hall_d/2 + self.cfg.corridor_length + self.cfg.equipment_room_size[1]/2 + 1), z,
            self.cfg.equipment_room_size[0], self.cfg.equipment_room_size[1],
            self.cfg.level_height - 2,
            level
        )
        corridor_s.connections.append(equip_s.id)
        equip_s.connections.append(corridor_s.id)
        
        # Corner equipment rooms
        corner_offset = hall_w/2 + 8
        for cx, cy in [(corner_offset, corner_offset), (corner_offset, -corner_offset),
                       (-corner_offset, corner_offset), (-corner_offset, -corner_offset)]:
            if abs(cx) < avail_w/2 - 4 and abs(cy) < avail_d/2 - 4:
                corner_room = self._add_room(
                    RoomType.EQUIPMENT_ROOM, cx, cy, z,
                    self.cfg.equipment_room_size[0] * 0.9,
                    self.cfg.equipment_room_size[1] * 0.9,
                    self.cfg.level_height - 2,
                    level
                )
                # Connect to nearest chamber
                if cx > 0:
                    chamber_e.connections.append(corner_room.id)
                    corner_room.connections.append(chamber_e.id)
                else:
                    chamber_w.connections.append(corner_room.id)
                    corner_room.connections.append(chamber_w.id)
    
    def _generate_middle_floor(self, z: float, avail_w: float, avail_d: float, level: int):
        """Middle floors with ring corridor and side rooms."""
        
        # Central open area (atrium void - no floor here)
        atrium_size = min(16, avail_w * 0.3)
        
        # Ring corridor around atrium
        ring_width = 7
        ring_inner = atrium_size / 2 + 1
        ring_outer = ring_inner + ring_width
        
        # Four corridor segments forming a ring
        # North segment
        corridor_n = self._add_room(
            RoomType.CORRIDOR, 0, ring_inner + ring_width/2, z,
            ring_outer * 1.8, ring_width, self.cfg.level_height - 1,
            level
        )
        
        # South segment
        corridor_s = self._add_room(
            RoomType.CORRIDOR, 0, -(ring_inner + ring_width/2), z,
            ring_outer * 1.8, ring_width, self.cfg.level_height - 1,
            level
        )
        
        # East segment
        corridor_e = self._add_room(
            RoomType.CORRIDOR, ring_inner + ring_width/2, 0, z,
            ring_width, ring_outer * 1.8, self.cfg.level_height - 1,
            level
        )
        
        # West segment
        corridor_w = self._add_room(
            RoomType.CORRIDOR, -(ring_inner + ring_width/2), 0, z,
            ring_width, ring_outer * 1.8, self.cfg.level_height - 1,
            level
        )
        
        # Connect ring segments
        corridor_n.connections.extend([corridor_e.id, corridor_w.id])
        corridor_s.connections.extend([corridor_e.id, corridor_w.id])
        corridor_e.connections.extend([corridor_n.id, corridor_s.id])
        corridor_w.connections.extend([corridor_n.id, corridor_s.id])
        
        # Side chambers off the ring
        chamber_offset = ring_outer + self.cfg.side_chamber_size[0]/2 + 2
        
        if chamber_offset < avail_w/2 - 3:
            # North-East chamber
            ch_ne = self._add_room(
                RoomType.SIDE_CHAMBER, chamber_offset * 0.7, chamber_offset * 0.7, z,
                self.cfg.side_chamber_size[0] * 0.85, self.cfg.side_chamber_size[1] * 0.85,
                self.cfg.level_height - 1, level
            )
            corridor_n.connections.append(ch_ne.id)
            corridor_e.connections.append(ch_ne.id)
            ch_ne.connections.extend([corridor_n.id, corridor_e.id])
            
            # North-West chamber
            ch_nw = self._add_room(
                RoomType.SIDE_CHAMBER, -chamber_offset * 0.7, chamber_offset * 0.7, z,
                self.cfg.side_chamber_size[0] * 0.85, self.cfg.side_chamber_size[1] * 0.85,
                self.cfg.level_height - 1, level
            )
            corridor_n.connections.append(ch_nw.id)
            corridor_w.connections.append(ch_nw.id)
            ch_nw.connections.extend([corridor_n.id, corridor_w.id])
            
            # South-East chamber
            ch_se = self._add_room(
                RoomType.SIDE_CHAMBER, chamber_offset * 0.7, -chamber_offset * 0.7, z,
                self.cfg.side_chamber_size[0] * 0.85, self.cfg.side_chamber_size[1] * 0.85,
                self.cfg.level_height - 1, level
            )
            corridor_s.connections.append(ch_se.id)
            corridor_e.connections.append(ch_se.id)
            ch_se.connections.extend([corridor_s.id, corridor_e.id])
            
            # South-West chamber
            ch_sw = self._add_room(
                RoomType.SIDE_CHAMBER, -chamber_offset * 0.7, -chamber_offset * 0.7, z,
                self.cfg.side_chamber_size[0] * 0.85, self.cfg.side_chamber_size[1] * 0.85,
                self.cfg.level_height - 1, level
            )
            corridor_s.connections.append(ch_sw.id)
            corridor_w.connections.append(ch_sw.id)
            ch_sw.connections.extend([corridor_s.id, corridor_w.id])
    
    def _generate_top_floor(self, z: float, avail_w: float, avail_d: float, level: int):
        """Top floor with command room and balconies."""
        
        # Central command/objective room
        cmd_size = min(18, avail_w * 0.5)
        command_room = self._add_room(
            RoomType.MAIN_HALL, 0, 0, z,
            cmd_size, cmd_size, self.cfg.level_height,
            level
        )
        
        # Balconies extending outward
        balcony_width = 5
        balcony_length = 12
        
        # North balcony
        if cmd_size/2 + balcony_length < avail_d/2 - 2:
            bal_n = self._add_room(
                RoomType.BALCONY, 0, cmd_size/2 + balcony_length/2, z,
                balcony_width * 1.5, balcony_length, self.cfg.level_height,
                level
            )
            command_room.connections.append(bal_n.id)
            bal_n.connections.append(command_room.id)
        
        # South balcony
        if cmd_size/2 + balcony_length < avail_d/2 - 2:
            bal_s = self._add_room(
                RoomType.BALCONY, 0, -(cmd_size/2 + balcony_length/2), z,
                balcony_width * 1.5, balcony_length, self.cfg.level_height,
                level
            )
            command_room.connections.append(bal_s.id)
            bal_s.connections.append(command_room.id)
        
        # Side alcoves
        alcove_offset = cmd_size/2 + 6
        if alcove_offset < avail_w/2 - 4:
            alcove_e = self._add_room(
                RoomType.EQUIPMENT_ROOM, alcove_offset, 0, z,
                8, 10, self.cfg.level_height - 1,
                level
            )
            command_room.connections.append(alcove_e.id)
            alcove_e.connections.append(command_room.id)
            
            alcove_w = self._add_room(
                RoomType.EQUIPMENT_ROOM, -alcove_offset, 0, z,
                8, 10, self.cfg.level_height - 1,
                level
            )
            command_room.connections.append(alcove_w.id)
            alcove_w.connections.append(command_room.id)
    
    def _create_vertical_connections(self):
        """Mark rooms that should have vertical connections (ramps/stairs)."""
        # Find rooms at similar XY positions on adjacent levels
        for room in self.rooms:
            for other in self.rooms:
                if other.level == room.level + 1:
                    # Check if roughly above
                    dx = abs(room.x - other.x)
                    dy = abs(room.y - other.y)
                    if dx < 8 and dy < 8:
                        if other.id not in room.connections:
                            room.connections.append(other.id)
                        if room.id not in other.connections:
                            other.connections.append(room.id)
    
    def _add_room(self, room_type: RoomType, x: float, y: float, z: float,
                  width: float, depth: float, height: float, level: int) -> Room:
        """Add a room to the layout."""
        room = Room(
            id=self.room_id_counter,
            room_type=room_type,
            x=x, y=y, z=z,
            width=width, depth=depth, height=height,
            level=level
        )
        self.rooms.append(room)
        self.room_id_counter += 1
        return room


# =============================================================================
# MESH BUILDER
# =============================================================================

class MeshBuilder:
    """Builds geometry with hollow rooms."""
    
    def __init__(self, name: str):
        self.name = name
        self.bm = bmesh.new()
    
    def add_tapered_shell(self, 
                          base_w: float, base_d: float,
                          top_w: float, top_d: float,
                          height: float,
                          wall_thick: float,
                          base_z: float = 0.0):
        """Create a hollow tapered shell (exterior walls only)."""
        
        # Outer shell
        self._add_tapered_box_faces(
            base_w, base_d, top_w, top_d, height, base_z, invert=False
        )
        
        # Inner shell (slightly smaller)
        inner_base_w = base_w - wall_thick * 2
        inner_base_d = base_d - wall_thick * 2
        inner_top_w = top_w - wall_thick * 2
        inner_top_d = top_d - wall_thick * 2
        
        self._add_tapered_box_faces(
            inner_base_w, inner_base_d, 
            inner_top_w, inner_top_d,
            height, base_z, invert=True
        )
    
    def _add_tapered_box_faces(self, base_w, base_d, top_w, top_d, height, base_z, invert=False):
        """Add faces for a tapered box."""
        bw, bd = base_w / 2, base_d / 2
        tw, td = top_w / 2, top_d / 2
        z0, z1 = base_z, base_z + height
        
        v_bottom = [
            self.bm.verts.new((-bw, -bd, z0)),
            self.bm.verts.new((bw, -bd, z0)),
            self.bm.verts.new((bw, bd, z0)),
            self.bm.verts.new((-bw, bd, z0)),
        ]
        
        v_top = [
            self.bm.verts.new((-tw, -td, z1)),
            self.bm.verts.new((tw, -td, z1)),
            self.bm.verts.new((tw, td, z1)),
            self.bm.verts.new((-tw, td, z1)),
        ]
        
        if invert:
            self.bm.faces.new(v_bottom)
            self.bm.faces.new(v_top[::-1])
            for i in range(4):
                ni = (i + 1) % 4
                self.bm.faces.new([v_top[i], v_top[ni], v_bottom[ni], v_bottom[i]])
        else:
            self.bm.faces.new(v_bottom[::-1])
            self.bm.faces.new(v_top)
            for i in range(4):
                ni = (i + 1) % 4
                self.bm.faces.new([v_bottom[i], v_bottom[ni], v_top[ni], v_top[i]])
    
    def add_room_geometry(self, room: Room, wall_thick: float = 1.0):
        """
        Create floor and walls for a room.
        Rooms are hollow boxes with no ceiling (open to above).
        """
        x, y, z = room.x, room.y, room.z
        w, d, h = room.width, room.depth, room.height
        hw, hd = w / 2, d / 2
        
        # Floor
        self._add_floor(x, y, z, w, d, 1.0)
        
        # Walls (partial, with gaps for doorways)
        # For simplicity, create corner pillars and partial walls
        pillar_size = wall_thick * 2
        
        # Corner pillars
        corners = [
            (x - hw + pillar_size/2, y - hd + pillar_size/2),
            (x + hw - pillar_size/2, y - hd + pillar_size/2),
            (x + hw - pillar_size/2, y + hd - pillar_size/2),
            (x - hw + pillar_size/2, y + hd - pillar_size/2),
        ]
        
        for cx, cy in corners:
            self._add_box(cx, cy, z, pillar_size, pillar_size, h)
        
        # Wall segments between pillars (with doorway gaps)
        doorway_width = 6.0
        
        # North and South walls
        wall_len = w - pillar_size * 2
        if wall_len > doorway_width + 4:
            seg_len = (wall_len - doorway_width) / 2
            # North wall - two segments
            self._add_box(x - wall_len/2 + seg_len/2, y + hd - wall_thick/2, z,
                         seg_len, wall_thick, h)
            self._add_box(x + wall_len/2 - seg_len/2, y + hd - wall_thick/2, z,
                         seg_len, wall_thick, h)
            # South wall - two segments
            self._add_box(x - wall_len/2 + seg_len/2, y - hd + wall_thick/2, z,
                         seg_len, wall_thick, h)
            self._add_box(x + wall_len/2 - seg_len/2, y - hd + wall_thick/2, z,
                         seg_len, wall_thick, h)
        
        # East and West walls
        wall_len = d - pillar_size * 2
        if wall_len > doorway_width + 4:
            seg_len = (wall_len - doorway_width) / 2
            # East wall
            self._add_box(x + hw - wall_thick/2, y - wall_len/2 + seg_len/2, z,
                         wall_thick, seg_len, h)
            self._add_box(x + hw - wall_thick/2, y + wall_len/2 - seg_len/2, z,
                         wall_thick, seg_len, h)
            # West wall
            self._add_box(x - hw + wall_thick/2, y - wall_len/2 + seg_len/2, z,
                         wall_thick, seg_len, h)
            self._add_box(x - hw + wall_thick/2, y + wall_len/2 - seg_len/2, z,
                         wall_thick, seg_len, h)
    
    def add_corridor_geometry(self, room: Room, wall_thick: float = 1.0):
        """Create corridor with floor and side walls."""
        x, y, z = room.x, room.y, room.z
        w, d, h = room.width, room.depth, room.height
        hw, hd = w / 2, d / 2
        
        # Floor
        self._add_floor(x, y, z, w, d, 1.0)
        
        # Determine corridor orientation
        if w > d:
            # East-West corridor - walls on north and south
            self._add_box(x, y + hd - wall_thick/2, z, w, wall_thick, h)
            self._add_box(x, y - hd + wall_thick/2, z, w, wall_thick, h)
        else:
            # North-South corridor - walls on east and west
            self._add_box(x + hw - wall_thick/2, y, z, wall_thick, d, h)
            self._add_box(x - hw + wall_thick/2, y, z, wall_thick, d, h)
    
    def add_platform(self, x: float, y: float, z: float, w: float, d: float, thick: float = 1.0):
        """Add a simple platform/floor."""
        self._add_floor(x, y, z, w, d, thick)
    
    def add_ramp(self, x1: float, y1: float, z1: float,
                 x2: float, y2: float, z2: float,
                 width: float, thickness: float = 0.5):
        """Add a ramp between two points."""
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length < 0.01:
            return
        
        # Perpendicular
        px, py = -dy / length * width / 2, dx / length * width / 2
        
        # Top surface
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
    
    def _add_floor(self, x: float, y: float, z: float, w: float, d: float, thick: float):
        """Add a floor slab."""
        hw, hd = w / 2, d / 2
        
        v_top = [
            self.bm.verts.new((x - hw, y - hd, z)),
            self.bm.verts.new((x + hw, y - hd, z)),
            self.bm.verts.new((x + hw, y + hd, z)),
            self.bm.verts.new((x - hw, y + hd, z)),
        ]
        self.bm.faces.new(v_top)
        
        v_bot = [
            self.bm.verts.new((x - hw, y + hd, z - thick)),
            self.bm.verts.new((x + hw, y + hd, z - thick)),
            self.bm.verts.new((x + hw, y - hd, z - thick)),
            self.bm.verts.new((x - hw, y - hd, z - thick)),
        ]
        self.bm.faces.new(v_bot)
        
        # Edges
        for i in range(4):
            ni = (i + 1) % 4
            self.bm.faces.new([v_top[i], v_top[ni], v_bot[3-ni], v_bot[3-i]])
    
    def _add_box(self, x: float, y: float, z: float, w: float, d: float, h: float):
        """Add a solid box."""
        hw, hd = w / 2, d / 2
        
        v_bot = [
            self.bm.verts.new((x - hw, y - hd, z)),
            self.bm.verts.new((x + hw, y - hd, z)),
            self.bm.verts.new((x + hw, y + hd, z)),
            self.bm.verts.new((x - hw, y + hd, z)),
        ]
        
        v_top = [
            self.bm.verts.new((x - hw, y - hd, z + h)),
            self.bm.verts.new((x + hw, y - hd, z + h)),
            self.bm.verts.new((x + hw, y + hd, z + h)),
            self.bm.verts.new((x - hw, y + hd, z + h)),
        ]
        
        self.bm.faces.new(v_bot[::-1])
        self.bm.faces.new(v_top)
        for i in range(4):
            ni = (i + 1) % 4
            self.bm.faces.new([v_bot[i], v_bot[ni], v_top[ni], v_top[i]])
    
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
# BASE GENERATOR
# =============================================================================

class TribesBaseGenerator:
    """Generates complete Tribes-style bases."""
    
    def __init__(self, cfg: Config = None):
        self.cfg = cfg or Config()
        self.collection = None
        self.rooms: List[Room] = []
        random.seed(self.cfg.seed)
    
    def generate(self):
        """Generate the complete base."""
        print("\n" + "="*60)
        print("FPSZ BASE GENERATOR v5 - Complex Interiors")
        print(f"Style: {self.cfg.style.value}")
        print(f"Seed: {self.cfg.seed}")
        print("="*60)
        
        self._setup_collection()
        
        # Generate interior layout
        print("\n1. Generating interior layout...")
        layout_gen = InteriorLayout(self.cfg)
        self.rooms = layout_gen.generate_layout()
        print(f"   Created {len(self.rooms)} rooms across {self.cfg.num_levels} levels")
        
        # Build exterior shell
        print("\n2. Building exterior shell...")
        self._build_exterior()
        
        # Build interior rooms
        print("\n3. Building interior rooms...")
        self._build_interior()
        
        # Build ramps
        print("\n4. Building ramps...")
        self._build_ramps()
        
        # Build entrances
        print("\n5. Building entrances...")
        self._build_entrances()
        
        print("\n" + "="*60)
        print("Generation complete!")
        print(f"Total rooms: {len(self.rooms)}")
        
        # Room breakdown
        from collections import Counter
        room_counts = Counter(r.room_type.value for r in self.rooms)
        for rtype, count in room_counts.items():
            print(f"  {rtype}: {count}")
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
        """Build the exterior shell."""
        cfg = self.cfg
        mb = MeshBuilder("Base_Exterior")
        
        taper_amount = cfg.base_height * cfg.wall_taper
        top_w = cfg.base_width - taper_amount * 2
        top_d = cfg.base_depth - taper_amount * 2
        
        if cfg.style == BaseStyle.PYRAMID:
            mb.add_tapered_shell(
                cfg.base_width, cfg.base_depth,
                top_w, top_d,
                cfg.base_height,
                cfg.wall_thickness
            )
        
        elif cfg.style == BaseStyle.STEPPED_PYRAMID:
            # Multiple tiers
            num_tiers = 4
            tier_h = cfg.base_height / num_tiers
            
            for tier in range(num_tiers):
                scale = 1.0 - tier * 0.18
                tier_w = cfg.base_width * scale
                tier_d = cfg.base_depth * scale
                top_scale = scale - 0.04
                tier_top_w = cfg.base_width * top_scale
                tier_top_d = cfg.base_depth * top_scale
                
                mb.add_tapered_shell(
                    tier_w, tier_d,
                    tier_top_w, tier_top_d,
                    tier_h,
                    cfg.wall_thickness,
                    base_z=tier * tier_h
                )
        
        elif cfg.style == BaseStyle.TOWER_ON_BASE:
            # Wide base
            base_h = cfg.base_height * 0.35
            mb.add_tapered_shell(
                cfg.base_width * 1.2, cfg.base_depth * 1.2,
                cfg.base_width * 1.1, cfg.base_depth * 1.1,
                base_h,
                cfg.wall_thickness
            )
            # Tower
            tower_h = cfg.base_height * 0.65
            mb.add_tapered_shell(
                cfg.base_width * 0.6, cfg.base_depth * 0.6,
                cfg.base_width * 0.5, cfg.base_depth * 0.5,
                tower_h,
                cfg.wall_thickness,
                base_z=base_h
            )
        
        obj = mb.finalize(self.collection)
        self._apply_material(obj, "Exterior", (0.42, 0.44, 0.47))
    
    def _build_interior(self):
        """Build interior room geometry."""
        cfg = self.cfg
        
        # Group rooms by type for separate objects
        mb_floors = MeshBuilder("Base_Floors")
        mb_walls = MeshBuilder("Base_Walls")
        
        for room in self.rooms:
            if room.room_type == RoomType.CORRIDOR:
                mb_floors.add_corridor_geometry(room, cfg.interior_wall_thickness)
            elif room.room_type == RoomType.BALCONY:
                # Balconies are just platforms
                mb_floors.add_platform(room.x, room.y, room.z, room.width, room.depth, 1.0)
            else:
                mb_floors.add_room_geometry(room, cfg.interior_wall_thickness)
        
        floor_obj = mb_floors.finalize(self.collection)
        self._apply_material(floor_obj, "Floor", (0.35, 0.37, 0.4))
    
    def _build_ramps(self):
        """Build ramps connecting levels."""
        cfg = self.cfg
        mb = MeshBuilder("Base_Ramps")
        
        ramp_rise = cfg.level_height
        ramp_run = ramp_rise / math.tan(math.radians(cfg.ramp_angle))
        
        # Find main halls/corridors on each level for ramp placement
        rooms_by_level = {}
        for room in self.rooms:
            if room.level not in rooms_by_level:
                rooms_by_level[room.level] = []
            rooms_by_level[room.level].append(room)
        
        # Place ramps between levels
        for level in range(cfg.num_levels - 1):
            z_start = (level + 1) * cfg.level_height + cfg.floor_thickness
            z_end = z_start + ramp_rise
            
            # Alternate ramp positions for variety
            if level % 4 == 0:
                # East side, going north
                x = 12
                y_start, y_end = -ramp_run/2, ramp_run/2
            elif level % 4 == 1:
                # West side, going south
                x = -12
                y_start, y_end = ramp_run/2, -ramp_run/2
            elif level % 4 == 2:
                # North side, going east
                x_start, x_end = -ramp_run/2, ramp_run/2
                y = 12
                mb.add_ramp(x_start, y, z_start, x_end, y, z_end, cfg.ramp_width)
                continue
            else:
                # South side, going west
                x_start, x_end = ramp_run/2, -ramp_run/2
                y = -12
                mb.add_ramp(x_start, y, z_start, x_end, y, z_end, cfg.ramp_width)
                continue
            
            mb.add_ramp(x, y_start, z_start, x, y_end, z_end, cfg.ramp_width)
        
        obj = mb.finalize(self.collection)
        self._apply_material(obj, "Ramp", (0.48, 0.43, 0.35))
    
    def _build_entrances(self):
        """Build entrance ramps."""
        cfg = self.cfg
        mb = MeshBuilder("Base_Entrances")
        
        # Entrance height
        entrance_z = cfg.level_height * 0.4
        
        # Calculate wall position
        taper_at_entrance = cfg.base_height * cfg.wall_taper * (entrance_z / cfg.base_height)
        wall_offset = cfg.base_depth / 2 - taper_at_entrance
        
        # Ramp length
        ramp_len = entrance_z / math.tan(math.radians(22))
        
        # South entrance
        mb.add_ramp(
            0, -(wall_offset + ramp_len + 2), 0,
            0, -wall_offset + 4, entrance_z,
            cfg.entrance_width, 1.0
        )
        
        # Landing platform
        mb.add_platform(0, -wall_offset + 6, entrance_z, cfg.entrance_width + 6, 8, 1.0)
        
        # North entrance
        mb.add_ramp(
            0, wall_offset + ramp_len + 2, 0,
            0, wall_offset - 4, entrance_z,
            cfg.entrance_width, 1.0
        )
        mb.add_platform(0, wall_offset - 6, entrance_z, cfg.entrance_width + 6, 8, 1.0)
        
        # Optional side entrances
        if cfg.num_entrances > 2:
            side_offset = cfg.base_width / 2 - taper_at_entrance
            
            # East
            mb.add_ramp(
                side_offset + ramp_len + 2, 0, 0,
                side_offset - 4, 0, entrance_z,
                cfg.entrance_width * 0.8, 1.0
            )
            
            # West
            mb.add_ramp(
                -(side_offset + ramp_len + 2), 0, 0,
                -(side_offset - 4), 0, entrance_z,
                cfg.entrance_width * 0.8, 1.0
            )
        
        obj = mb.finalize(self.collection)
        self._apply_material(obj, "Entrance", (0.48, 0.43, 0.35))
    
    def _apply_material(self, obj: bpy.types.Object, name: str, color: Tuple[float, float, float]):
        """Apply material to object."""
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

def generate_base(style: str = "pyramid", seed: int = None, num_levels: int = 4, **kwargs):
    """
    Generate a Tribes-style base.
    
    Args:
        style: "pyramid", "stepped", or "tower"
        seed: Random seed (None for random)
        num_levels: Number of interior levels (2-6)
        **kwargs: Override any Config parameter
    """
    cfg = Config()
    
    # Style
    style_map = {
        "pyramid": BaseStyle.PYRAMID,
        "stepped": BaseStyle.STEPPED_PYRAMID,
        "tower": BaseStyle.TOWER_ON_BASE,
    }
    cfg.style = style_map.get(style.lower(), BaseStyle.PYRAMID)
    
    # Seed
    if seed is not None:
        cfg.seed = seed
    else:
        import time
        cfg.seed = int(time.time()) % 100000
    
    # Levels
    cfg.num_levels = max(2, min(6, num_levels))
    cfg.base_height = cfg.num_levels * cfg.level_height + 8
    
    # Overrides
    for key, value in kwargs.items():
        if hasattr(cfg, key):
            setattr(cfg, key, value)
    
    generator = TribesBaseGenerator(cfg)
    generator.generate()


def quick_generate():
    """Quick generation with random settings."""
    import time
    seed = int(time.time()) % 100000
    styles = ["pyramid", "stepped", "tower"]
    style = random.choice(styles)
    levels = random.randint(3, 5)
    
    print(f"\nQuick generate: {style}, {levels} levels, seed={seed}")
    generate_base(style=style, seed=seed, num_levels=levels)


if __name__ == "__main__":
    # Generate a pyramid base with 4 levels
    generate_base(style="pyramid", seed=12345, num_levels=4)
    
    # Or try these:
    # generate_base(style="stepped", seed=54321, num_levels=5)
    # generate_base(style="tower", seed=11111, num_levels=4)
    # quick_generate()  # Random style and levels
