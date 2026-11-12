"""Match the original simulator's hide-both policy for colliding body names."""


def visible_labels(rectangles, selected=None):
    """Return visible body IDs for {ID: (left, top, width, height)} screen rectangles.

    Every colliding label is suppressed, even if its partner is suppressed too.
    Preserve the selected body's name; use the Sun (ID 0) when none is selected.
    Recomputing from all candidates each frame restores names when zooming in.
    """
    priority = 0 if selected is None else selected
    hidden = set()
    items = list(rectangles.items())
    for offset, (first, a) in enumerate(items):
        for second, b in items[offset + 1:]:
            overlap = (a[0] <= b[0] + b[2] and a[0] + a[2] >= b[0]
                       and a[1] <= b[1] + b[3] and a[1] + a[3] >= b[1])
            if overlap:
                hidden.update((first, second))
    hidden.discard(priority)
    return set(rectangles) - hidden
