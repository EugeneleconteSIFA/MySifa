"""MySifa — Service ICS (iCalendar).

Téléchargement borné d'un flux ICS distant (garde anti-SSRF), parsing des
VEVENT et expansion des règles de récurrence sur une fenêtre de dates.

Sous-ensemble RFC 5545 volontairement restreint mais couvrant l'usage réel :
DTSTART / DTEND / DURATION, VALUE=DATE, TZID, UTC, SUMMARY, DESCRIPTION,
LOCATION, UID, STATUS, RRULE (FREQ / INTERVAL / COUNT / UNTIL / BYDAY /
BYMONTHDAY / BYMONTH), EXDATE et RECURRENCE-ID.
"""

from __future__ import annotations

import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

try:  # Python 3.9+
    from zoneinfo import ZoneInfo

    _TZ_PARIS: Optional[Any] = ZoneInfo("Europe/Paris")
except Exception:  # pragma: no cover - environnement sans tzdata
    ZoneInfo = None  # type: ignore[assignment]
    _TZ_PARIS = None

ICS_MAX_BYTES = 4 * 1024 * 1024
ICS_TIMEOUT_S = 12
ICS_USER_AGENT = "MySifa-Calendar/1.0 (+https://www.mysifa.com)"
MAX_OCCURRENCES = 2000
WEEKDAY_CODES = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


class IcsError(Exception):
    """Erreur fonctionnelle de récupération ou de parsing d'un flux ICS."""


# --------------------------------------------------------------------------
# Téléchargement
# --------------------------------------------------------------------------


def normalize_feed_url(raw: str) -> str:
    """webcal:// → https:// ; valide le schéma et la présence d'un hôte."""
    url = str(raw or "").strip()
    if not url:
        raise IcsError("URL vide.")
    low = url.lower()
    if low.startswith("webcal://"):
        url = "https://" + url[len("webcal://") :]
    elif low.startswith("webcals://"):
        url = "https://" + url[len("webcals://") :]
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("http", "https"):
        raise IcsError("Schéma non supporté — utilisez http, https ou webcal.")
    if not parsed.hostname:
        raise IcsError("URL invalide — hôte manquant.")
    return url


def _assert_public_host(url: str) -> None:
    """Refuse une URL qui résout vers une adresse privée / locale (anti-SSRF)."""
    host = urllib.parse.urlsplit(url).hostname or ""
    if not host:
        raise IcsError("URL invalide — hôte manquant.")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise IcsError(f"Hôte introuvable : {host}")
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise IcsError("Adresse réseau interne refusée.")


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        checked = normalize_feed_url(newurl)
        _assert_public_host(checked)
        return super().redirect_request(req, fp, code, msg, headers, checked)


def fetch_ics(url: str, *, timeout: int = ICS_TIMEOUT_S) -> str:
    """Télécharge un flux ICS. Lève IcsError en cas de problème."""
    safe_url = normalize_feed_url(url)
    _assert_public_host(safe_url)
    req = urllib.request.Request(
        safe_url,
        headers={"User-Agent": ICS_USER_AGENT, "Accept": "text/calendar, text/plain"},
    )
    opener = urllib.request.build_opener(_SafeRedirectHandler)
    try:
        with opener.open(req, timeout=timeout) as resp:
            raw = resp.read(ICS_MAX_BYTES + 1)
    except urllib.error.HTTPError as e:
        raise IcsError(f"HTTP {e.code} sur le flux distant.")
    except urllib.error.URLError as e:
        raise IcsError(f"Flux injoignable : {getattr(e, 'reason', e)}")
    except (TimeoutError, socket.timeout):
        raise IcsError("Délai dépassé sur le flux distant.")
    except OSError as e:
        raise IcsError(f"Flux injoignable : {e}")
    if len(raw) > ICS_MAX_BYTES:
        raise IcsError("Flux trop volumineux (> 4 Mo).")
    text = raw.decode("utf-8", errors="replace")
    if "BEGIN:VCALENDAR" not in text.upper():
        raise IcsError("La réponse n'est pas un calendrier iCalendar.")
    return text


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------


def _unfold(text: str) -> list[str]:
    lines: list[str] = []
    for raw in str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def _split_prop(line: str) -> Optional[tuple[str, dict[str, str], str]]:
    idx = line.find(":")
    if idx < 0:
        return None
    head = line[:idx]
    value = line[idx + 1 :]
    parts = head.split(";")
    name = parts[0].strip().upper()
    params: dict[str, str] = {}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            params[k.strip().upper()] = v.strip().strip('"')
    return name, params, value


def _unescape_text(value: str) -> str:
    out: list[str] = []
    i = 0
    s = str(value or "")
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt in ("n", "N"):
                out.append("\n")
            elif nxt in ("\\", ",", ";"):
                out.append(nxt)
            else:
                out.append(nxt)
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _to_paris_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    if _TZ_PARIS is not None:
        return dt.astimezone(_TZ_PARIS).replace(tzinfo=None)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _parse_dt_value(value: str, params: dict[str, str]) -> Optional[tuple[datetime, bool]]:
    """Retourne (datetime naïf heure Paris, all_day)."""
    v = str(value or "").strip()
    if not v:
        return None
    if params.get("VALUE", "").upper() == "DATE" or (len(v) == 8 and v.isdigit()):
        try:
            d = datetime.strptime(v[:8], "%Y%m%d")
        except ValueError:
            return None
        return d, True
    is_utc = v.endswith("Z")
    core = v[:-1] if is_utc else v
    try:
        dt = datetime.strptime(core[:15], "%Y%m%dT%H%M%S")
    except ValueError:
        try:
            dt = datetime.strptime(core[:13], "%Y%m%dT%H%M")
        except ValueError:
            return None
    if is_utc:
        return _to_paris_naive(dt.replace(tzinfo=timezone.utc)), False
    tzid = params.get("TZID")
    if tzid and ZoneInfo is not None:
        try:
            return _to_paris_naive(dt.replace(tzinfo=ZoneInfo(tzid))), False
        except Exception:
            return dt, False
    return dt, False


def _parse_duration(value: str) -> Optional[timedelta]:
    s = str(value or "").strip().upper()
    if not s:
        return None
    sign = 1
    if s.startswith("-"):
        sign = -1
        s = s[1:]
    elif s.startswith("+"):
        s = s[1:]
    if not s.startswith("P"):
        return None
    s = s[1:]
    days = hours = mins = secs = weeks = 0
    num = ""
    in_time = False
    for ch in s:
        if ch == "T":
            in_time = True
            num = ""
            continue
        if ch.isdigit():
            num += ch
            continue
        try:
            n = int(num or "0")
        except ValueError:
            n = 0
        if ch == "W":
            weeks = n
        elif ch == "D":
            days = n
        elif ch == "H":
            hours = n
        elif ch == "M":
            if in_time:
                mins = n
            else:
                days += n * 30
        elif ch == "S":
            secs = n
        num = ""
    return sign * timedelta(
        weeks=weeks, days=days, hours=hours, minutes=mins, seconds=secs
    )


def _parse_rrule(value: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for part in str(value or "").split(";"):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        out[k.strip().upper()] = v.strip()
    return out


def parse_ics(text: str) -> list[dict]:
    """Extrait les VEVENT bruts d'un flux ICS."""
    events: list[dict] = []
    cur: Optional[dict] = None
    for line in _unfold(text):
        stripped = line.strip()
        upper = stripped.upper()
        if upper == "BEGIN:VEVENT":
            cur = {"exdates": [], "rrule": None, "recurrence_id": None}
            continue
        if upper == "END:VEVENT":
            if cur is not None:
                events.append(cur)
            cur = None
            continue
        if cur is None:
            continue
        prop = _split_prop(stripped)
        if not prop:
            continue
        name, params, value = prop
        if name == "DTSTART":
            parsed = _parse_dt_value(value, params)
            if parsed:
                cur["dtstart"], cur["all_day"] = parsed
        elif name == "DTEND":
            parsed = _parse_dt_value(value, params)
            if parsed:
                cur["dtend"] = parsed[0]
        elif name == "DURATION":
            dur = _parse_duration(value)
            if dur is not None:
                cur["duration"] = dur
        elif name == "SUMMARY":
            cur["summary"] = _unescape_text(value).strip()
        elif name == "DESCRIPTION":
            cur["description"] = _unescape_text(value).strip()
        elif name == "LOCATION":
            cur["location"] = _unescape_text(value).strip()
        elif name == "UID":
            cur["uid"] = value.strip()
        elif name == "STATUS":
            cur["status"] = value.strip().upper()
        elif name == "RRULE":
            cur["rrule"] = _parse_rrule(value)
        elif name == "EXDATE":
            for chunk in value.split(","):
                parsed = _parse_dt_value(chunk, params)
                if parsed:
                    cur["exdates"].append(parsed[0])
        elif name == "RECURRENCE-ID":
            parsed = _parse_dt_value(value, params)
            if parsed:
                cur["recurrence_id"] = parsed[0]
    return [e for e in events if e.get("dtstart")]


# --------------------------------------------------------------------------
# Expansion des récurrences
# --------------------------------------------------------------------------


def _add_months(d: datetime, n: int) -> datetime:
    y = d.year + (d.month - 1 + n) // 12
    m = (d.month - 1 + n) % 12 + 1
    day = d.day
    while day > 0:
        try:
            return d.replace(year=y, month=m, day=day)
        except ValueError:
            day -= 1
    return d


def _byday_matches(dt: datetime, byday: list[str]) -> bool:
    """BYDAY mensuel/annuel : gère les ordinaux (3TH, -1FR)."""
    for token in byday:
        t = token.strip().upper()
        if not t:
            continue
        code = t[-2:]
        if code not in WEEKDAY_CODES:
            continue
        if WEEKDAY_CODES[code] != dt.weekday():
            continue
        ordinal_raw = t[:-2]
        if not ordinal_raw:
            return True
        try:
            ordinal = int(ordinal_raw)
        except ValueError:
            continue
        if ordinal > 0:
            if (dt.day - 1) // 7 + 1 == ordinal:
                return True
        else:
            last = _month_last_day(dt.year, dt.month)
            if (last - dt.day) // 7 + 1 == -ordinal:
                return True
    return False


def _month_last_day(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (date(year, month + 1, 1) - timedelta(days=1)).day


def _month_candidates(
    year: int,
    month: int,
    ref: datetime,
    byday: list[str],
    bymonthday: list[int],
) -> list[datetime]:
    """Jours retenus dans un mois donné pour une règle MONTHLY / YEARLY."""
    last = _month_last_day(year, month)
    out: list[datetime] = []
    if byday:
        for day in range(1, last + 1):
            cand = ref.replace(year=year, month=month, day=day)
            if _byday_matches(cand, byday):
                out.append(cand)
    elif bymonthday:
        wanted = sorted({d if d > 0 else last + 1 + d for d in bymonthday})
        for day in wanted:
            if 1 <= day <= last:
                out.append(ref.replace(year=year, month=month, day=day))
    else:
        day = min(ref.day, last)
        out.append(ref.replace(year=year, month=month, day=day))
    return sorted(out)


def _rrule_occurrences(
    start: datetime, rule: dict[str, Any], win_start: datetime, win_end: datetime
) -> list[datetime]:
    freq = str(rule.get("FREQ") or "").upper()
    if freq not in ("DAILY", "WEEKLY", "MONTHLY", "YEARLY"):
        return [start]
    try:
        interval = max(1, int(rule.get("INTERVAL") or 1))
    except ValueError:
        interval = 1
    count_raw = rule.get("COUNT")
    try:
        count = int(count_raw) if count_raw else None
    except ValueError:
        count = None
    until: Optional[datetime] = None
    if rule.get("UNTIL"):
        parsed = _parse_dt_value(str(rule["UNTIL"]), {})
        if parsed:
            until = parsed[0]
    byday = [x.strip() for x in str(rule.get("BYDAY") or "").split(",") if x.strip()]
    bymonthday = [
        int(x)
        for x in str(rule.get("BYMONTHDAY") or "").split(",")
        if x.strip().lstrip("-").isdigit()
    ]
    bymonth = [
        int(x) for x in str(rule.get("BYMONTH") or "").split(",") if x.strip().isdigit()
    ]

    out: list[datetime] = []
    emitted = 0

    def _push(occ: datetime) -> bool:
        """Retourne False quand l'expansion doit s'arrêter."""
        nonlocal emitted
        if occ < start:
            return True
        if until and occ > until:
            return False
        if count is not None and emitted >= count:
            return False
        emitted += 1
        if occ > win_end:
            return False
        if occ >= win_start:
            out.append(occ)
        return len(out) < MAX_OCCURRENCES

    if freq == "DAILY":
        cur = start
        guard = 0
        while guard < MAX_OCCURRENCES * 6:
            guard += 1
            if bymonth and cur.month not in bymonth:
                cur = cur + timedelta(days=interval)
                continue
            if not _push(cur):
                return out
            cur = cur + timedelta(days=interval)
            if cur > win_end and count is None:
                return out
        return out

    if freq == "WEEKLY":
        wanted = sorted(
            {
                WEEKDAY_CODES[d.upper()[-2:]]
                for d in byday
                if d.upper()[-2:] in WEEKDAY_CODES
            }
        ) or [start.weekday()]
        cur_week = start - timedelta(days=start.weekday())
        guard = 0
        while guard < MAX_OCCURRENCES * 4:
            guard += 1
            for wd in wanted:
                occ = (cur_week + timedelta(days=wd)).replace(
                    hour=start.hour, minute=start.minute, second=start.second
                )
                if bymonth and occ.month not in bymonth:
                    continue
                if not _push(occ):
                    return out
            cur_week = cur_week + timedelta(weeks=interval)
            if cur_week > win_end and count is None:
                return out
        return out

    if freq == "MONTHLY":
        cursor = start.replace(day=1)
        guard = 0
        while guard < MAX_OCCURRENCES * 2:
            guard += 1
            if not bymonth or cursor.month in bymonth:
                for occ in _month_candidates(
                    cursor.year, cursor.month, start, byday, bymonthday
                ):
                    if not _push(occ):
                        return out
            cursor = _add_months(cursor, interval)
            if cursor > win_end and count is None:
                return out
        return out

    # YEARLY
    months = sorted(bymonth) or [start.month]
    year = start.year
    guard = 0
    while guard < MAX_OCCURRENCES * 2:
        guard += 1
        for mth in months:
            for occ in _month_candidates(year, mth, start, byday, bymonthday):
                if not _push(occ):
                    return out
        year += interval
        if datetime(year, 1, 1) > win_end and count is None:
            return out
    return out


def expand_events(
    raw_events: list[dict], win_start: date, win_end: date
) -> list[dict]:
    """Développe les VEVENT (récurrences comprises) sur [win_start, win_end]."""
    w0 = datetime(win_start.year, win_start.month, win_start.day)
    w1 = datetime(win_end.year, win_end.month, win_end.day, 23, 59, 59)

    overrides: dict[tuple[str, str], dict] = {}
    for ev in raw_events:
        rid = ev.get("recurrence_id")
        if rid and ev.get("uid"):
            overrides[(str(ev["uid"]), rid.strftime("%Y%m%dT%H%M%S"))] = ev

    out: list[dict] = []
    for ev in raw_events:
        if str(ev.get("status") or "") == "CANCELLED":
            continue
        start = ev.get("dtstart")
        if not start:
            continue
        all_day = bool(ev.get("all_day"))
        end = ev.get("dtend")
        if end is None and ev.get("duration") is not None:
            end = start + ev["duration"]
        if end is None:
            end = start + (timedelta(days=1) if all_day else timedelta(hours=1))
        if all_day:
            # DTEND est exclusif pour une date pure.
            end = end - timedelta(days=1)
            if end < start:
                end = start
            end = end.replace(hour=23, minute=59, second=0)
        if end < start:
            end = start
        length = end - start

        exdates = {d.strftime("%Y%m%dT%H%M%S") for d in (ev.get("exdates") or [])}
        exdates |= {d.strftime("%Y%m%d") for d in (ev.get("exdates") or [])}

        rule = ev.get("rrule")
        if ev.get("recurrence_id") and rule is None:
            occurrences = [start]
        elif rule:
            occurrences = list(_rrule_occurrences(start, rule, w0, w1))
        else:
            occurrences = [start]

        uid = str(ev.get("uid") or "")
        for occ in occurrences:
            key_full = occ.strftime("%Y%m%dT%H%M%S")
            if key_full in exdates or occ.strftime("%Y%m%d") in exdates:
                continue
            if rule and uid and (uid, key_full) in overrides:
                continue
            occ_end = occ + length
            if occ_end < w0 or occ > w1:
                continue
            out.append(
                {
                    "uid": uid or f"{key_full}-{ev.get('summary') or ''}",
                    "summary": ev.get("summary") or "Sans titre",
                    "description": ev.get("description") or "",
                    "location": ev.get("location") or "",
                    "start": occ,
                    "end": occ_end,
                    "all_day": all_day,
                    "occurrence_key": key_full,
                }
            )
    out.sort(key=lambda e: (e["start"], e["summary"]))
    return out


def events_from_ics(text: str, win_start: date, win_end: date) -> list[dict]:
    return expand_events(parse_ics(text), win_start, win_end)
