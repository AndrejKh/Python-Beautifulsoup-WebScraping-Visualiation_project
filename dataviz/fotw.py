import pandas as pd
from pudzu.pillar import *
from pathlib import Path
from tqdm import tqdm

BG = "#EEEEEE"
FOTW_DIR = Path("images")

class HeraldicPalette(metaclass=NamedPaletteMeta):
    Y = "#fcdd09" # 0 yellow
    W = "#ffffff" # 1 white
    B = "#0f47af" # 2 blue
    R = "#da121a" # 3 red
    P = "#9116a1" # 4 purple
    K = "#000000" # 5 black
    G = "#009200" # 6 green
    T = "#804000" # 7 brown
    O = "#ff8000" # 8 orange
    C = "#75aadb" # 9 sky blue
    Q = "#ffc0cb" # A pink

def runs(row): return (np.ediff1d(row) != 0).sum() + 1

def omit_types(filter, types="()^!~@}'$_"):
    @wraps(filter)
    def wrapped(p, *args, **kwargs):
        if any(c in p.stem for c in types): return None
        return filter(p, *args, **kwargs)
    return wrapped
    
def generate_cribs(filter, prefix=None, max_cols=10, max_rows=10, base_path=FOTW_DIR):
    i, counts, images = 0, {}, {}
    index = []
    
    def save_and_increment(cat):
        if images.get(cat, []):
            icons = []
            for p in images[cat]:
                icon = Image.open(p).to_rgba().pad_to_aspect(80,50,bg=BG).resize_fixed_aspect(height=50)
                label = Image.from_text(p.stem, sans(10))
                both = Image.from_column([icon, label], padding=(0,3))
                icons.append(both)
            img = Image.from_array(list(generate_batches(icons, max_cols)), padding=5, bg=BG)
            counts[cat] = counts.get(cat, 0) + 1
            filename = f"output/{prefix or filter.__name__}_{cat}_{counts[cat]}.png"
            print(f"Saving flags to {filename}")
            img.save(filename)
            images[cat] = []
    
    for p in tqdm(sorted(base_path.rglob("*gif"))):
        try:
            cat = filter(p)
            if cat:
                i += 1
                print(str(cat)[0], end="")
                if i % max_cols == 0: print(f" {p.stem}")
                images.setdefault(cat, []).append(p)
                index.append((p, cat))
                if len(images[cat]) >= max_cols * max_rows: save_and_increment(cat)
                    
        except Exception:
            continue
    print()
    for cat in images: save_and_increment(cat)
    return pd.DataFrame(index, columns=["path", "category"])

@omit_types
def transparent(p):
    """Any flags with transparency"""
    img = Image.open(p)
    return any(c[-1] == 0 and v > max(img.width, img.height) for v,c in img.to_rgba().getcolors())

def bands(n):
    """Simple heuristic for n-banded flags"""
    @omit_types
    def bands(p):
        img = Image.open(p)
        if img.width < img.height: return None
        a = np.array(img)
        if all(a[0] == a[-1]) and runs(a[0]) == n and runs(a[:,0]) == 1:
            cat = "Vertical"
        elif all(a[:,0] == a[:,-1]) and runs(a[:,0]) == n and runs(a[0]) == 1:
            cat = "Horizontal"
        elif (all(a[0] == a[-1]) or all(a[:,0] == a[:,-1])) and runs(a[0]) == n and runs(a[:,0]) == n:
            cat = "Cross"
        else:
            return
        ap = np.array(img.to_palette(HeraldicPalette))
        if cat == "Vertical":
            cat += "_" + "".join(HeraldicPalette.names[i] for i,_ in itertools.groupby(ap[0]))
        elif cat == "Horizontal":
            cat += "_" + "".join(HeraldicPalette.names[i] for i,_ in itertools.groupby(ap[:,0]))
        return cat
    return bands

def color(color: str):
    """Simple heuristic for detecting a Heraldic color."""
    @omit_types
    def colors(p):
        img = Image.open(p)
        if (img.width / img.height) < 0.8: return None
        ap = np.array(img.to_palette(HeraldicPalette))
        u, f = np.unique(ap, return_counts=True)
        d = { HeraldicPalette.names[k] : v for k,v in zip(u,f) }
        if d.get(color) > (img.width * img.height / 10): return color
    return colors
    
@omit_types
def rwb(p):
    """Red-white-blue flags"""
    img = Image.open(p)
    if img.width < img.height: return None
    img = img.to_rgba().remove_transparency("white")
    ap = np.array(img.to_palette(HeraldicPalette))
    u, f = np.unique(ap, return_counts=True)
    d = { k : v for k,v in zip(u,f) if v > img.width * 2 }
    if all(v > ap.size // 50 for v in d.values()):
        ds = set(d)
        if ds == { 1, 2, 3 }: return "B"
        elif ds == { 1, 9, 3}: return "C"
        elif ds == { 1, 2, 3, 9}: return "X"

@omit_types
def gwb(p):
    """Green-white-blue flags"""
    img = Image.open(p)
    if img.width < img.height: return None
    img = img.to_rgba().remove_transparency("white")
    ap = np.array(img.to_palette(HeraldicPalette))
    u, f = np.unique(ap, return_counts=True)
    d = { k : v for k,v in zip(u,f) if v > img.width * 2 }
    if all(v > ap.size // 50 for v in d.values()):
        ds = set(d)
        if ds == { 1, 2, 6 }: return "B"
        elif ds == { 1, 9, 6}: return "C"
        elif ds == { 1, 2, 6, 9}: return "X"

def colorset(*colors: str, exclusive: bool = True):
    """Detecting multiple colors"""

    colsets = { color : { HeraldicPalette.names.index(c) for c in color}  for color in colors}
    
    @omit_types
    def colorset(p):
        """Gold-white-black flags"""
        img = Image.open(p)
        if img.width < img.height: return None
        img = img.to_rgba().remove_transparency("white")
        ap = np.array(img.to_palette(HeraldicPalette))
        u, f = np.unique(ap, return_counts=True)
        d = { k : v for k,v in zip(u,f) if v > img.width * img.height * 0.05 }
        ds = set(d)
        for color, colset in colsets.items():
            if colset == ds: return color
            if not exclusive and colset < ds: return "X"+color
    return colorset


@omit_types
def grey(p):
    """Flags with grey"""
    img = Image.open(p)
    if (img.width / img.height) < 0.8: return None
    cols = img.to_rgba().getcolors(65536)
    return any(r==g==b and a==255 and 20 <= r <= 240 and v > (img.width * img.height / 50) for v,(r,g,b,a) in cols)


