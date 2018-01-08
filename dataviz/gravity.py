import sys
import matplotlib.pyplot as plt
sys.path.append('..')
from pillar import *
from scipy import signal

# slow gravity calculation that's fast enough because numpy :-)

np.seterr(divide='ignore', invalid='ignore')

def force_components(rows, cols, linear=False):
    xs = np.fromfunction(lambda i,j: (rows-1-i), (2*rows-1, 2*cols-1))
    ys = np.fromfunction(lambda i,j: (cols-1-j), (2*rows-1, 2*cols-1))
    n3 = (xs**2 + ys**2) ** (1 if linear else 3/2)
    return np.nan_to_num(xs / n3), np.nan_to_num(ys / n3)

def gravity_components(arr, linear=False):
    isqxs, isqys = force_components(*arr.shape, linear=linear)
    xs = np.rot90(signal.convolve2d(np.rot90(arr, 2), isqxs, 'same'), 2)
    ys = np.rot90(signal.convolve2d(np.rot90(arr, 2), isqys, 'same'), 2)
    return xs, ys

def gravity_magnitude(arr, normalised=True, linear=False):
    if isinstance(arr, Image.Image): arr = mask_to_array(arr)
    components = gravity_components(arr, linear=linear)
    mag = (components[0] ** 2 + components[1] ** 2) ** 0.5
    return mag / mag.max() if normalised else mag

# some visualisation helpers

def mask_to_array(img):
    return np.array(img.as_mask()) / 255
    
def mask_to_img(img, fg="grey", bg="white"):
    return MaskUnion(..., fg, bg, masks=img)
    
def shapeplot(shape, min=None, max=None):
    shape = mask_to_img(shape)
    shape = shape.place(MaskUnion(..., "green", masks=make_iterable(min))).place(MaskUnion(..., "red", masks=make_iterable(max)))
    return shape

def heatmap(array, cmap=plt.get_cmap("hot")):
    return Image.fromarray(cmap(array, bytes=True))
   
def minmax(array, low=2, high=10, lowcol="green", midcol="white", highcol="red"):
    # for figuring out low and high points; not pretty enough to actually use
    intervals = [low/2, low/2, 100-low-high, high/2, high/2]
    cmap = GradientColormap(lowcol, lowcol, midcol, midcol, highcol, highcol, intervals=intervals)
    return heatmap(array, cmap)
    
def minblend(shape, p=0.25, **kwargs):
    return ignoring_extra_args(shapeplot)(shape, **kwargs).blend(
        ignoring_extra_args(minmax)(ignoring_extra_args(gravity_magnitude)(shape, **kwargs), **kwargs), p=p)

def linechart(data, width, height, color, cache="cache/gravity_plot.png"):
    if height is None: height = width
    fig = plt.figure(figsize=(width/100,height/100), dpi=100)
    ax = fig.add_axes((0,0,1,1))
    ax.set_axis_off()
    ax.plot(data, color)
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)
    plt.savefig(cache, bbox_inches="tight", pad_inches=0, dpi='figure', transparent=True)
    plt.close()
    return Image.open(cache)

def scanlines(array, directions):
    h, w = array.shape
    x, y = round(w / 2), round(h / 2)
    img = Rectangle((w,h//2), "white")
    if "v" in directions: img = img.place(linechart(array[:,x], h, w//2, "#008000"))
    if "h" in directions: img = img.place(linechart(array[y], w, h//2, "#800000"))
    # if "d" in directions: 
    return img

def odd(n): return round(n) + (round(n)-1)%2

# list of shapes

WIDTH = 60 # 100
PADDING = 20
SHAPES = CaseInsensitiveDict(base_factory=OrderedDict)

ShapeOpts = namedtuple('ShapeOpts', ['name', 'shape', 'min', 'max', 'min_linear', 'max_linear', 'scanlines', 'description'])
def make_shape(name, shape, min=None, max=None, min_linear=..., max_linear=..., scanlines="h", description="Some **interesting** point?"):
    return ShapeOpts(name, shape, min, max, min if min_linear == ... else min_linear, max if max_linear == ... else max_linear, scanlines, description)

base = Image.new("RGBA", (round(WIDTH*1.5), round(WIDTH*1.5)))
pwidth = odd(WIDTH*2/3)
ppwdith = odd(pwidth*3/4)
dot = Ellipse(5)

circle = base.place(Ellipse(pwidth))
circle_min = dot
circle_max = MaskIntersection(..., masks=(Ellipse(pwidth+2), Ellipse(pwidth-2, invert=True)), include_missing=True)
SHAPES["circle"] = make_shape("circle", circle, circle_min, circle_max)

ellipse = base.place(Ellipse((pwidth, odd(pwidth / 2))))
ellipse_min = dot
ellipse_max = None # TODO: ?!
SHAPES["ellipse"] = make_shape("ellipse", ellipse, ellipse_min, ellipse_max, scanlines="vh")

core = base.place(Ellipse(pwidth, (0,0,0,100))).place(Ellipse(ppwdith))
core_min = dot
core_max = MaskIntersection(..., masks=(Ellipse(ppwdith+2), Ellipse(ppwdith-2, invert=True)), include_missing=True)
SHAPES["core"] = make_shape("dense core", core, core_min, core_max)

hollow = base.place(MaskIntersection(..., masks=(Ellipse(pwidth), Ellipse(ppwdith, invert=True)), include_missing=True))
hollow_min = MaskIntersection(..., masks=(Ellipse(round(pwidth*0.85)+2), Ellipse(round(pwidth*0.85)-2, invert=True)), include_missing=True).place(dot)
hollow_max = circle_max
hollow_min_linear = Ellipse(ppwdith)
SHAPES["hollow"] = make_shape("hollow shell", hollow, hollow_min, hollow_max, hollow_min_linear)

square = base.place(Rectangle(pwidth))
square_min = dot
# TODO: max, diagonal
SHAPES["square"] = make_shape("square", square, square_min)

# mountain = base.place(Ellipse(pwidth)) # Triange(odd(pwdith/3))

# TODO: mountain, plateau, two, two weighted, square, rectangle, ?, reddit
# shapeplot(ellipse, ellipse_min, ellipse_max).blend(minmax(a, high=0.01), p=0.25).show()

def plot_shape(shape): 
    mag = gravity_magnitude(shape.shape, linear=False)
    mag_linear = gravity_magnitude(shape.shape, linear=True)
    w, h = mag.shape
    y = round(h / 2)
    grid = Image.from_array([
        [shapeplot(shape.shape, shape.min, shape.max),
         shapeplot(shape.shape, shape.min_linear, shape.max_linear)][::-1],
        [heatmap(mag),
         heatmap(mag_linear)][::-1],
        [scanlines(mag, shape.scanlines).pad((0,PADDING),"white"),
         scanlines(mag_linear, shape.scanlines).pad((0,PADDING),"white")][::-1]
        ], padding=0, bg="white")
    markup = Image.from_markup(shape.description, partial(arial, 12), max_width=w*2)
    markup = Rectangle((w*2, markup.height), "white").place(markup, align=0)
    return Image.from_column([
        Image.from_text(shape.name.upper(), arial(16, bold=True)),
        grid,
        markup
        ], padding=0, bg="white")

# unused quadtree implementation from before I figured out how to use numpy properly

class QuadTree(object):

    def __new__(cls, array, x=0, y=0):
        """Generate hierarchical QuadTree object, or None if the array is zero."""
        w,h = array.shape[0], array.shape[1]
        assert w == h, "QuadTree input array must be a square"
        if array.size == 1: # leaf node
            if array[0,0] == 0: return None
            children = None
        else: # internal node
            assert w % 2 == 0, "QuadTree input array size be a power of two"
            children = [QuadTree(array[i:i+w//2,j:j+h//2], x+i, y+j) for (i,j) in itertools.product([0,w//2],[0,h//2])]
            if not any(children): return None
        self = super(QuadTree, cls).__new__(cls)
        self.children = children
        return self

    def __init__(self, array, x=0, y=0):
        """Initialize a QuadTree object."""
        self.width = array.shape[0]
        if array.size == 1:
            self.mass = array[0,0]
            self.com = np.array([x,y])
        else:
            self.mass = sum(c.mass for c in self.children if c is not None)
            self.com = sum(c.com * c.mass for c in self.children if c is not None) / self.mass
            
    def __repr__(self):
        return "<QuadTree mass={} com={}>".format(self.mass, self.com)

def qtree_gravity(qtree, loc, theta):
    v = loc - qtree.com
    d = np.linalg.norm(v)
    if qtree.width == 1 or d > 0 and qtree.width / d < theta:
        return 0 if d == 0 else v * qtree.mass / (d**3)
    return sum(qtree_gravity(c, loc, theta) for c in qtree.children if c is not None)
   
def qtree_gravity_array(arr, theta=0.8):
    padded_size = 1 << (max(arr.shape)-1).bit_length()
    padded = np.pad(arr, [(0, padded_size - arr.shape[0]), (0, padded_size - arr.shape[1])], mode='constant')
    qtree = QuadTree(padded)
    def calculate(i, j): return qtree_gravity(qtree, np.array([i, j]), theta)
    return np.fromfunction(np.frompyfunc(calculate, 2, 1), arr.shape, dtype=int)
