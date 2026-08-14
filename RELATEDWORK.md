# Where this sits — the neighbours, the reckoning, and the door

Assembled 6–7 August 2026 from a five-strand literature sweep. Every item was
checked against a live publisher, DOI, arXiv, or proceedings page; anything that
could not be fetched is marked. This document exists to answer three questions the
repository could not previously answer: *which literature is this in*, *what here
is actually new*, and *where would it be published*.

The short version, stated before the evidence, because it is uncomfortable and
should not be buried: **the conceptual home of this project is artificial life, not
machine learning; several of our headline findings are re-derivations of results
that are decades old in fields we had not read; and what survives that reckoning is
narrower than we thought but genuinely unclaimed.**

---

## 1. The reckoning

| our finding | prior art | verdict |
|---|---|---|
| In-distribution screening is structurally blind to off-distribution defects | D'haeseleer, Forrest & Helman (1996) prove that detector sets derived from "self" have geometric **holes** — regions no finite self-derived detector can cover, as a structural property, not an accident | **Re-derivation.** Thirty years old in artificial immune systems. Ours is a quantified instantiation in a new substrate with a cost multiplier attached — a contribution, but not a discovery |
| Open exchange drives libraries toward monoculture | Cantú-Paz (2000) on migration rate, effective selection pressure and takeover time in island-model GAs; the entire niching/fitness-sharing literature from Goldberg & Richardson (1987) | **Re-derivation.** "Dense migration collapses diversity" is the founding pathology of parallel EAs |
| Institutions only matter under scarcity | Whitley, Rana & Heckendorn (1999): island-model advantage concentrates on *separable* problems — migration helps when demes hold non-redundant discoveries | **Substantially known**, in the vocabulary of separability rather than scarcity |
| Screening cost is charged in the same currency as improvement | Rogers (1988): at equilibrium social learning earns no more than the costlier individual learning it free-rides on. Sheldon & Verhulst (1996): immune defence trades off against growth from a shared budget | **Closest true ancestor.** But neither is a computational model with a fungible per-agent budget — see §6 |
| A tiered screen beats both no screening and blanket screening | Enquist, Eriksson & Ghirlanda (2007), "critical social learning" — conditional use of social information resolves Rogers' paradox | **Anticipated in theory.** Our tiers are an implementation of a known resolution |

None of this kills the project. It relocates it. A result that independently
re-derives, in a live LLM population, a structural theorem from artificial immune
systems is worth reporting *as such* — and is far more defensible than the same
result presented as a discovery, which is what an unread author would have done and
what a reviewer would have destroyed.

---

## 2. Artificial life — the nearest ancestors

**Digital parasites are not a metaphor here; they are prior work.**

- **Ray, "An Approach to the Synthesis of Life"** (1991), *Artificial Life II*,
  Addison-Wesley, pp. 371–408. In Tierra, a mutant that lost its own copy procedure
  survived by executing its neighbour's — the first spontaneous digital parasite.
  Hosts then evolved template sequences immune to it; parasites evolved to breach
  that immunity; hyper-parasites emerged that seize the instruction pointer and
  force parasites to replicate *their* genome; and the resulting obligate
  cooperation was itself invaded by cheaters. **Relation:** our parasite,
  immunity, laundering and free-riding are all already-named ALife phenomena. Ray
  is the single most important citation we were missing.
- **Zaman, Meyer, Devangam, Bryson, Lenski & Ofria, "Coevolution Drives the
  Emergence of Complex Traits and Promotes Evolvability"** (2014), *PLOS Biology*
  12(12):e1002023. Host–parasite coevolution in Avida produces *higher* complexity
  and more evolvable genomes than parasite-free evolution. **Relation:** the
  load-bearing complication. In the canonical ALife case the parasite is
  **generative**. Ours is purely destructive, and a reviewer steeped in this
  lineage will ask why. We must either justify the departure (an adversarially
  designed skill is not an evolved parasite, so no arms race is expected) or make
  the adversary adaptive.
- **Kobayashi** (2001), *Nucleic Acids Research* 29(18):3742. Restriction–
  modification systems — bacteria's oldest anti-transfer immunity — behave as
  selfish addiction modules that propagate by threat of harm. **Relation:** the
  biological precedent for *the immune system becoming the parasite*, which is the
  "who screens the screener" question our design invites.
- **Vale et al.** (2015), *Proc. R. Soc. B* 282:20151270. The fitness cost of
  CRISPR-Cas is dominated by *maintaining* the system, not by acquiring spacers or
  running defence. **Relation:** a productive mismatch — we charge cost per
  screening event; biology charges mostly for standing capacity. Worth addressing.
- **Sheldon & Verhulst** (1996), *TREE* 11(8):317. Founding statement of ecological
  immunology: defence is not free and trades off against growth from a shared
  budget. **Relation: cite this first** for "the price of governance." It is closer
  to our mechanism than the CRISPR work.

**Artificial immune systems — where our headline already lives.**

- **Forrest, Perelson, Allen & Cherukuri, "Self-Nonself Discrimination in a
  Computer"** (1994), *IEEE S&P*, pp. 202–212. The founding negative-selection
  algorithm: generate random detectors, discard those matching self, keep the rest.
- **D'haeseleer, Forrest & Helman** (1996), *IEEE S&P*. Formalises **holes** —
  see §1. *(Full text robots-blocked; bibliographic facts and the holes mechanism
  corroborated from multiple secondary sources. Verify by hand before citing.)*
- **Stibor** (2008), PhD thesis, TU Darmstadt. The AIS field's own internal
  critique concluding negative selection is structurally the wrong tool for
  real-world anomaly detection. **Relation:** our regression tier is that failure
  mode, rediscovered in a new substrate.

**Cultural evolution — the true ancestor of the cost claim.**

Rogers (1988), Rendell, Fogarty & Laland (2010, *Evolution* 64(2):534 — population
structure can make the paradox *worse*, not better), and Enquist et al. (2007).
Rendell et al. is structurally close to our non-monotone inequality result:
structure producing a counter-intuitive interior effect rather than a monotone one.

**ALife's own LLM work.**

- **Nisioti, Risi, Momennejad, Oudeyer & Moulin-Frier, "Collective Innovation in
  Groups of Large Language Models"** (2024), ALIFE 2024, doi:10.1162/isal_a_00730.
  LLM agents share discoveries in Little Alchemy 2; dynamically rewired groups beat
  fully-connected ones because full connectivity causes premature convergence.
  **The closest same-substrate sibling** — but connectivity, not institution or
  screening, is the independent variable, and there is no adversary or provenance.
- **Perez, Léger, Oudeyer, Moulin-Frier et al.** (2024), arXiv:2403.08882 —
  the general framework of which the above is one instance. This is a sustained
  Inria *Flowers* programme; position against the programme, not one paper.
- **Kumar, Lu, Kirsch, Tang, Stanley, Isola & Ha, "Automating the Search for
  Artificial Life With Foundation Models"** (2025), *Artificial Life* 31(3):368,
  arXiv:2412.17799. Establishes that the journal publishes foundation-model
  methods — and that Sakana authors publish there.
- **Masumori, Doi, Maruyama, Takata & Ikegami, "OpenLife"** (2026),
  arXiv:2606.31046. Six autonomous LLM agents over ~12 weeks with persistent memory
  and a budget-based *metabolism*. **The most current adjacent work** and the most
  likely competitor for reviewer attention.
- **Dorin & Stepney, "What Is Artificial Life Today, and Where Should It Go?"**
  (2024), *Artificial Life* 30(1):1. Important caution: the journal's own
  self-assessment mentions LLMs mainly in an ethics-and-risk register, not as a
  first-class substrate. We are arguing into a field that has not yet endorsed our
  material, which must shape the introduction.

---

## 3. Evolutionary computation — this is an island model

An EC reviewer will call this *a heterogeneous island-model evolutionary algorithm
with LLM-mediated variation operators and a cost-gated migration-acceptance layer*.
The mapping is exact: agents are demes, skills are individuals, self-editing is
mutation, import is migration, the institution is the migration topology.

Canonical: **Tanese** (1989), founding distributed GA; **Whitley, Rana &
Heckendorn** (1999); **Cantú-Paz**, *Efficient and Accurate Parallel Genetic
Algorithms* (2000); **Skolicki & De Jong** (2005), GECCO, doi:10.1145/1068009.1068219
— migration size and interval have a *non-monotone* effect on quality, a direct
precedent for our non-monotone curve; **Alba & Troya** (2001).

Diversity: **Goldberg & Richardson** (1987) fitness sharing; **Mahfoud** (1995)
niching, with population-size lower bounds before niches collapse — transferable to
our scarcity threshold.

Quality-diversity: **Mouret & Clune** (2015) MAP-Elites — an EC reviewer will
propose modelling each agent's library as a per-task MAP-Elites archive, making
this *island-MAP-Elites over textual genotypes*; **Lehman & Stanley** (2011);
**Bradley et al., QDAIF** (2023), arXiv:2310.13032 — the only prior QD system with
free-text genotypes judged by an LLM, and its core question ("can the evaluator be
fooled?") is ours.

LLM-driven evolution, and the uncomfortable part: **FunSearch** (Romera-Paredes et
al., *Nature* 625:468, 2024) uses "an island-based evolutionary method";
**AlphaEvolve** (arXiv:2506.13131) states it combines "MAP-elites and island-based
population models"; **ShinkaEvolve** (Sakana, arXiv:2509.19349) has islands whose
members "occasionally migrate." Islands plus LLM mutation is now this subfield's
**default architecture**. Our contribution cannot be the island structure. Also:
**ELM** (Lehman, Gordon, Jain, Ndousse, Yeh & Stanley, 2022, arXiv:2206.08896);
**Language Model Crossover** (Meyerson et al., ACM TELO, 2023) — "import and adapt
another agent's skill" is language-model crossover; **Voyager** (2023) — the
skill-library ancestor, explicitly single-agent.

Coevolution: **Hillis** (1990), *Physica D* 42:228 — coevolving parasites prevent
stagnation; **Rosin & Belew** (1997), *Evolutionary Computation* 5(1):1 — narrow
static test pools get exploited, which is our 6/6 result's founding motivation;
**Watson & Pollack** (2001) on disengagement. **Our saboteur does not evolve, so
this is a static red-team probe, not coevolution.** Say so, or fix it. Also
**Kumar, Bahlous-Boldi, Sharma, Isola, Risi, Tang & Ha, "Digital Red Queen"**
(2026), arXiv:2601.03335 — LLM adversarial evolution converging to its own
monoculture, months old and directly relevant.

Cost of evaluation: **Jin** (2011), *Swarm and Evolutionary Computation* 2:61 —
surrogate-assisted EC frames fitness evaluation as a budgeted scarce resource. Our
three screening tiers are points on a fidelity–cost curve; this is the correct
existing frame for them.

---

## 4. The translational case — agent skills as a real ecosystem

This is what makes the work more than a simulation, and it is the strongest card.

**Qu, Liu, Geng, Deng, Li, Zhang, Zhang & Ma** (2026), arXiv:2604.03081 — 1,070
adversarial `SKILL.md` artifacts across four frameworks and five models, 11.6–33.5%
bypass rates. **Ling, Zhong & Huang** (2026), arXiv:2602.08004 — analysis of 40,285
public skills. Industry base rates (Snyk "ToxicSkills": 36.8% of 3,984 scanned
skills flawed; the CSA's SKILL.md supply-chain advisory; OWASP Agentic Skills Top
10). **Xu & Yan** (2026), arXiv:2602.12430 — the nearest formal neighbour, a
four-tier *permission* model, unpriced and unevaluated.

Foundational security lineage: Greshake et al. (2023) indirect prompt injection;
**Gu et al., "Agent Smith"** (ICML 2024) — exponential contagion through pairwise
agent contact, our propagation precedent; AgentPoison (NeurIPS 2024); BadAgent
(ACL 2024), whose "poison survives benign retraining" is the single-agent form of
our screening-blindness result.

None of these run a population-level simulation. **The epidemiology is ours; the
vulnerability is theirs.**

---

## 5. International relations — demoted to interpretation layer

The IR apparatus (Grieco 1988's `U = V − k(W − V)`; Snidal 1991 on large-N
attenuation; Powell 1991 on the endogeneity of relative-gains concern; Ostrom 1990
on the cost of monitoring; Keohane 1984) remains correct and worth citing, but it
should no longer lead. For an ALife audience it is the *interpretation* of a dial
whose mechanism is better described in the field's own vocabulary — relatedness,
spite, reciprocity, kin selection. An ALife reviewer will specifically ask for the
export dial to be glossed in those terms rather than imported unglossed.

Powell remains the concession that must be made explicitly: we sweep `k`
exogenously, and Powell's whole point is that relative-gains sensitivity is
endogenous to the environment. Stating this converts our biggest vulnerability into
a declared scope condition.

---

## 6. What is genuinely ours

After the reckoning, this is what survives — and it is enough for a Letter, and
possibly for an Article.

1. **A budget that is fungible between screening and self-improvement.** Island
   models treat migration as free. Artificial immune systems do not model a shared
   organismal budget at all — we searched specifically and found none. Ecological
   immunology has the concept in biology but not as a computational system. This is
   the one mechanism with no located computational precedent, and it should be the
   paper's spine.
2. **An asymmetric, strategic export policy decoupled from topology.** Parallel EAs
   model migration rate symmetrically; nobody models a deme that *refuses* on
   strategic grounds while remaining connected.
3. **First-hand versus transitive propagation as a tracked variable**, with
   defectiveness derived from artifact content rather than sender identity, so a
   parasite laundered through an honest intermediary is still detectable. The HGT
   literature tracks direct transfer only.
4. **The non-monotone inequality curve with an interior maximum**, robust across
   five endowment shapes. Rendell et al. (2010) gestures at structure worsening
   outcomes; nobody produces this hump.
5. **Format-faithful `SKILL.md` artifacts** — the unit of transfer is the artifact
   deployed systems actually use, which is what makes this translational rather
   than allegorical.

---

## 7. The door

**ALIFE 2026** (Waterloo, 17–21 August) is ten days away and every submission
window closed months ago. **ALIFE 2027** (Prague) has no announced dates. GECCO
2026 and PPSN 2026 have passed. There is, as of today, no open conference deadline
anywhere in this space.

That leaves the best option anyway: **rolling submission to *Artificial Life* (MIT
Press).** Editors-in-chief Susan Stepney and Alan Dorin. Article 6,000–12,000
words; **Letter under 2,000 words** for a short communication of original results;
Fast Track Letter for especially timely work, decided "within a matter of weeks."
Code and data must be public — which we already are.

And there is an explicit invitation. Dorin & Stepney's editorial closing the
journal's 30th-anniversary volume (*Artificial Life* 30(4):439, 2024) asks in as
many words for work that "applies the principles, understanding, and techniques of
our discipline to tackle real, urgent, complex problems that impact human society,"
naming governance among the example domains. Their companion editorial goes
further: "**We should also be establishing policies and frameworks for the proper
creation and management of artificial living systems**" — which is a near-verbatim
description of a quarantine regime for propagating skills. They add that such
submissions "have not been received nearly as often as we would like."

The risk is equally clear: an ALife-native reviewer may read this as multi-agent
systems work wearing ALife vocabulary. The defence is to foreground ALife-native
content — skills as replicators, screening as immunity with a metabolic cost,
Bedau-style evolutionary activity statistics over the skill population — rather
than bolting a governance angle onto an engineering system.

---

## 8. How these papers are written

Extracted from the three papers that prompted this repositioning: the ASAL paper
(Kumar et al.), Taniguchi et al.'s System 0/1/2/3, and the Dorin & Stepney
editorials. Rules, not praise.

1. **Name your mechanisms — two to four capitalized handles, introduced together
   in one place, then reused verbatim everywhere after.** ASAL has exactly three
   (Supervised Target, Open-Endedness, Illumination). A reader carries three
   things; past that the paper reads as accreted rather than architected. Ours:
   *Exchange Institution, Export Policy, Quarantine.*
2. **Withhold the proposal until the problem is built.** Both papers spend six to
   ten paragraphs before "we propose." The proposal has to be earned.
3. **Open on borrowed legitimacy, not on your own claim.** ASAL's first sentence is
   about a Nobel Prize, not about ASAL.
4. **Reuse an existing schema when naming a big idea.** Taniguchi brackets
   Kahneman's System 1/2 with System 0 and System 3, so the reader's existing
   furniture does half the work.
5. **Write every figure caption as a restated claim, not a description.** A reader
   who only scans figures should still get the spine.
6. **Define jargon in the same clause that introduces it.** No unglossed coinage,
   ever.
7. **Related work as short headed narrative subsections, never a citation wall.**
   Each subsection argues "here is what was tried and why it is insufficient here."
8. **Hedge your critique of others; never hedge your own thesis.** Confidence on
   the claim, qualification on the literature review.
9. **Give every abstract sentence one job**, moving outward in scale: hook, gap,
   claim, name-and-list, scope evidence, headline result, secondary result,
   significance.
10. **Name concrete examples instead of gesturing at categories.** "Boids, Particle
    Life, Game of Life, Lenia" earns generality; "several substrates" asserts it.
11. **Close the introduction on significance or priority, never on a summary.**
12. **Match register to ambition.** ASAL's clipped systems-paper economy and
    Taniguchi's sustained clause-dense argument are both successful ALife
    registers. Given a monograph-trained author, Taniguchi's is the closer native
    mode — a wide literature compressed into one diagram and one sustained claim.

---

*Every URL and date above was checked against a live page on 6–7 August 2026.
Items noted as robots-blocked or triangulated should be confirmed by hand before
they enter a manuscript bibliography.*
