"""Runtime settings, read once from the environment (see .env.example)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

# Provinces the app focuses on (docs/SOURCES.md §4, OPEN_QUESTIONS Q5): the whole Bangkok Metropolitan Region
# (Bangkok + Nonthaburi, Pathum Thani, Samut Prakan, Samut Sakhon, Nakhon Pathom; the last two added 2026-09-26,
# D-023) and the lower Chao Phraya chain up to Nakhon Sawan.
FOCUS_PROVINCES = (
    "กรุงเทพมหานคร", "นนทบุรี", "ปทุมธานี", "สมุทรปราการ", "สมุทรสาคร", "นครปฐม", "พระนครศรีอยุธยา",
    "อ่างทอง", "สิงห์บุรี", "ชัยนาท", "นครสวรรค์",
)
# Gauges whose values are clearly not m MSL (KI-210): collected and archived, shown on the map with a note, but
# their levels are hidden and never forecast until the datum offset is known.
DATUM_SUSPECT = {"GLF002": "Tha Chin mouth: median 5.5 m, max 7.4 m, spikes to -28.6 m (MSL gauges nearby: ~0-1.6 m)"}
# Stations that must be tracked even if the latest-values feed omits them (BKK008 is absent from
# waterlevel_load but served by the HII chart XHR; see research/VALIDATION_2026-09-26.md §E).
EXTRA_STATIONS = ("BKK008",)

# Rain-forecast points (Open-Meteo). Regional forcing only; NWP cells are coarser than polders (KI-306).
RAIN_POINTS = {
    "bkk_central": (13.75, 100.50),
    "bkk_east": (13.80, 100.75),
    "bkk_north": (13.90, 100.60),
    "bkk_west": (13.72, 100.40),
    "samut_sakhon_nakhon_pathom": (13.72, 100.20),
    "nonthaburi_pathum": (14.00, 100.52),
    "ayutthaya": (14.35, 100.55),
    "chainat": (15.18, 100.13),
    "nakhon_sawan": (15.70, 100.10),
}


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: _env(
        "DATABASE_URL", "postgresql://floodwatch:floodwatch@127.0.0.1:5432/floodwatch"))
    archive_path: str = field(default_factory=lambda: _env("TELEMETRY_ARCHIVE_PATH", "./data/raw_archive"))
    user_agent: str = field(default_factory=lambda: _env(
        "HTTP_USER_AGENT", "BKK-FloodWatch/0.2 (+https://flood.autobahn.bot)"))
    timeout_s: float = field(default_factory=lambda: float(_env("HTTP_TIMEOUT_SECONDS", "120")))
    # Optional egress through a Thai IP for sources that geo-block (BMA). D-014. Format: socks5h://host:port
    thai_egress_proxy: str = field(default_factory=lambda: _env("THAI_EGRESS_PROXY"))
    min_free_disk_gb: float = field(default_factory=lambda: float(_env("MIN_FREE_DISK_GB", "2")))
    gistda_api_key: str = field(default_factory=lambda: _env("GISTDA_API_KEY"))
    gistda_api_endpoint: str = field(default_factory=lambda: _env(
        "GISTDA_API_ENDPOINT",
        "https://api-gateway.gistda.or.th/api/2.0/resources/gi-service/v1.0/disasters/flood-extent-1day"))


settings = Settings()
