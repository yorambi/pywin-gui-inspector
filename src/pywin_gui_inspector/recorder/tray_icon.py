from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont


class TrayIconFactory:
    """Creates the tray icon image for idle and recording states.

    Generates a 64×64 RGBA icon with a circular badge containing the
    letter "R".  The colour scheme changes between idle (green outline on
    dark background) and recording (solid red fill with white text) states.

    Attributes:
        SIZE: Edge length in pixels of the square icon canvas.
    """

    SIZE = 64

    @staticmethod
    def make(recording: bool = False) -> Image.Image:
        """Renders and returns a tray icon image for the given recorder state.

        Draws a circular badge with an "R" label.  In recording mode, the
        badge is filled red with a white letter; in idle mode, it is dark
        with a green outline and green letter.  Falls back to the default
        PIL font if ``consolab.ttf`` is not available.

        Args:
            recording: If True, renders the recording-active (red) variant.
                Defaults to False (idle / green variant).

        Returns:
            A 64×64 ``PIL.Image.Image`` in RGBA mode ready to be passed to
            a pystray ``Icon``.
        """
        size   = TrayIconFactory.SIZE
        img    = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw   = ImageDraw.Draw(img)
        cx, cy = size // 2, size // 2

        if recording:
            draw.ellipse([2, 2, size-3, size-3], outline=(220, 50, 50), width=4)
            draw.ellipse([10, 10, size-11, size-11], fill=(200, 40, 40))
            txt_color = (255, 255, 255)
        else:
            draw.ellipse([2, 2, size-3, size-3], fill=(30, 30, 50), outline=(0, 200, 80), width=3)
            txt_color = (0, 200, 80)

        try:
            font = ImageFont.truetype("consolab.ttf", 30)
        except Exception:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), "R", font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((cx - tw // 2, cy - th // 2 - 2), "R", fill=txt_color, font=font)
        return img