from pathlib import Path
import pygame

ROOT = Path(__file__).resolve().parents[1]
pygame.init()

for p in [ROOT/'assets/weapons/new/modelosarmas.png', ROOT/'assets/weapons/new/modelosarmasmelee.png']:
    image = pygame.image.load(str(p)).convert_alpha()
    mask = pygame.mask.from_surface(image, threshold=8)
    comps = mask.connected_components(minimum=18)
    rects=[]
    for c in comps: rects.extend(c.get_bounding_rects())
    rects=[r for r in rects if r.width >= 2 and r.height >= 2]
    print(f'{p.name}: size={image.get_size()} components={len(rects)}')
    for i,r in enumerate(sorted(rects,key=lambda x:(x.top,x.left))): print(f'  {i}: {r.x},{r.y},{r.width},{r.height}')
pygame.quit()