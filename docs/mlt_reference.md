# MLT XML Reference

Quick reference for the MLT XML format used by `mlt-pilot`.

## Document Structure

```xml
<?xml version="1.0"?>
<mlt root="./" title="Project Title">
  <profile ... />
  <producer id="..." in="0" out="N">
    <property name="resource">path/to/file</property>
    <property name="mlt_service">avformat</property>
  </producer>
  <playlist id="...">
    <entry producer="..." in="0" out="N" />
    <blank length="30" />
  </playlist>
  <tractor id="...">
    <track producer="playlist0" />
    <track producer="playlist1" />
    <filter id="..." in="0" out="N">
      <property name="service_name">value</property>
    </filter>
    <transition id="..." a_track="0" b_track="1" in="0" out="N">
      <property name="...">value</property>
    </transition>
  </tractor>
</mlt>
```

## Root Element

| Attribute | Description | Example |
|-----------|-------------|---------|
| `root` | Base directory for relative paths | `./` |
| `title` | Project title | `"My Video"` |

## Profile Element

Defines the video format: resolution, frame rate, aspect ratio, colorspace.

| Attribute | Description | Example |
|-----------|-------------|---------|
| `width` | Frame width in pixels | `1920` |
| `height` | Frame height in pixels | `1080` |
| `progressive` | 1=progressive, 0=interlaced | `1` |
| `sample_aspect_num` | Sample aspect ratio numerator | `1` |
| `sample_aspect_den` | Sample aspect ratio denominator | `1` |
| `display_aspect_num` | Display aspect ratio numerator | `16` |
| `display_aspect_den` | Display aspect ratio denominator | `9` |
| `frame_rate_num` | Frame rate numerator | `30` |
| `frame_rate_den` | Frame rate denominator | `1` |
| `colorspace` | Color space: 709=HD, 601=SD | `709` |

## Producer Element

Represents a media source (video, audio, image).

| Attribute | Description |
|-----------|-------------|
| `id` | Unique identifier (e.g., `producer0`) |
| `in` | Start frame (inclusive) |
| `out` | End frame (inclusive) |

### Producer Properties

| Property | Description | Example |
|----------|-------------|---------|
| `resource` | Path to the media file | `videos/clip.mp4` |
| `mlt_service` | MLT service type | `avformat`, `pixbuf`, `pango` |

## Playlist Element

Represents a track on the timeline.

| Attribute | Description |
|-----------|-------------|
| `id` | Unique identifier (e.g., `playlist0`) |

### Entry Element (clip reference)

| Attribute | Description |
|-----------|-------------|
| `producer` | ID of the source producer |
| `in` | Start frame in source media |
| `out` | End frame in source media |

### Blank Element (gap)

| Attribute | Description |
|-----------|-------------|
| `length` | Duration in frames |

## Tractor Element

Composites multiple tracks together with transitions and filters.

### Track Element (inside tractor)

| Attribute | Description |
|-----------|-------------|
| `producer` | ID of the playlist to reference |

## Filter Element

Applies an effect to a track.

| Attribute | Description |
|-----------|-------------|
| `id` | Unique identifier |
| `in` | Start frame (optional) |
| `out` | End frame (optional) |

Common filter services:
- `volume` — Audio volume control (`gain` property)
- `brightness` — Brightness/contrast adjustment
- `greyscale` — Convert to black and white
- `opacity` — Opacity control
- `affine` — Position, rotation, scale

## Transition Element

Defines a transition between two tracks.

| Attribute | Description |
|-----------|-------------|
| `id` | Unique identifier |
| `a_track` | Background track index |
| `b_track` | Foreground track index |
| `in` | Start frame |
| `out` | End frame |

Common transition services:
- `composite` — Layer compositing
- `mix` — Audio/video crossfade
- `luma` — Luma wipe/dissolve

## Time Representation

MLT uses **frame numbers** for all timing. Frame 0 is the first frame.
The `in` and `out` attributes are **inclusive**: a clip from frame 0 to frame 299
is 300 frames long (10 seconds at 30fps).

## Subtitle Producers

Subtitles use Pango text rendering:

```xml
<producer id="subtitle_0_1" in="150" out="240">
  <property name="mlt_service">pango</property>
  <property name="markup">Subtitle text here</property>
  <property name="family">Sans</property>
  <property name="size">26624</property>
</producer>
```

Font size in Pango units = CSS pixels * 1024.

## Common mlt_service Values

| Service | Media Type | Description |
|---------|-----------|-------------|
| `avformat` | Video/Audio | FFmpeg-based decoder |
| `pixbuf` | Image | Image loader (GDK-PixBuf) |
| `pango` | Text | Pango text renderer |

## Profile Reference

Common profiles available in `mlt-pilot`:

| Name | Resolution | FPS | Description |
|------|-----------|-----|-------------|
| `atsc_1080p_30` | 1920x1080 | 30 | Full HD progressive |
| `atsc_1080p_25` | 1920x1080 | 25 | Full HD progressive (PAL) |
| `atsc_1080p_24` | 1920x1080 | 24 | Full HD progressive (cinema) |
| `atsc_720p_30` | 1280x720 | 30 | HD progressive |
| `dv_ntsc` | 720x480 | 29.97 | SD NTSC |
| `dv_pal` | 720x576 | 25 | SD PAL |
