"""Fix 2015 general per-county precinct files (issue #91, precinct-file side).

Verified against the official 2015 General county Official Recapitulation PDFs
(recovered via Wayback; see 2015/20151103-general-precinct-vs-county-discrepancies.md).
Applies to 2015/counties/20151103__ms__general__<county>__precinct.csv only:
  1. drop county-total rows embedded as precincts (DeSoto '600 DE SOTO MS'/'600 DESOTO
     MS', Holmes 'HOLMES MS') — values equal the county totals exactly
  2. drop turnout rows (office 'Registered Voters' / 'Ballots Cast' — DeSoto, Pike,
     Rankin) — not results
  3. drop 'X' vote cells (Tishomingo State House rows; out-of-district cells)
  4. unify candidate spellings to the certified spellings (county-file TOTAL rows),
     matched by unique last name within (office, district)
  5. correct party labels to the certified party per candidate (Amite-area State
     Auditor swap, Hinds SD27/SD29, Itawamba SD5, Pike SD37, House 16/23/27/53/87/100,
     Marshall House 5, Hinds/Pearl River/Alcorn McFarland rows, Rankin strays)
  6. swap transposed candidate labels (values stay in place): Clay/Covington/Lafayette
     Governor Bryant<->Gray, Leflore State Auditor Pickering<->Pritchett (verified:
     ours' cells sum exactly to the county file's pair totals, county file = official)
  7. restore Tishomingo 'Springhill' rows whose values were duplicated from 'Paden'
     (official Tishomingo.pdf p.3 Springhill column)
Write-in rows are NOT touched. County-level file is NOT modified.
NOTE: rules 1-5 and 7 are idempotent (compare-and-skip), but rule 6's label swap is
NOT — run this script once, from a clean checkout.
"""
import csv
import collections
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERAL_DIR = os.path.join(ROOT, '2015', 'counties')

# rule 1: total rows embedded as precincts
TOTAL_PRECINCT_RE = {
    'DeSoto': re.compile(r'^600 DE ?SOTO MS$', re.I),
    'Holmes': re.compile(r'^HOLMES MS$', re.I),
}
# rule 2: turnout rows, carried in the office field
TURNOUT_OFFICES = {'Registered Voters', 'Ballots Cast'}
# rule 7: Tishomingo Springhill restoration (official recap p.3, Springhill column)
SPRINGHILL = {
    ('Lieutenant Governor', 'Democrat', 'Tim Johnson'): 92,
    ('Lieutenant Governor', 'Republican', 'Tate Reeves'): 245,
    ('Lieutenant Governor', 'Libertarian', 'Ron Williams'): 21,
    ('Lieutenant Governor', 'Reform', 'Rosa B. Williams'): 6,
    ('Secretary of State', 'Democrat', 'Charles E. Graham'): 93,
    ('Secretary of State', 'Republican', 'Delbert Hosemann'): 258,
    ('Secretary of State', 'Reform', 'Randy Walker'): 24,
    ('Attorney General', 'Democrat', 'Jim Hood'): 180,
    ('Attorney General', 'Republican', 'Mike Hurst'): 194,
    ('State Auditor', 'Republican', 'Stacey E. Pickering'): 259,
    ('State Auditor', 'Democrat', "Jocelyn 'Joce' Pepper Pritchett"): 95,
    ('State Auditor', 'Reform', 'Lajena Walley'): 13,
}

def np_(p):
    p = (p or '').strip().lower()
    for pre, code in [('rep', 'Republican'), ('dem', 'Democrat'), ('lib', 'Libertarian'),
                      ('ref', 'Reform'), ('con', 'Constitution'), ('ind', 'Independent'),
                      ('gre', 'Green')]:
        if p.startswith(pre):
            return code
    return (p or 'nonpartisan').capitalize()

def nk_(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())

def lev(a, b):
    """Levenshtein distance, small strings."""
    if abs(len(a) - len(b)) > 2:
        return 99
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[-1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]

ORDINAL_RE = re.compile(r'^(?:[IVX]{1,4}|Sr|Jr)\.?$', re.I)

def strip_ordinals(words):
    return [w for w in words if not ORDINAL_RE.fullmatch(w)]

cert = {}  # (office_nk, dist, cand_nk) -> (certified name raw, certified party full name)
cf = os.path.join(ROOT, '2015', '20151103__ms__general.csv')
for r in csv.reader(open(cf, newline='')):
    if nk_(r[0]) != 'total':
        continue
    words = re.sub(r"[^A-Za-z ']", '', r[4]).split()
    core = [w for w in words if not ORDINAL_RE.fullmatch(w)]
    cert[(nk_(r[1]), (r[2].strip().lstrip('0') or 'Z'),
          re.sub(r'[^a-z0-9]', '', ' '.join(core).lower()))] = (r[4], np_(r[3]))

def slot_certs(office_nk, dist):
    return {ck: v for (ok, d, ck), v in cert.items() if ok == office_nk and d == dist}

# a few variants that no mechanical rule can reach (different surname spelling)
EXPLICIT_RENAMES = {'Rosa B. Walker': 'Rosa B. Williams'}

# transposed-candidate label swaps: county -> office -> (candidate A, candidate B)
SWAPS = {
    'Clay': [('Governor', ('Phil Bryant', 'Robert Gray'))],
    'Covington': [('Governor', ('Phil Bryant', 'Robert Gray')),
                  ('State Auditor', ('Stacey E. Pickering', "Jocelyn 'Joce' Pepper Pritchett"))],
    'Lafayette': [('Governor', ('Phil Bryant', 'Robert Gray')),
                  ('State Auditor', ('Stacey E. Pickering', "Jocelyn 'Joce' Pepper Pritchett"))],
    'Leflore': [('State Auditor', ('Stacey E. Pickering', "Jocelyn 'Joce' Pepper Pritchett"))],
}

# explicit per-cell corrections transcribed from the official recaps
CELL_FIXES = {
    # Tishomingo State Auditor Pritchett cells (Tishomingo.pdf p.2–3; ours drifted
    # Iuka 315->325 and Coles Mill 67->27)
    ('Tishomingo', 'Iuka', 'State Auditor', "Jocelyn 'Joce' Pepper Pritchett"): 315,
    ('Tishomingo', 'Coles Mill', 'State Auditor', "Jocelyn 'Joce' Pepper Pritchett"): 67,
}

log = []
seen_renames = set()
def note(msg):
    log.append(msg)
    print(msg)

def process_path(path):
    raw = open(path, 'rb').read()
    eol = '\r\n' if b'\r\n' in raw else '\n'
    with open(path, newline='') as f:
        rows = list(csv.reader(f))
    header, data = rows[0], rows[1:]
    col = {name: i for i, name in enumerate(h.strip().lower() for h in header)}
    need = ('county', 'precinct', 'office', 'district', 'party', 'candidate', 'votes')
    if any(n not in col for n in need):
        # candidate-first layouts store county/precinct later; map by content if header lacks them
        # (benton/bolivar/tippah/sunflower/quitman/smith/stone/tallahatchie have all names present)
        note(f"SKIP {os.path.basename(path)}: header {header}")
        return 0
    i_c, i_p, i_o, i_d, i_pt, i_ca, i_v = (col[n] for n in need)
    county_name_col = i_c if header[i_c].strip().lower() == 'county' else i_c

    changes = collections.Counter()
    out = []
    for r in data:
        r = list(r)
        county, precinct, office = r[i_c], r[i_p].strip(), r[i_o]
        dist = (r[i_d].strip().lstrip('0') or 'Z')
        cand, party = r[i_ca], np_(r[i_pt])
        votes = r[i_v].strip()

        # rule 1: embedded county-total rows
        if county in TOTAL_PRECINCT_RE and TOTAL_PRECINCT_RE[county].fullmatch(precinct):
            changes['dropped-total-row'] += 1
            continue
        # rule 2: turnout rows
        if office in TURNOUT_OFFICES:
            changes['dropped-turnout-row'] += 1
            continue
        # rule 3: X cells (out-of-district)
        if votes == 'X':
            changes['dropped-X-row'] += 1
            continue
        # turnout rows can also appear with an office as normal, turnout in the
        # candidate field (Pike State Senate 37: party blank, candidate 'Registered')
        if cand.strip() in ('Registered', 'Ballots', 'Registered Voters', 'Ballots Cast'):
            changes['dropped-turnout-row'] += 1
            continue

        # rule 4+5: candidate spelling and party, only for candidates known to the
        # certified office slot
        cnk = nk_(cand)
        if cand in EXPLICIT_RENAMES and re.search(r'[A-Za-z]', r[i_o]):
            target = EXPLICIT_RENAMES[cand]
            slot_key = (nk_(r[i_o]), dist, nk_(target))
            r[i_ca] = target
            changes['renamed-candidate'] += 1
            if slot_key in cert and cert[slot_key][1] != party:
                r[i_pt] = cert[slot_key][1]
                changes['fixed-party'] += 1
            continue
        slot = slot_certs(nk_(office), dist)
        if cnk in slot:
            cname, cparty = slot[cnk]
            if cname != cand:
                r[i_ca] = cname
                changes['renamed-candidate'] += 1
            if cparty != party:
                r[i_pt] = cparty
                changes['fixed-party'] += 1
        else:
            # unique match to a certified name: full-nk edit distance (ordinals
            # stripped on both sides), else unique ordinal-striped suffix
            words = re.sub(r"[^A-Za-z ']", '', cand).split()
            core = [w for w in words if not ORDINAL_RE.fullmatch(w)]
            own_core_nk = re.sub(r'[^a-z0-9]', '', ' '.join(core).lower())
            ln = re.sub(r'[^a-z0-9]', '', (core[-1] if core else '').lower())
            near_hits = [ck for ck in slot if lev(own_core_nk, ck) <= 2] if own_core_nk else []
            suffix_hits = [ck for ck in slot if len(ln) >= 3 and ck.endswith(ln)]
            hits = near_hits if len(near_hits) == 1 else list(dict.fromkeys(suffix_hits))
            if len(hits) == 1:
                cname, cparty = slot[hits[0]]
                changed_flag = False
                if cname != cand:
                    r[i_ca] = cname
                    changes['renamed-candidate'] += 1
                    changed_flag = True
                if cparty != party:
                    r[i_pt] = cparty
                    changes['fixed-party'] += 1
                    changed_flag = True
                if changed_flag and (cand, cname, party, cparty) not in seen_renames:
                    seen_renames.add((cand, cname, party, cparty))
                    note(f"  {os.path.basename(path)}: {cand!r} -> {cname!r}, party {party}->{cparty}")
            elif not hits:
                if ('UNMATCHED', cand) not in seen_renames:
                    seen_renames.add(('UNMATCHED', cand))
                    note(f"  {os.path.basename(path)}: UNMATCHED candidate {cand!r} "
                         f"(office={r[i_o]!r} dist={r[i_d]!r}) left as-is")

        # rule 6: transposed labels (applied per row below, in a second pass)
        cfk = (county, precinct.strip(), r[i_o], r[i_ca].strip())
        if cfk in CELL_FIXES and r[i_v].strip() != str(CELL_FIXES[cfk]):
            r[i_v] = str(CELL_FIXES[cfk])
            changes['cell-fix'] += 1
        out.append(r)

    # rule 6 second pass: swap (candidate, party) between the pair within each precinct
    if county_name_col is not None:
        county = out[0][i_c].strip() if out else ''
        for office_name, (a, b) in SWAPS.get(county, []):
            groups = collections.defaultdict(dict)
            for idx, r in enumerate(out):
                if r[i_o] == office_name:
                    key = (r[i_c], r[i_p].strip(), (r[i_d].strip().lstrip('0') or 'Z'))
                    groups[key][r[i_ca].strip()] = idx
            sw = 0
            for key, members in sorted(groups.items()):
                if a.strip() in members and b.strip() in members and len(members) >= 2:
                    ia, ib = members[a.strip()], members[b.strip()]
                    out[ia][i_ca], out[ia][i_pt], out[ib][i_ca], out[ib][i_pt] = (
                        out[ib][i_ca], out[ib][i_pt], out[ia][i_ca], out[ia][i_pt])
                    sw += 1
                else:
                    note(f"  {os.path.basename(path)}: swap skipped {key} members={sorted(members)}")
            changes['swapped-pairs'] = sw

    # rule 7: Tishomingo Springhill restoration
    if 'Tishomingo' in {r[i_c] for r in out}:
        rest = 0
        for r in out:
            if r[i_c] == 'Tishomingo' and r[i_p].strip() == 'Springhill':
                key = (r[i_o], r[i_pt], r[i_ca])
                if key in SPRINGHILL and r[i_v].strip() != str(SPRINGHILL[key]):
                    r[i_v] = str(SPRINGHILL[key])
                    rest += 1
        changes['springhill-restored'] = rest

    if any(changes.values()):
        with open(path, 'w', newline='') as f:
            w = csv.writer(f, lineterminator=eol)
            w.writerow(header)
            w.writerows(out)
    note(f"{os.path.basename(path)}: {dict(changes)}")
    return sum(changes.values())

total = 0
for path in sorted(glob.glob(os.path.join(GENERAL_DIR, '20151103__ms__general__*__precinct.csv'))):
    total += process_path(path)
note(f"TOTAL field changes: {total}")