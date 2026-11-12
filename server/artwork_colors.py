"""Choose a highlight and a contrasting companion from a cover's palette."""
import colorsys
import math
from PIL import Image


def cover_colors(image):
    sample = image.convert('RGB')
    sample.thumbnail((128, 128), Image.Resampling.LANCZOS)
    indexed = sample.quantize(colors=32, method=Image.Quantize.MEDIANCUT)
    palette = indexed.getpalette()
    total = sample.width * sample.height
    colors = []
    for count, index in indexed.getcolors():
        rgb = tuple(palette[index * 3:index * 3 + 3])
        hue, saturation, value = colorsys.rgb_to_hsv(*(channel / 255 for channel in rgb))
        colors.append({'rgb': rgb, 'area': count / total,
                       'hue': hue, 'saturation': saturation, 'value': value})

    def hue_distance(first, second):
        difference = abs(first['hue'] - second['hue'])
        return min(difference, 1 - difference)

    def distance(first, second):
        return math.sqrt(sum(((a - b) / 255) ** 2
                            for a, b in zip(first['rgb'], second['rgb'])) / 3)

    chromatic = [color for color in colors if color['area'] >= .004
                 and color['saturation'] >= .2 and color['value'] >= .24
                 and color['saturation'] * color['value'] >= .1]
    # Pool nearby hues: a blue area split into many shades still counts as one
    # prominent family. Black, white, and gray do not compete with real colors.
    for color in chromatic:
        color['family_area'] = sum(other['area'] for other in chromatic
                                   if hue_distance(color, other) <= .06)
    substantial = [color for color in chromatic if color['family_area'] >= .02]

    def prominence(color):
        return (color['family_area'] ** .45 * color['area'] ** .15 *
                color['saturation'] ** .75 * color['value'] ** .35)

    if substantial:
        primary = max(substantial, key=prominence)
        companions = [color for color in substantial
                      if hue_distance(primary, color) >= .1 and distance(primary, color) >= .15]
    else:
        neutrals = [color for color in colors if .18 <= color['value'] <= .9]
        primary = max(neutrals or colors, key=lambda color: color['area'])
        companions = []

    if companions:
        # Prefer a second recognizable hue over a high-contrast dark border.
        secondary = max(companions, key=lambda color:
            prominence(color) * (.4 + .6 * (hue_distance(primary, color) / .5) ** .7))
    else:
        # Single-hue and monochrome covers can use a contrasting shade/neutral.
        fallback = [color for color in colors if color['area'] >= .015]
        secondary = max(fallback or colors, key=lambda color:
                        color['area'] ** .35 * distance(primary, color))
    return tuple('#%02x%02x%02x' % color['rgb'] for color in (primary, secondary))


def highlight_color(image):
    return cover_colors(image)[0]


def write_shelf_colors(artwork, destination):
    pairs = sorted({(sides['color'], sides['secondary_color']) for sides in artwork.values()})
    destination.write_text('/* Generated from two distinguishable color families in each front cover. */\n' +
        ''.join('.is-enhanced .spine-' + first[1:] + '-' + second[1:] +
                ' .album-artwork{background-color:' + first +
                ';background-image:linear-gradient(180deg,' + first + ' 0%,' + second + ' 100%)}\n'
                for first, second in pairs))
