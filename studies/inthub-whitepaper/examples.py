#!/usr/bin/env python3
"""The running system of definitions.md § Examples — every claim as an assertion.

Each construct cites its entry: D9[model], D12[sampler], ... Texts are Python
strings, a str being a sequence of symbols, written by juxtaposition ('aBa'
for the sequence a, B, a). Run:

    python3 examples.py     ->  one OK line if every example checks

The definitions govern. If this file and the Examples section disagree, one of
them is wrong. Everything is deliberately naive so each value can be tracked
by hand.
"""

# ---- the primitives, exhibited -------------------------------------------
# P1[sequence]   'aBa'                 items, one after another
# P2[symbol]     'a'                   a member of an agreed set
# P3[set]        {'a', 'b'}            no order among them, none repeated
# P4[function]   each def below        for each input, exactly one output
# P5[less than]  0 < 1                 Python's < on N
# P6[same as]    run(x) == run(x)      one value, not two
# P7[length]     len('BaB') == 3

# ---- the running system ---------------------------------------------------
A0 = {'a', 'b', 'ä'}     # D1[alphabet] — the input alphabet
A  = {'a', 'B'}          # D6[token alphabet] — the output alphabet of T
N  = (0, 1, 2)           # D5[number] — ordered by <
L  = 3                   # the bound on length


def T(text):             # D3[tokenizer] : A0^* -> A^*
    assert all(s in A0 for s in text)
    return ''.join({'ä': 'aB', 'b': 'B'}.get(s, s) for s in text)


def M(t):                # D9[model] : A^<=L -> (A -> N); its value is a D8[scoring]
    assert 1 <= len(t) <= L and all(s in A for s in t)
    return {s: (1 if s != t[-1] else 0) for s in A}


def S(sc, n):            # D12[sampler] : (A -> N) x N -> A; n is the draw
    # draw 0 takes the greatest-scored symbol, draw 1 the least — *strictly*:
    # where scores tie there is no single such symbol and S has no value
    # (D12 Notes). A tie-break here would silently totalize the sampler.
    target = (max if n == 0 else min)(sc.values())
    winners = [s for s in sorted(sc) if sc[s] == target]
    if len(winners) != 1:
        raise ValueError('no single greatest/least-scored symbol')
    return winners[0]


def asm(texts):          # D11[assembly] : (A^*)^* -> A^<=L
    return ''.join(texts)[-L:]


def step(t, n):          # D13[model step] : A^<=L x N -> A^<=L
    # D13's lift [s] is invisible in Python, where a symbol and the
    # one-symbol text are the same str — the ledger distinguishes them.
    return asm((t, S(M(t), n)))


def run(t, draws):       # D14[model run] : A^<=L x N^* -> A^<=L
    assert len(draws) >= 1          # bottoms out at one draw (D14 Notes)
    for n in draws:
        t = step(t, n)
    return t


OK, NO = 'ok', 'no'      # V, the verdict alphabet


def nodouble(texts):     # D15[check] : (A^*)^* -> V
    bad = any(a == b for t in texts for a, b in zip(t, t[1:]))
    return NO if bad else OK


def agree(texts):        # D15[check], consensus-shaped — needs the boundaries
    return OK if all(t == texts[0] for t in texts) else NO


GO, REVIEW, DROP = 'go', 'review', 'drop'   # C, the action alphabet


def dec(verdicts):       # D16[decision] : V^* -> C
    return REVIEW if NO in verdicts else GO


# D10/D17/D18/D19 — a specification is a text; what it *determines* rests on a
# reading convention outside the entries. Here the conventions are these
# readers, stated in code because the ledger cannot state them.
MODEL_SPEC = 'score 1 to the symbol opposite the last symbol, 0 to the other'
RUN_SPEC   = 'components as above; start aB; draws 0, 0'    # D17[run specification]
CHECK_SPEC = 'run nodouble, then agree'                     # D18[check specification]


def weak_spec_models():  # D10: 'score the opposite of the last symbol HIGHER'
    def make(hi, lo):
        return lambda t: {s: (hi if s != t[-1] else lo) for s in A}
    return [make(hi, lo) for hi, lo in ((1, 0), (2, 0), (2, 1))]


def read_frame(t):       # D19[frame]: a text over A beginning Ba declares <nodouble>
    return (nodouble,) if t.startswith('Ba') else None      # None: merely a text


def has_no_value(f, *args):
    try:
        f(*args)
    except (ValueError, AssertionError):
        return True
    return False


# ---- the examples, asserted ------------------------------------------------

# whether ä is one symbol or two is T's answer, not the writing's (D2, D3, D4, D7)
assert T('äa') == 'aBa' and len('äa') == 2 and len(T('äa')) == 3

# in practice: the numbering — the integer is attached to the token and is
# not the token (D4 Notes). It is how a function from A materializes as an
# array: the emitted logit vector is scoring o numbering^-1.
numbering = {'a': 0, 'B': 1}                    # a bijection A -> {0, 1}
inv = {i: sym for sym, i in numbering.items()}
sc = M('aB')                                    # the scoring a=1, B=0
assert [sc[inv[i]] for i in range(len(A))] == [1, 0]
# a second numbering changes every array while T agrees on every text --
# why 'the same tokenizer' needs the numbering defined (D4, D9 Notes)
numbering2 = {'a': 1, 'B': 0}
inv2 = {i: sym for sym, i in numbering2.items()}
assert [sc[inv2[i]] for i in range(len(A))] == [0, 1]

# one step, by hand: M(aB) scores a=1 B=0; S picks a; asm gives aBa (D8, D13)
assert M('aB') == {'a': 1, 'B': 0}
assert step('aB', 0) == 'aBa'

# a run, and forgetting: aBaB clipped to BaB — the starting a is gone and
# BaB records nothing about it (D14, D11)
assert run('aB', (0, 0)) == 'BaB'

# the draw is an input; the functions stay deterministic (D12, D14)
assert run('aB', (0,)) == 'aBa' and run('aB', (1,)) == 'aBB'
assert run('aB', (0, 0)) == run('aB', (0, 0))

# why a check takes a sequence of texts: two sequences with different
# verdicts assemble to the same text, so no check on the assembled text
# can compute agreement (D15, D11)
assert agree(('aBa', 'aBB')) == NO and agree(('aBB', 'aBB')) == OK
assert asm(('aBa', 'aBB')) == asm(('aBB', 'aBB')) == 'aBB'

# the chain end to end: two runs -> verdict text -> action (D15, D16)
r0, r1 = run('aB', (0,)), run('aB', (1,))
verdicts = (nodouble((r0,)), nodouble((r1,)), agree((r0, r1)))
assert verdicts == (OK, NO, NO) and dec(verdicts) == REVIEW

# a weakened specification determines a set of models, not one (D10)
distinct = {tuple(sorted(m('aB').items())) for m in weak_spec_models()}
assert len(distinct) == 3

# replaying what a run specification pins gives the same text (D17)
assert run('aB', (0, 0)) == 'BaB'

# a frame enters the input and need not survive it (D19, D11):
# asm clips BaaB to aaB, which no longer begins Ba — the declaration is
# readable only before assembly. The obligation it declared still
# discharges on the output.
assert read_frame('Ba') is not None and read_frame('aB') is None
assert asm(('Ba', 'aB')) == 'aaB' and read_frame('aaB') is None
assert nodouble((run('aaB', (0,)),)) == OK

# D20[checked run] — the accountability wrap, inlined: raise or return the
# moment dec's symbol is the refuse or the accept. The definition recurses on
# the remaining draw-sequences; this loop is its iterative rendering. The
# refuse (DROP) need only exist in C; dec never gives it.
def op(t, d, checks, decide, accept, refuse):     # D20[checked run]
    for j in range(len(d)):
        u = run(t, d[j])
        a = decide(tuple(c((t, u)) for c in checks))
        if a == refuse:
            raise ValueError('refused')           # an early refuse is final
        if a == accept:
            return u                              # the run's text, handed back
    raise ValueError('nothing accepted')          # partial, like S on a tie

# review is neither accept nor refuse: it only lets the recursion continue —
# the draws are the retry budget (D20 Notes: the three-role reduction)
assert op('aB', ((1,), (0,)), (nodouble,), dec, GO, DROP) == 'aBa'
assert has_no_value(op, 'aB', ((1,),), (nodouble,), dec, GO, DROP)

def dec_p(verdicts):                     # privacy-style: refuse outright
    return DROP if NO in verdicts else GO

assert has_no_value(op, 'aB', ((1,), (0,)), (nodouble,), dec_p, GO, DROP)
assert op('aB', ((0,),), (nodouble,), dec_p, GO, DROP) == 'aBa'

# ---- the non-examples, asserted --------------------------------------------

# a scoring with no greatest-scored symbol: S has no value there (D12)
assert has_no_value(S, {s: 0 for s in A}, 0)

# an assembly that ignores the sampled symbol gives a model step that
# consults M and changes nothing — why D13 is not named 'generation step'
def asm0(texts):
    return texts[0][-L:]

def step0(t, n):
    return asm0((t, S(M(t), n)))

assert step0('aB', 0) == 'aB' and step0('BaB', 1) == 'BaB'

# the textbook's model, specialized: a bigram count over the corpus aBaa.
# 'probability' is the outside name for the proportions behind S_p's table;
# the table itself needs no arithmetic to check (D9, D12).
CORPUS = 'aBaa'

def Mc(t):               # D9[model]: how often each symbol followed t's last
    assert 1 <= len(t) <= L and all(s in A for s in t)
    pairs = list(zip(CORPUS, CORPUS[1:]))
    return {s: sum(1 for x, y in pairs if x == t[-1] and y == s) for s in A}

def S_p(sc, n):          # D12[sampler] by table: proportional, so the tie
    table = {            # has a value — the draw decides it
        (('B', 1), ('a', 1)): {0: 'a', 1: 'B'},
        (('B', 0), ('a', 1)): {0: 'a', 1: 'a'},
    }
    return table[tuple(sorted(sc.items()))][n]

assert Mc('aB') == {'a': 1, 'B': 0}      # after B: a once
assert Mc('Ba') == {'a': 1, 'B': 1}      # after a: a once, B once — the tie
assert has_no_value(S, Mc('Ba'), 0)      # greatest-symbol sampler: no value
assert S_p(Mc('Ba'), 0) == 'a' and S_p(Mc('Ba'), 1) == 'B'
assert S_p(Mc('aB'), 0) == 'a'

# the empty text: M needs a last symbol, so it has no value there; whether
# the empty text is in A^<=L at all is the Notation section's open question —
# the system runs entirely on lengths 1 to 3 and never needs the answer
assert has_no_value(M, '')

print('OK — every example in definitions.md § Examples checks. '
      f'A={sorted(A)} N={list(N)} L={L}')
