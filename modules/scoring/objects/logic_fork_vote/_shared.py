"""@module scoring.objects.logic_fork_vote._shared — what the logic_fork_vote row classes share (constants, seeds, helpers); split from logic_fork_vote_basis.py (sap-2c)."""
from scoring.worldview_elections_basis import (
    ELECTION_MODES, _by_name, _parse, _rows,
    _tally_approval, _tally_ranked, _tally_sole,
)
import json

VOTE_STATUSES = ('open', 'closed')
def tally_logic_fork_vote(manager, vote_name):
    """The running (or final) tally for one LogicForkVote — same
    shape/semantics as tally_election()/tally_display_vote(), over
    fork-criterion candidates."""
    vote = _by_name(manager, 'LogicForkVote').get(vote_name)
    if vote is None:
        return {'ok': False,
                'error': f"no LogicForkVote named '{vote_name}'",
                'knownVotes': sorted(_by_name(manager, 'LogicForkVote'))}
    mode = getattr(vote, 'mode', 'sole')
    if mode not in ELECTION_MODES:
        return {'ok': False,
                'error': f"unknown mode '{mode}'",
                'modes': list(ELECTION_MODES)}
    candidates = _parse(
        getattr(vote, 'candidate_criterion_names_json', '[]'), '[]')
    if not candidates:
        return {'ok': False,
                'error': 'vote has no candidate criteria',
                'suggestion': {
                    'knob': 'candidate_criterion_names_json',
                    'action': 'name the LogicForkCriterion rows being '
                              'voted on for this fork'}}
    known_criteria = set(_by_name(manager, 'LogicForkCriterion'))
    unknown_candidates = [c for c in candidates if c not in known_criteria]
    ballots = [b for b in _rows(manager, 'LogicForkBallot')
               if getattr(b, 'vote_name', '') == vote_name]
    if not ballots:
        return {'ok': False,
                'error': 'no ballots cast',
                'candidates': candidates}

    pairwise = None
    if mode == 'approval':
        per, winners, weights, refused, note = _tally_approval(
            ballots, candidates)
        counted = len(ballots) - len(refused)
    elif mode == 'sole':
        per, winners, weights, refused, note = _tally_sole(
            ballots, candidates)
        counted = len(ballots) - len(refused)
    else:
        per, winners, weights, refused, note, pairwise, counted = \
            _tally_ranked(ballots, candidates)

    report = {
        'ok': True,
        'vote': vote_name,
        'displayName': getattr(vote, 'display_name', '') or vote_name,
        'decisionProcedure': getattr(vote, 'decision_procedure_name', ''),
        'fork': getattr(vote, 'fork_name', ''),
        'mode': mode,
        'status': getattr(vote, 'status', 'open'),
        'candidates': candidates,
        'unknownCandidates': unknown_candidates,
        'ballotsCast': len(ballots),
        'ballotsCounted': counted,
        'refusedBallots': refused,
        'results': per,
        'winners': winners,
        'weights': {c: round(w, 6) for c, w in weights.items()},
        'note': note,
        'suggestion': {
            'knob': f'POST /api/scoring/logic-fork-votes/{vote_name}/apply',
            'action': "close the vote (status = 'closed'), then apply "
                      'to record the winning criterion for this fork '
                      '(explicit, provenance-stamped)'},
    }
    if pairwise is not None:
        report['pairwise'] = pairwise
    return report
def apply_logic_fork_vote(manager, vote_name):
    """Write a CLOSED vote's winning criterion onto the LogicForkVote
    row itself. A tie refuses — a fork's decision criterion is
    singular by definition."""
    tally = tally_logic_fork_vote(manager, vote_name)
    if not tally.get('ok'):
        return tally
    if tally['status'] != 'closed':
        return {'ok': False,
                'error': f"vote '{vote_name}' is '{tally['status']}' "
                         '— only closed votes apply',
                'suggestion': {
                    'knob': 'LogicForkVote.status',
                    'action': "set 'closed' first (an explicit edit) "
                              'so the applied result is final'}}
    if len(tally['winners']) != 1:
        return {'ok': False,
                'error': f"{len(tally['winners'])} winners tied "
                         f"({', '.join(tally['winners']) or 'none'}) "
                         "— a fork's decision criterion is singular; "
                         're-vote or break the tie explicitly rather '
                         'than picking one arbitrarily',
                'winners': tally['winners']}
    vote = _by_name(manager, 'LogicForkVote').get(vote_name)
    winner = tally['winners'][0]
    vote.elected_criterion_name = winner
    vote.elected_provenance = (
        f"vote-derived from '{vote_name}' ({tally['mode']}, "
        f"{tally['ballotsCounted']} ballots counted)")
    try:
        manager.db.saveInstanceInDB(vote)
    except Exception:
        pass  # in-memory managers (selftests) have no db
    return {'ok': True,
            'vote': vote_name,
            'decisionProcedure': tally['decisionProcedure'],
            'fork': tally['fork'],
            'electedCriterion': winner,
            'electedProvenance': vote.elected_provenance,
            'note': "this vote row now names the fork's resolved "
                    'decision criterion — NOTE: this records the '
                    'resolution, it does not auto-rewrite a live '
                    'SolutionDefinition graph (see module docstring)'}
def resolved_procedure_summary(manager, decision_procedure_name):
    """Human-readable 'what does this decision procedure look like
    right now' report: every known fork in this procedure, its
    resolved criterion if any vote has been applied, else its
    incumbent default, else honestly unresolved. NOT a rewritten
    no-code graph — a summary for people to read, per this module's
    documented scope."""
    criteria = [c for c in _rows(manager, 'LogicForkCriterion')
                if getattr(c, 'decision_procedure_name', '')
                == decision_procedure_name]
    if not criteria:
        return {'ok': False,
                'error': f"no LogicForkCriterion rows for decision "
                         f"procedure '{decision_procedure_name}'",
                'knownProcedures': sorted({
                    getattr(c, 'decision_procedure_name', '')
                    for c in _rows(manager, 'LogicForkCriterion')})}

    votes_by_fork = {}
    for v in _rows(manager, 'LogicForkVote'):
        if getattr(v, 'decision_procedure_name', '') \
                == decision_procedure_name:
            votes_by_fork[getattr(v, 'fork_name', '')] = v

    forks = {}
    for c in criteria:
        fork = getattr(c, 'fork_name', '')
        forks.setdefault(fork, []).append({
            'name': getattr(c, 'name', ''),
            'displayName': getattr(c, 'display_name', ''),
            'description': getattr(c, 'description', ''),
            'isCurrentDefault': bool(getattr(c, 'is_current_default', False)),
            'proposedBy': getattr(c, 'proposed_by', ''),
        })

    report_forks = []
    for fork_name, fork_criteria in forks.items():
        vote = votes_by_fork.get(fork_name)
        elected = getattr(vote, 'elected_criterion_name', '') if vote else ''
        default = next((c['name'] for c in fork_criteria
                        if c['isCurrentDefault']), '')
        resolved = elected or default
        report_forks.append({
            'fork': fork_name,
            'candidateCriteria': fork_criteria,
            'vote': getattr(vote, 'name', '') if vote else None,
            'voteStatus': getattr(vote, 'status', '') if vote else None,
            'resolvedCriterion': resolved or None,
            'resolvedSource': ('vote' if elected
                               else 'incumbent-default' if default
                               else None),
        })

    edges = [
        {
            'fromFork': getattr(e, 'from_fork', '') or None,
            'fromOutcome': getattr(e, 'from_outcome', '') or None,
            'toFork': getattr(e, 'to_fork', '') or None,
            'toTerminal': getattr(e, 'to_terminal', '') or None,
            'description': getattr(e, 'description', ''),
        }
        for e in _rows(manager, 'DecisionProcedureEdge')
        if getattr(e, 'decision_procedure_name', '')
        == decision_procedure_name
    ]

    return {
        'ok': True,
        'decisionProcedure': decision_procedure_name,
        'forks': report_forks,
        'edges': edges,
        'note': 'this is a human-readable summary of resolved/'
                'unresolved forks and their graph connections, not a '
                'rewritten executable no-code '
                'graph — see logic_fork_vote.py module docstring',
    }
SEED_LOGIC_FORK_CRITERIA = [
    {
        'name': 'is-repeat-offender',
        'display_name': 'Is a Repeat Offender',
        'description': "Is this the individual's second or later "
                       'conviction for this offense category? A '
                       'binary recurrence check — the incumbent '
                       'default at this fork.',
        'decision_procedure_name': 'repeat-offense-sentencing-framework',
        'fork_name': 'recidivism-risk-fork',
        'is_current_default': True,
        'proposed_by': 'demo-sentencing-status-quo',
        'provenance_id': 'incumbent framework baseline',
    },
    {
        'name': 'reform-durability-likelihood',
        'display_name': 'Reform Durability Likelihood',
        'description': 'Likelihood that behavioral and psychological '
                       'reform actually lasts for the remainder of '
                       "the individual's life, given their "
                       'demonstrated context (documented treatment '
                       'engagement, support-system stability, '
                       'behavioral-change indicators from a named '
                       'assessment method) — rather than treating '
                       'prior recurrence count alone as destiny.',
        'decision_procedure_name': 'repeat-offense-sentencing-framework',
        'fork_name': 'recidivism-risk-fork',
        'is_current_default': False,
        'proposed_by': 'demo-reform-assessment-coalition',
        'provenance_id': 'Phase C mechanism seed — Dustin 2026-07-14 '
                         'worked example, verbatim intent',
    },
    {
        # A third, more realistic recidivism-risk criterion — added
        # 2026-07-14 without disturbing the already-resolved vote
        # above: a genuinely documented proposal that simply hasn't
        # been put to a vote yet (a real, valid state — not every
        # criterion needs an active vote to exist). Modeled on real
        # validated instruments used in actual practice (e.g.
        # STATIC-99R-style actuarial risk tools).
        'name': 'actuarial-risk-instrument-standard',
        'display_name': 'Validated Actuarial Risk Instrument',
        'description': 'A normed risk-percentile score from a '
                       'validated actuarial instrument combining '
                       'static historical factors (age at release, '
                       'victim relationship to offender, prior '
                       'offense count/type) with dynamic factors '
                       '(supervision compliance, treatment '
                       'engagement) — in the style of real published '
                       'sex-offense recidivism instruments (e.g. '
                       'STATIC-99R). Neither a binary recurrence '
                       'check nor a subjective likelihood judgment: '
                       'a normed, externally-validated score.',
        'decision_procedure_name': 'repeat-offense-sentencing-framework',
        'fork_name': 'recidivism-risk-fork',
        'is_current_default': False,
        'proposed_by': 'demo-forensic-psychology-panel',
        'provenance_id': 'documented proposal, not yet put to a vote',
    },
    # Conviction-phase forks (2026-07-14 — Dustin: "come up with a
    # more realistic criteria evaluation... in a court trying a
    # criminal for rape and different variations in context that
    # would affect conviction and sentencing"). Each grounded in real
    # documented legal standards/history, not invented.
    {
        'name': 'force-based-consent-standard',
        'display_name': 'Force-Based Consent Standard',
        'description': 'Requires proof of physical force, or an '
                       'explicit threat of force, sufficient to '
                       'overcome resistance — the traditional '
                       'common-law baseline still embedded in many '
                       'criminal statutes.',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'fork_name': 'consent-determination-fork',
        'is_current_default': True,
        'proposed_by': 'demo-defense-bar-association',
        'provenance_id': 'traditional statutory baseline in many '
                         'US jurisdictions',
    },
    {
        'name': 'affirmative-consent-standard',
        'display_name': 'Affirmative Consent Standard',
        'description': 'Absence of affirmative, ongoing, freely-'
                       'given consent is sufficient regardless of '
                       'force — silence or non-resistance is not '
                       'consent. The "yes means yes" reform '
                       'direction (e.g. California SB 967\'s campus '
                       'standard; some newer state statutes move '
                       'criminal codes toward this framing too).',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'fork_name': 'consent-determination-fork',
        'is_current_default': False,
        'proposed_by': 'demo-victim-advocacy-coalition',
        'provenance_id': 'affirmative-consent reform movement',
    },
    {
        'name': 'incapacitation-focused-consent-standard',
        'display_name': 'Incapacitation-Focused Consent Standard',
        'description': 'Centers entirely on whether the complainant '
                       'had legal capacity to consent at the time '
                       '(intoxication level, unconsciousness, '
                       'cognitive impairment) — independent of force '
                       'or affirmative-consent framing.',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'fork_name': 'consent-determination-fork',
        'is_current_default': False,
        'proposed_by': 'demo-forensic-psychology-panel',
        'provenance_id': 'incapacitation-centered statutory framing '
                         '(distinct legal track in many codes)',
    },
    {
        'name': 'corroboration-requirement-standard',
        'display_name': 'Corroboration Requirement',
        'description': "Requires independent corroborating evidence "
                       "beyond the complainant's own testimony to "
                       'sustain a conviction — the older common-law '
                       'rule, abolished in most US jurisdictions '
                       'starting in the 1970s-80s but still real in '
                       'some places.',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'fork_name': 'testimony-sufficiency-fork',
        'is_current_default': False,
        'proposed_by': 'demo-defense-bar-association',
        'provenance_id': 'pre-reform common-law rule',
    },
    {
        'name': 'victim-testimony-sufficient-standard',
        'display_name': 'Victim Testimony Sufficient',
        'description': 'Credible complainant testimony alone is '
                       'legally sufficient to sustain a conviction — '
                       'no corroborating evidence required. The '
                       'actual modern majority-US legal standard.',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'fork_name': 'testimony-sufficiency-fork',
        'is_current_default': True,
        'proposed_by': 'demo-prosecutors-association',
        'provenance_id': 'modern majority-US evidentiary standard',
    },
    {
        'name': 'broadly-admissible-standard',
        'display_name': 'Prior History Broadly Admissible',
        'description': "Complainant's prior sexual history broadly "
                       'usable to challenge credibility/character — '
                       'the pre-reform historical approach.',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'fork_name': 'prior-sexual-history-admissibility-fork',
        'is_current_default': False,
        'proposed_by': 'demo-defense-bar-association',
        'provenance_id': 'pre-rape-shield historical approach',
    },
    {
        'name': 'categorically-excluded-with-exceptions-standard',
        'display_name': 'Categorically Excluded (Rape Shield)',
        'description': "Complainant's prior sexual history is "
                       'categorically excluded except for narrow '
                       'enumerated exceptions (e.g. prior sexual '
                       'contact with the same defendant, an '
                       'alternative source of physical evidence) — '
                       'the actual modern rape-shield standard (FRE '
                       '412 and state equivalents).',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'fork_name': 'prior-sexual-history-admissibility-fork',
        'is_current_default': True,
        'proposed_by': 'demo-victim-advocacy-coalition',
        'provenance_id': 'modern rape-shield law standard (FRE 412 '
                         'and state equivalents)',
    },
    {
        'name': 'judicial-discretion-balancing-standard',
        'display_name': 'Judicial-Discretion Balancing Test',
        'description': 'Prior sexual history admitted only after '
                       'in-camera judicial review balancing '
                       'probative value against prejudicial/privacy '
                       'harm, case-by-case — a live position in '
                       'ongoing legal scholarship debate over rigid '
                       'categorical exclusion vs. structured '
                       'discretion.',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'fork_name': 'prior-sexual-history-admissibility-fork',
        'is_current_default': False,
        'proposed_by': 'demo-judicial-conference',
        'provenance_id': 'legal-scholarship structured-discretion '
                         'proposal',
    },
    # Two more sentencing-phase forks — completing the graph from
    # conviction through final sentence (Dustin: "flush out a more
    # complete logic graph").
    {
        'name': 'structured-point-based-guideline-standard',
        'display_name': 'Structured Point-Based Guideline',
        'description': 'Each aggravating factor (weapon use, victim '
                       'vulnerability, position of trust abused, '
                       'premeditation) and mitigating factor (no '
                       'prior record, genuine acceptance of '
                       'responsibility, age/diminished capacity) is '
                       'separately scored and combined into a '
                       'computed guideline range — the actual '
                       'structure real federal/state sentencing '
                       'guideline systems use.',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'fork_name': 'aggravating-mitigating-factor-weighting-fork',
        'is_current_default': True,
        'proposed_by': 'demo-judicial-conference',
        'provenance_id': 'real federal/state sentencing guideline '
                         'structure',
    },
    {
        'name': 'mandatory-minimum-standard',
        'display_name': 'Mandatory Minimum, No Discretion Below Floor',
        'description': 'Offense category alone determines a fixed '
                       'sentence range; aggravating/mitigating '
                       'factors have no discretionary effect below '
                       'the statutory floor.',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'fork_name': 'aggravating-mitigating-factor-weighting-fork',
        'is_current_default': False,
        'proposed_by': 'demo-prosecutors-association',
        'provenance_id': 'mandatory-minimum statutory framework',
    },
    {
        'name': 'restorative-justice-informed-standard',
        'display_name': 'Restorative-Justice-Informed Weighting',
        'description': 'Incorporates structured victim input (a '
                       'formal preference channel on non-custodial/'
                       'restorative elements, not just a symbolic '
                       'statement) as a weighted factor alongside '
                       'traditional aggravating/mitigating factors.',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'fork_name': 'aggravating-mitigating-factor-weighting-fork',
        'is_current_default': False,
        'proposed_by': 'demo-victim-advocacy-coalition',
        'provenance_id': 'restorative-justice sentencing proposal',
    },
    {
        'name': 'informational-only-standard',
        'display_name': 'Victim Impact Statement, Informational Only',
        'description': 'Victim impact statement is heard by the '
                       'court but does not formally alter the '
                       'guideline calculation — heard, not scored.',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'fork_name': 'victim-impact-weighting-fork',
        'is_current_default': True,
        'proposed_by': 'demo-defense-bar-association',
        'provenance_id': 'traditional victim-impact-statement '
                         'treatment in many jurisdictions',
    },
    {
        'name': 'clinically-scored-trauma-standard',
        'display_name': 'Clinically-Scored Trauma Severity',
        'description': 'Documented, clinically-assessed trauma '
                       'severity (via a standardized instrument) '
                       'becomes a scored aggravating factor within '
                       'the guideline calculation itself, not merely '
                       'heard.',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'fork_name': 'victim-impact-weighting-fork',
        'is_current_default': False,
        'proposed_by': 'demo-forensic-psychology-panel',
        'provenance_id': 'clinical-assessment sentencing-reform '
                         'proposal',
    },
    {
        'name': 'structured-victim-voice-standard',
        'display_name': 'Structured Victim Voice (Non-Custodial Terms)',
        'description': 'Victim is given formal structured input on '
                       'specific sentencing elements (no-contact '
                       'terms, restitution scope) without altering '
                       'the custodial-term calculation itself.',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'fork_name': 'victim-impact-weighting-fork',
        'is_current_default': False,
        'proposed_by': 'demo-judicial-conference',
        'provenance_id': 'structured-victim-input sentencing proposal',
    },
]
SEED_LOGIC_FORK_VOTES = [
    {
        'name': 'recidivism-fork-criterion-vote',
        'display_name': 'Which criterion should the recidivism-risk '
                        'fork actually use?',
        'description': "Sole-choice vote: 'is a repeat offender' (the "
                       "incumbent default) vs. 'reform durability "
                       "likelihood' (the proposed alternate) for the "
                       'repeat-offense sentencing framework\'s '
                       'recidivism-risk fork.',
        'decision_procedure_name': 'repeat-offense-sentencing-framework',
        'fork_name': 'recidivism-risk-fork',
        'candidate_criterion_names_json': json.dumps([
            'is-repeat-offender', 'reform-durability-likelihood']),
        'mode': 'sole',
        'status': 'closed',
        'opens_date': '2026-07-01', 'closes_date': '2026-07-14',
        'provenance_id': 'Phase C mechanism seed',
    },
    {
        # Ranked-condorcet, 5 ballots — hand-computed winner:
        # affirmative-consent-standard beats both others pairwise
        # (4-1 vs force-based, 3-2 vs incapacitation-focused).
        'name': 'consent-determination-fork-vote',
        'display_name': 'Which standard should the consent-'
                        'determination fork use?',
        'description': 'Ranked-condorcet vote over three consent-'
                       'determination standards for the sexual-'
                       'assault-adjudication framework.',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'fork_name': 'consent-determination-fork',
        'candidate_criterion_names_json': json.dumps([
            'force-based-consent-standard', 'affirmative-consent-standard',
            'incapacitation-focused-consent-standard']),
        'mode': 'ranked-condorcet',
        'status': 'closed',
        'opens_date': '2026-07-01', 'closes_date': '2026-07-14',
        'provenance_id': 'Phase C mechanism seed',
    },
    {
        # Sole choice, 5 ballots — hand-computed: victim-testimony-
        # sufficient-standard (the actual modern default) reaffirmed
        # 4-1 against a proposed reversion to corroboration.
        'name': 'testimony-sufficiency-fork-vote',
        'display_name': 'Which standard should the testimony-'
                        'sufficiency fork use?',
        'description': "Sole-choice vote: keep the modern 'victim "
                       "testimony sufficient' standard, or revert to "
                       "a 'corroboration requirement'.",
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'fork_name': 'testimony-sufficiency-fork',
        'candidate_criterion_names_json': json.dumps([
            'corroboration-requirement-standard',
            'victim-testimony-sufficient-standard']),
        'mode': 'sole',
        'status': 'closed',
        'opens_date': '2026-07-01', 'closes_date': '2026-07-14',
        'provenance_id': 'Phase C mechanism seed',
    },
    {
        # Ranked-condorcet, 5 ballots — hand-computed: categorically-
        # excluded-with-exceptions-standard (the real rape-shield
        # default) reaffirmed, beating judicial-discretion 3-2 and
        # broadly-admissible 5-0.
        'name': 'prior-history-admissibility-fork-vote',
        'display_name': 'Which standard should the prior-sexual-'
                        'history admissibility fork use?',
        'description': 'Ranked-condorcet vote over three prior-'
                       'sexual-history admissibility standards.',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'fork_name': 'prior-sexual-history-admissibility-fork',
        'candidate_criterion_names_json': json.dumps([
            'broadly-admissible-standard',
            'categorically-excluded-with-exceptions-standard',
            'judicial-discretion-balancing-standard']),
        'mode': 'ranked-condorcet',
        'status': 'closed',
        'opens_date': '2026-07-01', 'closes_date': '2026-07-14',
        'provenance_id': 'Phase C mechanism seed',
    },
    {
        # Ranked-condorcet, 5 ballots — hand-computed: structured-
        # point-based-guideline-standard (the real default) reaffirmed,
        # beating mandatory-minimum 5-0 and restorative-justice 4-1.
        'name': 'aggravating-mitigating-weighting-fork-vote',
        'display_name': 'Which standard should the aggravating/'
                        'mitigating-factor-weighting fork use?',
        'description': 'Ranked-condorcet vote over three sentencing-'
                       'weighting standards.',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'fork_name': 'aggravating-mitigating-factor-weighting-fork',
        'candidate_criterion_names_json': json.dumps([
            'structured-point-based-guideline-standard',
            'mandatory-minimum-standard',
            'restorative-justice-informed-standard']),
        'mode': 'ranked-condorcet',
        'status': 'closed',
        'opens_date': '2026-07-01', 'closes_date': '2026-07-14',
        'provenance_id': 'Phase C mechanism seed',
    },
    {
        # Sole choice, 5 ballots — hand-computed: clinically-scored-
        # trauma-standard wins 3/5, a genuine reform adoption (not
        # every fork reaffirms the default — this one changes).
        'name': 'victim-impact-weighting-fork-vote',
        'display_name': 'Which standard should the victim-impact-'
                        'weighting fork use?',
        'description': 'Sole-choice vote over three victim-impact-'
                       'weighting standards.',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'fork_name': 'victim-impact-weighting-fork',
        'candidate_criterion_names_json': json.dumps([
            'informational-only-standard',
            'clinically-scored-trauma-standard',
            'structured-victim-voice-standard']),
        'mode': 'sole',
        'status': 'closed',
        'opens_date': '2026-07-01', 'closes_date': '2026-07-14',
        'provenance_id': 'Phase C mechanism seed',
    },
]
SEED_LOGIC_FORK_BALLOTS = [
    {
        'name': 'fork-ballot-reform-assessment-coalition',
        'vote_name': 'recidivism-fork-criterion-vote',
        'voter': 'demo-reform-assessment-coalition',
        'sole_choice': 'reform-durability-likelihood',
        'cast_date': '2026-07-02',
    },
    {
        'name': 'fork-ballot-status-quo',
        'vote_name': 'recidivism-fork-criterion-vote',
        'voter': 'demo-sentencing-status-quo',
        'sole_choice': 'is-repeat-offender',
        'cast_date': '2026-07-02',
    },
    {
        'name': 'fork-ballot-judge-1',
        'vote_name': 'recidivism-fork-criterion-vote',
        'voter': 'demo-judge-1',
        'sole_choice': 'reform-durability-likelihood',
        'cast_date': '2026-07-05',
    },
    {
        'name': 'fork-ballot-victim-advocate',
        'vote_name': 'recidivism-fork-criterion-vote',
        'voter': 'demo-victim-advocate',
        'sole_choice': 'is-repeat-offender',
        'cast_date': '2026-07-08',
    },
    {
        'name': 'fork-ballot-reentry-specialist',
        'vote_name': 'recidivism-fork-criterion-vote',
        'voter': 'demo-reentry-specialist',
        'sole_choice': 'reform-durability-likelihood',
        'cast_date': '2026-07-10',
    },
    # consent-determination-fork-vote (ranked-condorcet) — 5 voters,
    # each a genuinely different professional/civic perspective.
    # Hand-computed winner: affirmative-consent-standard.
    {
        'name': 'consent-ballot-victim-advocacy',
        'vote_name': 'consent-determination-fork-vote',
        'voter': 'demo-victim-advocacy-coalition',
        'ranking_json': json.dumps([
            'affirmative-consent-standard',
            'incapacitation-focused-consent-standard',
            'force-based-consent-standard']),
        'cast_date': '2026-07-03',
    },
    {
        'name': 'consent-ballot-defense-bar',
        'vote_name': 'consent-determination-fork-vote',
        'voter': 'demo-defense-bar-association',
        'ranking_json': json.dumps([
            'force-based-consent-standard',
            'incapacitation-focused-consent-standard',
            'affirmative-consent-standard']),
        'cast_date': '2026-07-03',
    },
    {
        'name': 'consent-ballot-prosecutors',
        'vote_name': 'consent-determination-fork-vote',
        'voter': 'demo-prosecutors-association',
        'ranking_json': json.dumps([
            'affirmative-consent-standard',
            'force-based-consent-standard',
            'incapacitation-focused-consent-standard']),
        'cast_date': '2026-07-04',
    },
    {
        'name': 'consent-ballot-forensic-panel',
        'vote_name': 'consent-determination-fork-vote',
        'voter': 'demo-forensic-psychology-panel',
        'ranking_json': json.dumps([
            'incapacitation-focused-consent-standard',
            'affirmative-consent-standard',
            'force-based-consent-standard']),
        'cast_date': '2026-07-05',
    },
    {
        'name': 'consent-ballot-judicial-conference',
        'vote_name': 'consent-determination-fork-vote',
        'voter': 'demo-judicial-conference',
        'ranking_json': json.dumps([
            'affirmative-consent-standard',
            'incapacitation-focused-consent-standard',
            'force-based-consent-standard']),
        'cast_date': '2026-07-06',
    },
    # testimony-sufficiency-fork-vote (sole) — hand-computed 4-1 for
    # the modern default.
    {
        'name': 'testimony-ballot-victim-advocacy',
        'vote_name': 'testimony-sufficiency-fork-vote',
        'voter': 'demo-victim-advocacy-coalition',
        'sole_choice': 'victim-testimony-sufficient-standard',
        'cast_date': '2026-07-03',
    },
    {
        'name': 'testimony-ballot-defense-bar',
        'vote_name': 'testimony-sufficiency-fork-vote',
        'voter': 'demo-defense-bar-association',
        'sole_choice': 'corroboration-requirement-standard',
        'cast_date': '2026-07-03',
    },
    {
        'name': 'testimony-ballot-prosecutors',
        'vote_name': 'testimony-sufficiency-fork-vote',
        'voter': 'demo-prosecutors-association',
        'sole_choice': 'victim-testimony-sufficient-standard',
        'cast_date': '2026-07-04',
    },
    {
        'name': 'testimony-ballot-forensic-panel',
        'vote_name': 'testimony-sufficiency-fork-vote',
        'voter': 'demo-forensic-psychology-panel',
        'sole_choice': 'victim-testimony-sufficient-standard',
        'cast_date': '2026-07-05',
    },
    {
        'name': 'testimony-ballot-judicial-conference',
        'vote_name': 'testimony-sufficiency-fork-vote',
        'voter': 'demo-judicial-conference',
        'sole_choice': 'victim-testimony-sufficient-standard',
        'cast_date': '2026-07-06',
    },
    # prior-history-admissibility-fork-vote (ranked-condorcet) —
    # hand-computed winner: categorically-excluded-with-exceptions-
    # standard (beats judicial-discretion 3-2, broadly-admissible 5-0).
    {
        'name': 'history-ballot-victim-advocacy',
        'vote_name': 'prior-history-admissibility-fork-vote',
        'voter': 'demo-victim-advocacy-coalition',
        'ranking_json': json.dumps([
            'categorically-excluded-with-exceptions-standard',
            'judicial-discretion-balancing-standard',
            'broadly-admissible-standard']),
        'cast_date': '2026-07-03',
    },
    {
        'name': 'history-ballot-defense-bar',
        'vote_name': 'prior-history-admissibility-fork-vote',
        'voter': 'demo-defense-bar-association',
        'ranking_json': json.dumps([
            'judicial-discretion-balancing-standard',
            'broadly-admissible-standard',
            'categorically-excluded-with-exceptions-standard']),
        'cast_date': '2026-07-03',
    },
    {
        'name': 'history-ballot-prosecutors',
        'vote_name': 'prior-history-admissibility-fork-vote',
        'voter': 'demo-prosecutors-association',
        'ranking_json': json.dumps([
            'categorically-excluded-with-exceptions-standard',
            'judicial-discretion-balancing-standard',
            'broadly-admissible-standard']),
        'cast_date': '2026-07-04',
    },
    {
        'name': 'history-ballot-forensic-panel',
        'vote_name': 'prior-history-admissibility-fork-vote',
        'voter': 'demo-forensic-psychology-panel',
        'ranking_json': json.dumps([
            'categorically-excluded-with-exceptions-standard',
            'judicial-discretion-balancing-standard',
            'broadly-admissible-standard']),
        'cast_date': '2026-07-05',
    },
    {
        'name': 'history-ballot-judicial-conference',
        'vote_name': 'prior-history-admissibility-fork-vote',
        'voter': 'demo-judicial-conference',
        'ranking_json': json.dumps([
            'judicial-discretion-balancing-standard',
            'categorically-excluded-with-exceptions-standard',
            'broadly-admissible-standard']),
        'cast_date': '2026-07-06',
    },
    # aggravating-mitigating-weighting-fork-vote (ranked-condorcet) —
    # hand-computed winner: structured-point-based-guideline-standard
    # (beats mandatory-minimum 5-0, restorative-justice 4-1).
    {
        'name': 'weighting-ballot-victim-advocacy',
        'vote_name': 'aggravating-mitigating-weighting-fork-vote',
        'voter': 'demo-victim-advocacy-coalition',
        'ranking_json': json.dumps([
            'restorative-justice-informed-standard',
            'structured-point-based-guideline-standard',
            'mandatory-minimum-standard']),
        'cast_date': '2026-07-07',
    },
    {
        'name': 'weighting-ballot-defense-bar',
        'vote_name': 'aggravating-mitigating-weighting-fork-vote',
        'voter': 'demo-defense-bar-association',
        'ranking_json': json.dumps([
            'structured-point-based-guideline-standard',
            'restorative-justice-informed-standard',
            'mandatory-minimum-standard']),
        'cast_date': '2026-07-07',
    },
    {
        'name': 'weighting-ballot-prosecutors',
        'vote_name': 'aggravating-mitigating-weighting-fork-vote',
        'voter': 'demo-prosecutors-association',
        'ranking_json': json.dumps([
            'structured-point-based-guideline-standard',
            'mandatory-minimum-standard',
            'restorative-justice-informed-standard']),
        'cast_date': '2026-07-08',
    },
    {
        'name': 'weighting-ballot-forensic-panel',
        'vote_name': 'aggravating-mitigating-weighting-fork-vote',
        'voter': 'demo-forensic-psychology-panel',
        'ranking_json': json.dumps([
            'structured-point-based-guideline-standard',
            'restorative-justice-informed-standard',
            'mandatory-minimum-standard']),
        'cast_date': '2026-07-09',
    },
    {
        'name': 'weighting-ballot-judicial-conference',
        'vote_name': 'aggravating-mitigating-weighting-fork-vote',
        'voter': 'demo-judicial-conference',
        'ranking_json': json.dumps([
            'structured-point-based-guideline-standard',
            'mandatory-minimum-standard',
            'restorative-justice-informed-standard']),
        'cast_date': '2026-07-10',
    },
    # victim-impact-weighting-fork-vote (sole) — hand-computed 3/5 for
    # a genuine reform adoption (clinically-scored-trauma-standard).
    {
        'name': 'impact-ballot-victim-advocacy',
        'vote_name': 'victim-impact-weighting-fork-vote',
        'voter': 'demo-victim-advocacy-coalition',
        'sole_choice': 'clinically-scored-trauma-standard',
        'cast_date': '2026-07-11',
    },
    {
        'name': 'impact-ballot-defense-bar',
        'vote_name': 'victim-impact-weighting-fork-vote',
        'voter': 'demo-defense-bar-association',
        'sole_choice': 'informational-only-standard',
        'cast_date': '2026-07-11',
    },
    {
        'name': 'impact-ballot-prosecutors',
        'vote_name': 'victim-impact-weighting-fork-vote',
        'voter': 'demo-prosecutors-association',
        'sole_choice': 'clinically-scored-trauma-standard',
        'cast_date': '2026-07-12',
    },
    {
        'name': 'impact-ballot-forensic-panel',
        'vote_name': 'victim-impact-weighting-fork-vote',
        'voter': 'demo-forensic-psychology-panel',
        'sole_choice': 'clinically-scored-trauma-standard',
        'cast_date': '2026-07-13',
    },
    {
        'name': 'impact-ballot-judicial-conference',
        'vote_name': 'victim-impact-weighting-fork-vote',
        'voter': 'demo-judicial-conference',
        'sole_choice': 'structured-victim-voice-standard',
        'cast_date': '2026-07-14',
    },
]
SEED_LOGIC_FORK_CONTRIBUTORS = [
    {
        'name': 'demo-sentencing-status-quo',
        'display_name': 'Sentencing Status Quo (incumbent baseline)',
        'kind': 'institution',
        'pseudonymous': False,
        'description': 'Represents the current framework\'s '
                       'incumbent default criterion at this fork.',
    },
    {
        'name': 'demo-reform-assessment-coalition',
        'display_name': 'Reform Assessment Coalition',
        'kind': 'organization',
        'pseudonymous': False,
        'description': 'Proposes assessment-based reform-durability '
                       'criteria as alternates to raw recurrence '
                       'counts at sentencing decision forks.',
    },
    {
        'name': 'demo-judge-1',
        'display_name': 'judge-1 (pseudonym)',
        'kind': 'individual',
        'pseudonymous': True,
        'description': 'Demo pseudonymous sitting judge casting a '
                       'ballot in the fork-criterion vote.',
    },
    {
        'name': 'demo-victim-advocate',
        'display_name': 'victim-advocate (pseudonym)',
        'kind': 'individual',
        'pseudonymous': True,
        'description': 'Demo pseudonymous victim advocate casting a '
                       'ballot in the fork-criterion vote.',
    },
    {
        'name': 'demo-reentry-specialist',
        'display_name': 'reentry-specialist (pseudonym)',
        'kind': 'individual',
        'pseudonymous': True,
        'description': 'Demo pseudonymous reentry/rehabilitation '
                       'specialist casting a ballot in the fork-'
                       'criterion vote.',
    },
    # Contributors for the sexual-assault-adjudication-framework's 5
    # forks — real, named professional/civic perspectives, not
    # anonymous placeholders (though individuals within them stay
    # pseudonymous by default, per this codebase's Contributor
    # convention).
    {
        'name': 'demo-victim-advocacy-coalition',
        'display_name': 'Victim Advocacy Coalition',
        'kind': 'coalition',
        'pseudonymous': False,
        'description': 'Advocates for survivor-centered evidentiary '
                       'and sentencing standards across the '
                       'adjudication framework\'s forks.',
    },
    {
        'name': 'demo-defense-bar-association',
        'display_name': 'Defense Bar Association',
        'kind': 'organization',
        'pseudonymous': False,
        'description': 'Represents criminal defense practitioners\' '
                       'positions on evidentiary and sentencing '
                       'standards.',
    },
    {
        'name': 'demo-prosecutors-association',
        'display_name': "Prosecutors' Association",
        'kind': 'organization',
        'pseudonymous': False,
        'description': "Represents prosecutors' positions on "
                       'evidentiary and sentencing standards.',
    },
    {
        'name': 'demo-forensic-psychology-panel',
        'display_name': 'Forensic Psychology Panel',
        'kind': 'organization',
        'pseudonymous': False,
        'description': 'Clinical/forensic-assessment expertise on '
                       'capacity, risk-assessment, and trauma-'
                       'severity standards.',
    },
    {
        'name': 'demo-judicial-conference',
        'display_name': 'Judicial Conference',
        'kind': 'institution',
        'pseudonymous': False,
        'description': 'Represents sitting judges\' collective '
                       'positions on procedural and sentencing '
                       'standards.',
    },
]
SEED_DECISION_PROCEDURE_EDGES = [
    {
        'name': 'edge-start-to-history-admissibility',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'from_fork': '', 'from_outcome': '',
        'to_fork': 'prior-sexual-history-admissibility-fork',
        'to_terminal': '',
        'description': 'Charge filed — the prior-sexual-history '
                       'admissibility ruling is a pretrial '
                       'evidentiary matter, decided before the '
                       'guilt-phase forks it shapes.',
    },
    {
        'name': 'edge-history-to-consent',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'from_fork': 'prior-sexual-history-admissibility-fork',
        'from_outcome': 'ruling-made',
        'to_fork': 'consent-determination-fork',
        'to_terminal': '',
        'description': 'Once the admissibility ruling is made, trial '
                       'proceeds to the guilt-phase consent '
                       'determination using only admissible evidence.',
    },
    {
        'name': 'edge-consent-established-to-acquittal',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'from_fork': 'consent-determination-fork',
        'from_outcome': 'consent-established',
        'to_fork': '', 'to_terminal': 'ACQUITTAL',
        'description': "If the fact-finder determines the chosen "
                       "standard's consent test IS satisfied, the "
                       'element fails and the case terminates in '
                       'acquittal.',
    },
    {
        'name': 'edge-consent-not-established-to-testimony',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'from_fork': 'consent-determination-fork',
        'from_outcome': 'consent-not-established',
        'to_fork': 'testimony-sufficiency-fork', 'to_terminal': '',
        'description': 'If consent is NOT established under the '
                       'chosen standard, the case proceeds to '
                       'whether the evidence is legally sufficient '
                       'to convict.',
    },
    {
        'name': 'edge-insufficient-to-acquittal',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'from_fork': 'testimony-sufficiency-fork',
        'from_outcome': 'insufficient-evidence',
        'to_fork': '', 'to_terminal': 'ACQUITTAL',
        'description': 'If the evidence, as admitted, does not meet '
                       'the chosen sufficiency standard, the case '
                       'terminates in acquittal (or dismissal).',
    },
    {
        'name': 'edge-sufficient-to-conviction',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'from_fork': 'testimony-sufficiency-fork',
        'from_outcome': 'sufficient-evidence',
        'to_fork': '', 'to_terminal': 'CONVICTION',
        'description': 'If the evidence meets the chosen sufficiency '
                       'standard, the case results in conviction and '
                       'proceeds to the sentencing-phase forks.',
    },
    {
        'name': 'edge-conviction-to-recidivism',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'from_fork': '', 'from_outcome': 'CONVICTION',
        'to_fork': 'recidivism-risk-fork', 'to_terminal': '',
        'description': 'Sentencing phase begins with the recidivism-'
                       'risk assessment — a cross-procedure reference '
                       "to the fork whose own LogicForkCriterion rows "
                       "are defined under 'repeat-offense-sentencing-"
                       "framework' (not duplicated here; "
                       'resolved_procedure_summary() only enumerates '
                       'locally-defined forks, so read that '
                       "procedure's own resolution for this fork's "
                       'current criterion).',
    },
    {
        'name': 'edge-recidivism-to-weighting',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'from_fork': 'recidivism-risk-fork', 'from_outcome': 'risk-assessed',
        'to_fork': 'aggravating-mitigating-factor-weighting-fork',
        'to_terminal': '',
        'description': 'The recidivism-risk assessment feeds into '
                       'the aggravating/mitigating-factor weighting '
                       'as one input among several.',
    },
    {
        'name': 'edge-weighting-to-impact',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'from_fork': 'aggravating-mitigating-factor-weighting-fork',
        'from_outcome': 'range-computed',
        'to_fork': 'victim-impact-weighting-fork', 'to_terminal': '',
        'description': 'Once a base guideline range is computed, '
                       'victim-impact weighting is applied to refine '
                       'or adjust within/alongside it.',
    },
    {
        'name': 'edge-impact-to-sentence',
        'decision_procedure_name': 'sexual-assault-adjudication-framework',
        'from_fork': 'victim-impact-weighting-fork',
        'from_outcome': 'final-adjustment',
        'to_fork': '', 'to_terminal': 'SENTENCE_IMPOSED',
        'description': 'Final sentence is imposed.',
    },
]
