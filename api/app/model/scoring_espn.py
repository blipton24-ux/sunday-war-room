"""ESPN's scoring rules, scored with our own stats (ADR-053).

ESPN describes a league's scoring as a list of `{statId, points, pointsOverrides}`. Three facts
about that list drive this module (earlier-project lessons, rewritten here):

* **ESPN omits zero-valued rules.** A missing "18-21 points allowed" tier means it scores
  nothing, so ladders are the full fixed ladders and a league only selects values within them.
* **A field-goal ladder is open at the top.** A league with a 50-59 yard value but no 60+ value
  scores 50-yard-and-longer kicks at it. `expand_espn` renames the top configured band to its
  open-ended form (`espn:FG50+`) so the registry stays static and `scoring_key` stays stable.
* **Per-position values** ride in `pointsOverrides`, keyed by lineup slot: a tight-end premium is
  `espn:REC@TE`. They replace the base value for that position (app/model/scoring.py).

Every rule is either scored or explained: `unsupported_reason` says why a rule we cannot score
(individual defenders, punters, head coaches, season-rate stats, anything our free data does not
carry) is not. Keys are `espn:<ABBREVIATION>`; a stat id we have never seen is `espn:STAT<id>`
and is reported, never dropped.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.model.scoring import (
    DEFENSE,
    KICKER,
    OFFENSE,
    Rule,
    col,
    per_unit,
    total,
)

PREFIX = "espn:"


def _words(text: str) -> list[str]:
    """A table written as space-separated words (reads better than hundreds of quoted strings)."""
    return text.split()


# --------------------------------------------------------------------------- ESPN's catalogue
# Stat id -> ESPN's abbreviation, in id order (0..234): the ids ESPN uses in scoringItems.
_ABBR_0_216 = _words("""
PA PC INC PY PTD PY5 PY10 PY20 PY25 PY50 PY100 PC5 PC10 IP5 IP10 PTD40 PTD50 P300 P400 2PC INTT
CPCT PYPG RA RY RTD 2PR RY5 RY10 RY20 RY25 RY50 R100 RA5 RA10 RTD40 RTD50 RY100 RY200 RYPA RYPG
RECS REY RETD 2PRE RETD40 RETD50 REY5 REY10 REY20 REY25 REY50 RE100 REC REC5 REC10 REY100 REY200
RET YAC YPC REYPG PTL FTD SKD PFUM RFUM REFUM FUM PFUML RFUML REFUML FUML TT FG50P FGA50P FGM50P
FG40 FGA40 FGM40 FG0 FGA0 FGM0 FG FGA FGM PAT PATA PATM PA0 PA1 PA7 PA14 BLKKRTD DEFRETTD INT FR
BLKK SF SK HALFSK KRTD PRTD INTTD FRTD TRTD FF TKA TKS TK TK3 TK5 STF PD KR PR KR10 KR25 PR10
PR25 PTSA PA18 PA22 PA28 PA35 PA46 PAPG YA YA100 YA199 YA299 YA349 YA399 YA449 YA499 YA549 YA550
YAPG PT PTY PT10 PT20 PTB PTR PTRY PTTB PTFC PTAVG PTA44 PTA42 PTA40 PTA38 PTA36 PTA34 PTA33 TW
TL TIE PTS PPG MGN WM25 WM20 WM15 WM10 WM5 WM1 LM1 LM5 LM10 LM15 LM20 LM25 MGNPG WINPCT PTD0
PTD10 PTD20 PTD30 RTD0 RTD10 RTD20 RTD30 RETD0 RETD10 RETD20 RETD30 DPTSA DPA0 DPA1 DPA7 DPA14
DPA18 DPA22 DPA28 DPA35 DPA46 DPAPG FG50 FGA50 FGM50 FG60 FGA60 FGM60 O2PRET D2PRET 2PRET O1PSF
D1PSF 1PSF GP PFD RFD REFD FGY FGMY FGAY
""")
_DISTANCE_STEPS = ("5", "10", "20", "25", "50", "100")
_ABBR_217_234 = [f"{family}{n}" for family in ("FGY", "FGMY", "FGAY") for n in _DISTANCE_STEPS]

STAT_ABBR: dict[int, str] = {i: a for i, a in enumerate(_ABBR_0_216 + _ABBR_217_234)}
STAT_COUNT = 235  # ESPN's catalogue as of the 2026 season; a test fails if this table drifts

# ESPN lineup slot id -> the position it stands for (pointsOverrides are keyed by slot).
SLOT_POSITION: dict[int, str] = {0: "QB", 2: "RB", 4: "WR", 6: "TE", 16: "DEF", 17: "K"}


def abbr_for(stat_id: int) -> str:
    return STAT_ABBR.get(stat_id, f"STAT{stat_id}")


# --------------------------------------------------------------------------- the rules
def _attempts_minus_completions(df):  # type: ignore[no-untyped-def]
    return col("attempts")(df) - col("completions")(df)


_FUM_LOST = ("rushing_fumbles_lost", "receiving_fumbles_lost", "sack_fumbles_lost")
_RETURNS = OFFENSE  # returner yardage; a team defense's return yards are not in the free data
_FG_MADE = {
    "0": ("fg_made_0_19", "fg_made_20_29", "fg_made_30_39"),
    "40": ("fg_made_40_49",),
    "50": ("fg_made_50_59",),
    "60": ("fg_made_60_",),
}
_FG_MISSED = {
    "0": ("fg_missed_0_19", "fg_missed_20_29", "fg_missed_30_39"),
    "40": ("fg_missed_40_49",),
    "50": ("fg_missed_50_59",),
    "60": ("fg_missed_60_",),
}
_BANDS = ("0", "40", "50", "60")

ESPN_RULES: dict[str, Rule] = {}


def _add(abbr: str, rule: Rule) -> None:
    ESPN_RULES[PREFIX + abbr] = rule


# per unit: points x a count
for _abbr, _q in {
    "PA": col("attempts"),
    "PC": col("completions"),
    "INC": _attempts_minus_completions,
    "PY": col("passing_yards"),
    "PTD": col("passing_tds"),
    "INTT": col("passing_interceptions"),
    "2PC": col("passing_2pt_conversions"),
    "RA": col("carries"),
    "RY": col("rushing_yards"),
    "RTD": col("rushing_tds"),
    "2PR": col("rushing_2pt_conversions"),
    "RECS": col("receptions"),  # ESPN's older twin of REC
    "REC": col("receptions"),
    "REY": col("receiving_yards"),
    "RETD": col("receiving_tds"),
    "2PRE": col("receiving_2pt_conversions"),
    "RET": col("targets"),
    "PTL": total("passing_2pt_conversions", "rushing_2pt_conversions", "receiving_2pt_conversions"),
    "SKD": col("sacks_suffered"),
    "FUM": col("fumbles_total"),
    "PFUML": col("sack_fumbles_lost"),
    "RFUML": col("rushing_fumbles_lost"),
    "REFUML": col("receiving_fumbles_lost"),
    "FUML": total(*_FUM_LOST),
    "TT": total("passing_interceptions", *_FUM_LOST),
    "PFD": col("passing_first_downs"),
    "RFD": col("rushing_first_downs"),
    "REFD": col("receiving_first_downs"),
    "KR": col("kickoff_return_yards"),
    "PR": col("punt_return_yards"),
}.items():
    _add(_abbr, per_unit(_q, OFFENSE))

# kicking
_add("PAT", per_unit(col("pat_made"), KICKER))
_add("PATA", per_unit(col("pat_att"), KICKER))
_add("PATM", per_unit(col("pat_missed"), KICKER))
_add("FG", per_unit(col("fg_made"), KICKER))
_add("FGA", per_unit(col("fg_att"), KICKER))
_add("FGM", per_unit(col("fg_missed"), KICKER))
_add("FG50P", per_unit(total(*_FG_MADE["50"], *_FG_MADE["60"]), KICKER))
_add("FGM50P", per_unit(total(*_FG_MISSED["50"], *_FG_MISSED["60"]), KICKER))
_add(
    "FGA50P",
    per_unit(total(*_FG_MADE["50"], *_FG_MADE["60"], *_FG_MISSED["50"], *_FG_MISSED["60"]), KICKER),
)
for _i, _band in enumerate(_BANDS):
    _made, _missed = _FG_MADE[_band], _FG_MISSED[_band]
    _above_made = tuple(c for b in _BANDS[_i:] for c in _FG_MADE[b])  # this band and longer
    _above_missed = tuple(c for b in _BANDS[_i:] for c in _FG_MISSED[b])
    for _prefix, _cols, _open in (
        ("FG", _made, _above_made),
        ("FGM", _missed, _above_missed),
        ("FGA", _made + _missed, _above_made + _above_missed),
    ):
        _add(f"{_prefix}{_band}", per_unit(total(*_cols), KICKER))
        if _band != "60":  # FG60 is already open-ended
            _add(f"{_prefix}{_band}+", per_unit(total(*_open), KICKER))

# step: points x whole steps of a stat per game ("every 10 rushing yards")
for _abbr, (_column, _size) in {
    **{f"PY{n}": ("passing_yards", int(n)) for n in ("5", "10", "20", "25", "50", "100")},
    **{f"RY{n}": ("rushing_yards", int(n)) for n in ("5", "10", "20", "25", "50")},
    **{f"REY{n}": ("receiving_yards", int(n)) for n in ("5", "10", "20", "25", "50")},
    "R100": ("rushing_yards", 100),
    "RE100": ("receiving_yards", 100),
    "PC5": ("completions", 5),
    "PC10": ("completions", 10),
    "RA5": ("carries", 5),
    "RA10": ("carries", 10),
    "REC5": ("receptions", 5),
    "REC10": ("receptions", 10),
    "KR10": ("kickoff_return_yards", 10),
    "KR25": ("kickoff_return_yards", 25),
    "PR10": ("punt_return_yards", 10),
    "PR25": ("punt_return_yards", 25),
}.items():
    _add(_abbr, Rule("step", col(_column), OFFENSE, step=float(_size)))
for _abbr, _size in {"IP5": 5, "IP10": 10}.items():
    _add(_abbr, Rule("step", _attempts_minus_completions, OFFENSE, step=float(_size)))

# player game bonuses: points once if the game total lands in the range. ESPN's labels are
# literal ("300-399 yard passing game"), so a 420-yard game earns nothing from P300.
for _abbr, (_column, _lo, _hi) in {
    "P300": ("passing_yards", 300, 399),
    "P400": ("passing_yards", 400, float("inf")),
    "RY100": ("rushing_yards", 100, 199),
    "RY200": ("rushing_yards", 200, float("inf")),
    "REY100": ("receiving_yards", 100, 199),
    "REY200": ("receiving_yards", 200, float("inf")),
}.items():
    _add(_abbr, Rule("range", col(_column), OFFENSE, lo=_lo, hi=_hi))

# team defense: counts
for _abbr, _q in {
    "SK": col("def_sacks"),
    "INT": col("def_interceptions"),
    "FR": col("fumble_recovery_opp"),
    "SF": col("def_safeties"),
    "BLKK": total("def_fg_blocks", "def_punt_blocks", "def_pat_blocks"),
    "PTSA": col("points_allowed"),
}.items():
    _add(_abbr, per_unit(_q, DEFENSE))

# team defense: points-allowed ladder, each tier literal (a tier a league omits scores nothing)
for _abbr, (_lo, _hi) in {
    "PA0": (0, 0),
    "PA1": (1, 6),
    "PA7": (7, 13),
    "PA14": (14, 17),
    "PA18": (18, 21),
    "PA22": (22, 27),
    "PA28": (28, 34),
    "PA35": (35, 45),
    "PA46": (46, float("inf")),
}.items():
    _add(_abbr, Rule("range", col("points_allowed"), DEFENSE, lo=_lo, hi=_hi))

# Touchdown groups. nflverse gives only two team totals (`def_tds`, `special_teams_tds`) and does
# not say whether a score came off an interception, a fumble or a block, while ESPN scores them
# separately. Scoring every member against the same total would multiply one touchdown, so a
# group is scored ONCE, at the value its configured members share; members with different values
# cannot be told apart and are reported instead (expand_espn).
TOUCHDOWN_GROUPS: dict[str, tuple[str, ...]] = {
    "def_tds": ("INTTD", "FRTD", "BLKKRTD", "DEFRETTD"),
    "special_teams_tds": ("KRTD", "PRTD", "FTD", "TRTD"),
}
_add("def_tds", per_unit(col("def_tds"), DEFENSE))
_add("special_teams_tds", per_unit(col("special_teams_tds"), OFFENSE | DEFENSE))


#  what we don't score
IDP = frozenset(_words("TKA TKS TK TK3 TK5 STF PD FF HALFSK"))
PUNTER = frozenset(
    _words("PT PTY PT10 PT20 PTB PTR PTRY PTTB PTFC PTA44 PTA42 PTA40 PTA38 PTA36 PTA34 PTA33")
)
HEAD_COACH = frozenset(
    _words("TW TL TIE PTS MGN WM25 WM20 WM15 WM10 WM5 WM1 LM1 LM5 LM10 LM15 LM20 LM25")
)
RATES = frozenset(_words("CPCT PYPG RYPA RYPG YPC REYPG PAPG YAPG DPAPG PTAVG PPG MGNPG WINPCT"))
# Needs a stat the free feeds do not carry (yards allowed, play-by-play touchdown distances,
# field-goal yardage, per-split defensive points, fumbles that were not lost, ...).
_NOT_IN_DATA_NAMES = _words("""
YA YA100 YA199 YA299 YA349 YA399 YA449 YA499 YA549 YA550 YAC PFUM RFUM REFUM GP
DPTSA DPA0 DPA1 DPA7 DPA14 DPA18 DPA22 DPA28 DPA35 DPA46 O2PRET D2PRET 2PRET O1PSF D1PSF 1PSF
FGY FGMY FGAY PTD40 PTD50 RTD40 RTD50 RETD40 RETD50
PTD0 PTD10 PTD20 PTD30 RTD0 RTD10 RTD20 RTD30 RETD0 RETD10 RETD20 RETD30
""")
NOT_IN_DATA = frozenset(
    _NOT_IN_DATA_NAMES + [f"{f}{n}" for f in ("FGY", "FGMY", "FGAY") for n in _DISTANCE_STEPS]
)

REASONS = {
    "idp": "Individual defensive players aren't projected yet.",
    "punter": "Punters aren't projected yet.",
    "head_coach": "Head coaches aren't projected yet.",
    "rate": "A season-rate stat used by category leagues, not points leagues.",
    "not_in_data": "The free stat feeds don't carry this, so it can't be scored.",
    "touchdown_mix": (
        "This league scores different defensive or special-teams touchdowns differently, and the "
        "free stats don't say which kind each was."
    ),
    "unknown": "A scoring rule this app doesn't recognise.",
}


def unsupported_reason(key: str) -> str:
    """Why a rule key (`espn:ABBR`, `espn:ABBR@POS`) is not scored, as one plain sentence."""
    abbr = key.removeprefix(PREFIX).partition("@")[0].rstrip("+")
    for code, names in (
        ("idp", IDP),
        ("punter", PUNTER),
        ("head_coach", HEAD_COACH),
        ("rate", RATES),
        ("not_in_data", NOT_IN_DATA),
    ):
        if abbr in names:
            return REASONS[code]
    if any(abbr in members for members in TOUCHDOWN_GROUPS.values()):
        return REASONS["touchdown_mix"]
    return REASONS["unknown"]


# --------------------------------------------------------------------------- settings -> rules
def espn_rule(key: str) -> Rule | None:
    """The rule for `espn:ABBR` or `espn:ABBR@POS`, or None when we cannot score it."""
    name, sep, position = key.removeprefix(PREFIX).partition("@")
    base = ESPN_RULES.get(PREFIX + name)
    if base is None:
        return None
    if not sep:
        return base
    if position not in SLOT_POSITION.values():
        return None  # an override for a slot we can't name (e.g. FLEX) would silently do nothing
    return Rule(
        base.shape,
        base.quantity,
        base.positions,
        lo=base.lo,
        hi=base.hi,
        only_position=position,
        step=base.step,
    )


def _split(key: str) -> tuple[str, str]:
    name, sep, position = key.removeprefix(PREFIX).partition("@")
    return name, (sep + position)


def expand_espn(items: list[dict[str, object]]) -> dict[str, float]:
    """ESPN `scoringItems` -> our rule dict (`espn:` keys -> points).

    Base values and per-position overrides become keys; zero base values are dropped (ESPN omits
    them anyway) but zero overrides are kept, since they suppress the base value for that
    position. Then the open-ended field-goal ladders and the touchdown groups are resolved.
    """
    rules: dict[str, float] = {}
    for item in items:
        abbr = abbr_for(int(item["statId"]))  # type: ignore[call-overload]
        points = float(item.get("points") or 0.0)  # type: ignore[arg-type]
        if points:
            rules[f"{PREFIX}{abbr}"] = points
        overrides = item.get("pointsOverrides") or {}
        for slot, value in overrides.items():  # type: ignore[attr-defined]
            position = SLOT_POSITION.get(int(slot), f"SLOT{int(slot)}")
            rules[f"{PREFIX}{abbr}@{position}"] = float(value)
    return _resolve_touchdown_groups(_open_field_goal_ladders(rules))


def _open_field_goal_ladders(rules: dict[str, float]) -> dict[str, float]:
    """The last configured field-goal band absorbs every longer kick (ESPN's behaviour)."""
    out = dict(rules)
    for prefix in ("FG", "FGM", "FGA"):
        names = {f"{prefix}{band}": i for i, band in enumerate(_BANDS)}
        by_scope: dict[str, list[tuple[int, str]]] = {}
        for key, value in rules.items():
            name, scope = _split(key)
            if name in names and value:
                by_scope.setdefault(scope, []).append((names[name], key))
        for found in by_scope.values():
            top_index, top_key = max(found)
            if top_index < len(_BANDS) - 1:
                name, scope = _split(top_key)
                out[f"{PREFIX}{name}+{scope}"] = out.pop(top_key)
    return out


def _resolve_touchdown_groups(rules: dict[str, float]) -> dict[str, float]:
    out = dict(rules)
    for aggregate, members in TOUCHDOWN_GROUPS.items():
        configured = {m: out[PREFIX + m] for m in members if out.get(PREFIX + m)}
        if not configured:
            continue
        values = set(configured.values())
        if len(values) == 1:  # one shared value: score the aggregate once
            for member in configured:
                del out[PREFIX + member]
            out[PREFIX + aggregate] = values.pop()
        # different values: leave the members in place; they are reported as unsupported
    return out


def espn_abbreviations(rules: Mapping[str, float]) -> set[str]:
    """The ESPN abbreviations present in a rule dict (for coverage reports and tests)."""
    return {key.removeprefix(PREFIX).partition("@")[0].rstrip("+") for key in rules}
