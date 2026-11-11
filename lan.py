"""This PC's address on the home network, and a QR code for it, so a phone can open the app."""
import socket

try:
    import segno
except ImportError:  # the QR code is a nicety: without segno the address is still printed
    segno = None


def lan_ip():
    """The address other devices on the network reach this PC at (no packet is sent: a UDP 'connect' only
    makes the OS pick the outgoing interface)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def phone_url(port, host="0.0.0.0"):
    """The URL a phone opens, or None when the server only listens on this PC."""
    if host in ("127.0.0.1", "localhost", "::1"):
        return None
    ip = host if host not in ("0.0.0.0", "::", "") else lan_ip()
    return None if ip.startswith("127.") else f"http://{ip}:{port}"


def print_qr(url, name):
    """Print the URL and its QR code in the console (scan it with the phone's camera)."""
    print(f"\n  {name} on your phone (same WiFi): {url}")
    if segno is None:
        print("  (pip install segno to show a QR code here)\n")
        return
    import sys
    try:   # the code is drawn with half blocks: the console has to be able to show them
        "▀▄█".encode(sys.stdout.encoding or "ascii")
    except (UnicodeEncodeError, LookupError):
        print("  (this console can't draw the QR code: open the address above, or the page's 'Open on your phone')\n")
        return
    print()
    segno.make(url, error="m").terminal(compact=True, border=2)
    print()


def qr_svg(url, dark="#d6d6d6", light="#1a1a1a"):
    """The QR code as an SVG string (for the page's 'Open on your phone' box)."""
    if segno is None:
        return None
    import io
    out = io.BytesIO()
    segno.make(url, error="m").save(out, kind="svg", scale=6, border=2, dark=dark, light=light, xmldecl=False)
    return out.getvalue().decode()
