#!/usr/bin/env python3
"""
Test script to debug the Mars WFC terrain generator
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from blender.terrain_generator import generate_layers, create_variants
from blender.tile import WFCTile
import random

def create_test_tiles():
    """Create some simple test tiles to see if the basic WFC logic works"""
    
    # Create a simple flat ground tile that can connect to anything
    ground_tile = WFCTile(
        name="ground",
        sockets={
            "UP": {"ground"},
            "DOWN": {"ground"},
            "NORTH": {"*"},  # Wildcard - connects to anything
            "SOUTH": {"*"},
            "EAST": {"*"},
            "WEST": {"*"}
        },
        weight=1.0,
        allow_rot=False
    )
    
    # Create a slope tile that can connect to ground and other slopes
    slope_tile = WFCTile(
        name="slope",
        sockets={
            "UP": {"ground"},
            "DOWN": {"ground"},
            "NORTH": {"slope_N", "ground"},  # Can connect to slopes or ground
            "SOUTH": {"slope_S", "ground"},
            "EAST": {"slope_E", "ground"},
            "WEST": {"slope_W", "ground"}
        },
        weight=1.0,
        allow_rot=True
    )
    
    # Create an air tile for the top
    air_tile = WFCTile(
        name="air",
        sockets={
            "UP": {"air"},
            "DOWN": {"ground"},
            "NORTH": {"air"},
            "SOUTH": {"air"},
            "EAST": {"air"},
            "WEST": {"air"}
        },
        weight=1.0,
        allow_rot=False
    )
    
    return [ground_tile, slope_tile, air_tile]

def test_basic_generation():
    """Test basic terrain generation with simple tiles"""
    print("=== Testing Basic Terrain Generation ===")
    
    try:
        # Create test tiles
        print("Creating test tiles...")
        bases = create_test_tiles()
        print(f"Created {len(bases)} base tiles")
        
        # Create variants
        print("Creating variants...")
        variants = create_variants(bases)
        print(f"Created {len(variants)} variants")
        
        # Test with small size
        size = (8, 8, 3)  # Small test size
        rng = random.Random(42)  # Fixed seed for reproducibility
        
        print(f"\nGenerating terrain with size {size}")
        print("=" * 50)
        
        result = generate_layers(
            bases=bases,
            variants=variants,
            size=size,
            rng=rng,
            guidance=None,
            step_callback=None
        )
        
        print(f"\n=== Generation Complete ===")
        print(f"Total placements: {len(result['placements'])}")
        print(f"Final size: {result['size']}")
        
        # Analyze placements by layer
        layers = {}
        for x, y, z, vi in result['placements']:
            if z not in layers:
                layers[z] = []
            layers[z].append((x, y, vi))
        
        for z in sorted(layers.keys()):
            print(f"Layer {z}: {len(layers[z])} tiles")
            
    except Exception as e:
        print(f"ERROR during generation: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    test_basic_generation()
