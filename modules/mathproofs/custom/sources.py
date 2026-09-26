"""
@module mathproofs.custom.sources

THE SOURCES BEHIND THE PROOF METHODS (bp-2e, his ask 2026-09-25): published work establishing why each checker tier
can be trusted for what it says — and where its authority stops. Rows of ProofMethodReference, the suite's existing
citation shape (EvidenceItem's fields). `proves` names the tier / vocabulary word each source underwrites.

Verification is honest per row: `verified=True` only where the DOI was resolved through Crossref on 2026-09-25 and
the title, authors and venue read back as recorded (`verified_via` says so); print-only references and archive
scans that did not resolve stay `verified=False` with the reason. Nothing here is cited from memory alone.
"""
import json

_AT = '2026-09-25'
_CR = 'Crossref record for the DOI resolved 2026-09-25; title, authors, venue and year read back'


def _s(name, title, parties, ref, date, url, proves, detail, key, verified=True, via=_CR, kind='publication', notes=''):
    return {'name': name, 'kind': kind, 'title': title, 'parties': parties, 'ref': ref, 'date': date, 'url': url, 'proves': proves,
            'proves_detail': detail, 'citation_key': key, 'verified': verified, 'verified_via': via, 'verified_at': _AT if verified else '',
            'subjects_json': json.dumps([p.strip() for p in proves.split(',')]), 'notes': notes}


SEED_PROOF_METHOD_REFERENCES = [
    # ---- tier 0: a numeric witness is NOT a proof --------------------------------------------------------------
    _s('dijkstra-1972-humble-programmer', 'The humble programmer', 'Dijkstra, E. W.', 'Communications of the ACM 15(10), 859–866', '1972',
       'https://doi.org/10.1145/355604.361591', 'tier:numeric, vocabulary:witnessed',
       'The classic statement that testing can show the presence of errors but never their absence — exactly why a claim that holds on the rows we have is "witnessed", never "proved".',
       'Dijkstra1972'),
    _s('claessen-hughes-2000-quickcheck', 'QuickCheck: a lightweight tool for random testing of Haskell programs', 'Claessen, K.; Hughes, J.',
       'ICFP 2000, Proceedings of the fifth ACM SIGPLAN international conference on Functional programming, 268–279', '2000',
       'https://doi.org/10.1145/351240.351266', 'tier:numeric',
       'Property checking on sampled inputs: a failing sample is a genuine counterexample (our refutation on a row), while passing samples only raise confidence — the numeric tier\'s two outcomes.',
       'ClaessenHughes2000'),
    # ---- tier 1: interval arithmetic is EXACT set arithmetic ---------------------------------------------------
    _s('moore-kearfott-cloud-2009-interval-analysis', 'Introduction to Interval Analysis', 'Moore, R. E.; Kearfott, R. B.; Cloud, M. J.',
       'Society for Industrial and Applied Mathematics (SIAM), Philadelphia', '2009', 'https://doi.org/10.1137/1.9780898717716', 'tier:interval, vocabulary:decided',
       'Interval arithmetic computes enclosures that provably contain every value of the set; inclusion of boxes is decided exactly, which is why a domain-inclusion verdict from this tier is "decided", not estimated.',
       'MooreKearfottCloud2009', kind='book'),
    # ---- tier 2: symbolic checking — what it establishes and its limit -----------------------------------------
    _s('meurer-2017-sympy', 'SymPy: symbolic computing in Python', 'Meurer, A.; Smith, C. P.; Paprocki, M.; et al.', 'PeerJ Computer Science 3, e103', '2017',
       'https://doi.org/10.7717/peerj-cs.103', 'tier:sympy',
       'The computer algebra system the sympy tier runs on; simplification of a difference to zero over free symbols is an identity check at a fixed dimension.',
       'Meurer2017'),
    _s('richardson-1968-undecidable-elementary', 'Some undecidable problems involving elementary functions of a real variable', 'Richardson, D.',
       'The Journal of Symbolic Logic 33(4), 514–520 (issue dated 1968; published 1969)', '1968', 'https://doi.org/10.2307/2271358', 'tier:sympy, vocabulary:checked-symbolically',
       'Zero-equivalence of expressions is undecidable in general (Richardson\'s theorem): a symbolic simplifier that fails to reach zero has not refuted anything, and a success is "checked-symbolically" — a machine-checked theorem (lean) is a different claim.',
       'Richardson1968'),
    # ---- tier 3: SMT decides the continuum and machine integers; a model is a counterexample --------------------
    _s('demoura-bjorner-2008-z3', 'Z3: An Efficient SMT Solver', 'de Moura, L.; Bjørner, N.',
       'Tools and Algorithms for the Construction and Analysis of Systems (TACAS 2008), Lecture Notes in Computer Science 4963, 337–340', '2008',
       'https://doi.org/10.1007/978-3-540-78800-3_24', 'tier:z3, vocabulary:decided, vocabulary:refuted',
       'The solver behind the z3 tier: a satisfying assignment of the negated claim is a concrete counterexample (our refutation names the point), unsat over the encoded domain is a decision, and a timeout is neither — "undecided".',
       'deMouraBjorner2008'),
    _s('kroening-strichman-2016-decision-procedures', 'Decision Procedures: An Algorithmic Point of View', 'Kroening, D.; Strichman, O.',
       'Springer, Texts in Theoretical Computer Science (2nd edition)', '2016', 'https://doi.org/10.1007/978-3-662-50497-0', 'tier:z3',
       'The textbook account of the decision procedures z3 applies: linear real arithmetic, integers, and bit-vectors by bit-blasting — the fixed-point MAC-overflow claim is decided over exact machine integers on this basis.',
       'KroeningStrichman2016', kind='book'),
    # ---- tier 4: a machine-checked proof in Lean/Mathlib; why it counts ----------------------------------------
    _s('demoura-2015-lean', 'The Lean Theorem Prover (System Description)', 'de Moura, L.; Kong, S.; Avigad, J.; van Doorn, F.; von Raumer, J.',
       'Automated Deduction — CADE-25, Lecture Notes in Computer Science 9195, 378–388', '2015', 'https://doi.org/10.1007/978-3-319-21401-6_26', 'tier:lean',
       'The proof assistant: proofs are terms checked by a small trusted kernel (dependent type theory); the lean tier\'s "proved" means the kernel accepted the term for the statement whose hash matches ours.',
       'deMoura2015'),
    _s('demoura-ullrich-2021-lean4', 'The Lean 4 Theorem Prover and Programming Language', 'de Moura, L.; Ullrich, S.',
       'Automated Deduction — CADE 28, Lecture Notes in Computer Science 12699, 625–635', '2021', 'https://doi.org/10.1007/978-3-030-79876-5_37', 'tier:lean',
       'The version the polari-proof-tools worker pins (v4.34.1): the same kernel discipline, with the elaborator and the library written in Lean itself.',
       'deMouraUllrich2021'),
    _s('mathlib-2020', 'The Lean mathematical library', 'The mathlib Community',
       'CPP 2020, Proceedings of the 9th ACM SIGPLAN International Conference on Certified Programs and Proofs, 367–381', '2020',
       'https://doi.org/10.1145/3372885.3373824', 'tier:lean',
       'The library our theorems import (pinned at one commit): the sums, sets and finite-index lemmas the σ-symmetry, chain-composition and restriction theorems build on are themselves machine-checked.',
       'mathlib2020'),
    _s('barendregt-wiedijk-2005-challenge', 'The challenge of computer mathematics', 'Barendregt, H.; Wiedijk, F.',
       'Philosophical Transactions of the Royal Society A 363, 2351–2375', '2005', 'https://doi.org/10.1098/rsta.2005.1650', 'tier:lean, vocabulary:proved',
       'Why a machine-checked proof is accepted as a proof: the de Bruijn criterion — a small, independently checkable kernel is the only thing that must be trusted — and what that trust does and does not cover.',
       'BarendregtWiedijk2005'),
    # ---- the vocabulary: three values, and refutation by counterexample -----------------------------------------
    _s('kleene-1952-metamathematics', 'Introduction to Metamathematics', 'Kleene, S. C.', 'North-Holland, Amsterdam (§64, the strong three-valued logic)', '1952', '',
       'vocabulary:undetermined, vocabulary:inapplicable',
       'Kleene\'s strong three-valued logic is the formal home of our third value: a claim whose premise fails or whose value is unrecorded is neither true nor false here — "undetermined", never vacuously true and never refuted.',
       'Kleene1952', verified=False, via='print reference; no DOI — not resolved online', kind='book'),
    _s('lakatos-1976-proofs-and-refutations', 'Proofs and Refutations: The Logic of Mathematical Discovery', 'Lakatos, I. (eds. Worrall, J.; Zahar, E.)',
       'Cambridge University Press (1976; the 2012 edition carries the DOI)', '1976', 'https://doi.org/10.1017/CBO9781139171472', 'vocabulary:refuted',
       'A single counterexample refutes a conjecture and the conjecture is then narrowed, not discarded — the discipline behind keeping a refuted claim with its counterexample and proposing the narrower scope.',
       'Lakatos1976', via='Cambridge Core page for the DOI read back 2026-09-25 (title, editors, publisher)', kind='book'),
]
