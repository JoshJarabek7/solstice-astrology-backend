# pyswisseph.pyi

# Constants
FLG_SPEED: int
FLG_SWIEPH: int

JUPITER: int
MARS: int
MERCURY: int
MOON: int
NEPTUNE: int
PLUTO: int
SATURN: int
SUN: int
URANUS: int
VENUS: int

SE_GREG_CAL: int  # Add this line for the Gregorian calendar constant

# Functions
def calc(jd: float, ipl: int, iflag: int) -> tuple[float, float, float]: ...
def houses(jd_ut: float, lat: float, lon: float, hsys: str) -> tuple[list[float], list[float]]: ...
def julday(year: int, month: int, day: int, hour: float, calflag: int) -> float: ...
