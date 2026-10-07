"""Ashen Vault UI atlas integration.

The atlas is a real sprite sheet: every reusable UI element is addressed by an
explicit source rectangle. The source artwork has a pure black background, so
black is treated as transparent when sprites are extracted.

This module deliberately avoids guessing from connected components. The atlas
contains touching/overlapping decorative pixels, so explicit regions are much
more reliable and preserve the authored artwork.
"""
from pathlib import Path
import math
import pygame

ROOT = Path(__file__).resolve().parent.parent
ATLAS_PATH = ROOT / "assets" / "ui" / "AshenVault_UI_Atlas.png"

