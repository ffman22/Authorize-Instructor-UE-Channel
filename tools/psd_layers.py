#!/usr/bin/env python3
"""Read single raster layers from an 8-bit RGB PSD with Pillow only (no extra packages).

Usage: psd_layers.py <file.psd>            list the layers
Import: flatten(path, ["Background", 3]) -> RGBA image of those layers (by name or index), bottom up.
Layer masks and blend modes are not applied; opacity is.
"""
import argparse
import struct
import zlib

from PIL import Image


def read(path):
    """Return (size, layers); each layer is {name, box, opacity, hidden, channels: {id: (offset, length)}}."""
    data = open(path, "rb").read()
    if data[:4] != b"8BPS":
        raise ValueError(f"not a PSD: {path}")
    height, width, depth = struct.unpack(">IIH", data[14:24])
    if depth != 8:
        raise ValueError("only 8-bit PSD files are supported")
    pos = 26
    for _ in range(2):  # color mode data, image resources
        pos += 4 + struct.unpack(">I", data[pos:pos + 4])[0]
    pos += 8  # layer and mask length, layer info length
    count = abs(struct.unpack(">h", data[pos:pos + 2])[0])
    pos += 2
    layers = []
    for _ in range(count):
        top, left, bottom, right, n = struct.unpack(">iiiiH", data[pos:pos + 18])
        pos += 18
        channels = []
        for _ in range(n):
            channels.append(struct.unpack(">hI", data[pos:pos + 6]))
            pos += 6
        opacity, flags = data[pos + 8], data[pos + 10]
        extra = struct.unpack(">I", data[pos + 12:pos + 16])[0]
        p = pos + 16
        p += 4 + struct.unpack(">I", data[p:p + 4])[0]  # layer mask
        p += 4 + struct.unpack(">I", data[p:p + 4])[0]  # blending ranges
        name = data[p + 1:p + 1 + data[p]].decode("mac_roman", "replace")
        pos += 16 + extra
        layers.append({"name": name, "box": (left, top, right, bottom), "opacity": opacity,
                       "hidden": bool(flags & 2), "channels": channels})
    for layer in layers:
        offsets = {}
        for cid, length in layer["channels"]:
            offsets[cid] = (pos, length)
            pos += length
        layer["channels"] = offsets
    return (width, height), layers, data


def channel(data, offset, length, w, h):
    compression = struct.unpack(">H", data[offset:offset + 2])[0]
    raw = data[offset + 2:offset + length]
    if compression == 0:
        return Image.frombytes("L", (w, h), raw)
    if compression == 1:  # PackBits; skip the per-row byte counts
        return Image.frombytes("L", (w, h), raw[2 * h:], "packbits", "L")
    if compression == 2:
        return Image.frombytes("L", (w, h), zlib.decompress(raw))
    raise ValueError(f"unsupported PSD compression {compression}")


def layer_image(data, layer):
    left, top, right, bottom = layer["box"]
    w, h = right - left, bottom - top
    bands = [channel(data, *layer["channels"][c], w, h) for c in (0, 1, 2)]
    alpha = (channel(data, *layer["channels"][-1], w, h) if -1 in layer["channels"]
             else Image.new("L", (w, h), 255))
    if layer["opacity"] < 255:
        alpha = alpha.point(lambda v: v * layer["opacity"] // 255)
    return Image.merge("RGBA", (*bands, alpha))


def flatten(path, wanted):
    """Composite the wanted layers (names or indexes) onto a transparent canvas, in file order."""
    size, layers, data = read(path)
    picked = [i for i, ly in enumerate(layers) if i in wanted or ly["name"] in wanted]
    if not picked:
        raise ValueError(f"no layer of {wanted} in {path}")
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    for i in picked:
        left, top, right, bottom = layers[i]["box"]
        if right <= left or bottom <= top:
            continue
        sheet = Image.new("RGBA", size, (0, 0, 0, 0))
        sheet.paste(layer_image(data, layers[i]), (left, top))
        canvas = Image.alpha_composite(canvas, sheet)
    return canvas


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="List the layers of a PSD file.")
    ap.add_argument("psd", help="path to the .psd file")
    size, layers, _ = read(ap.parse_args().psd)
    print(size)
    for i, ly in enumerate(layers):
        print(i, repr(ly["name"]), ly["box"], "hidden" if ly["hidden"] else "")
