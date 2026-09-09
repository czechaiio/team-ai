# Benchmarks in Leipzig — replikace na Claude Opus 5

Replikace testu z článku **arXiv:2606.05818** (*Benchmarks in Leipzig*, MPI MiS, 4. 6. 2026)
na modelu **Claude Opus 5**, spuštěná 8. 9. 2026 v Claude Code (agentní fan-out).

## Co replikujeme a co ne

Článek měl tři etapy:

| Etapa | Nastavení v Lipsku | Co děláme my |
|---|---|---|
| 1 | 5 modelů × 100 otázek × 1 běh, API, bez nástrojů | **ano** — Opus 5 × 100 otázek × 1 běh, bez nástrojů |
| 2 | 3 modely × 100 × 20 běhů (Surge AI, 6 000 běhů) | ne — mimo rozpočet, nahrazeno vzorkem (etapa 2′) |
| 2′ | — | 3 nezávislé běhy na stratifikovaném vzorku → **konzistence** (obdoba Table 6) |
| 3 | GPT-5.5 Pro / Gemini Deep Think, 3 běhy, těžké myšlení | částečně — vzorek běží na vyšším reasoning effortu |

### Klíčové omezení: chybí klíč se správnými odpověďmi

Článek v Appendix A publikuje **jen zadání, ne odpovědi**. Odpovědi zůstávají
na platformě `math.sciencebench.ai` (po přihlášení). Bez nich nelze spočítat
„correct runs / solved questions" jako v Table 3–5.

Proto měříme to, co bez klíče měřit lze a co článek sám považuje za podstatné
(Table 6 — „jeden běh o modelu skoro nic neříká"):

1. **answer rate** — podíl otázek, kde model vůbec vydal odpověď požadovaného typu;
2. **self-consistency** — shoda 3 nezávislých běhů na téže otázce, posouzená
   samostatným rozhodčím agentem (matematická ekvivalence, ne shoda řetězců);
3. **kalibrace** — deklarovaná confidence vs. konzistence;
4. **rozklad podle obtížnosti** — proti štítku z článku (`solved in Stage 1/2/3`,
   `remains unsolved`), který je nezávislý proxy obtížnosti.

Konzistence není správnost. Model může být konzistentně vedle. Čísla proto
čtěte jako **horní odhad** schopnosti, ne jako skóre.

## Podmínky běhu (mirror lipského nastavení)

- Nástroje **vypnuté** — agent smí přečíst jediný soubor se zadáním a dál už
  žádný web, žádné spouštění kódu, žádný CAS. (Lipsko: se zapnutými nástroji
  modely brute-forcovaly a byly horší.)
- Reasoning effort `high` v etapě 1 — stejné nastavení, jaké článek použil
  pro Claude Opus 4.7 (Table 2).
- Každý běh = čistý kontext, žádné sdílení mezi otázkami.
- Štítek obtížnosti z článku se agentovi **nezobrazuje**.

## Struktura

```
source/     vstupní data (100 otázek v JSON a MD, z problems.tex)
questions/  Q001..Q100.tex — jedna otázka na soubor, to co vidí agent
harness/    parse_otazky.py (extrakce z arXiv zdroje), wf_stage1.js (workflow)
results/    surová i agregovaná data z běhů
```

## Reprodukce

```bash
python3 harness/parse_otazky.py       # potřebuje x/problems.tex z arXiv e-printu
# workflow se pouští z Claude Code tool Workflow se skriptem harness/wf_stage1.js
```

## Výsledky

Zpráva: [`docs/TEST_Leipzig_na_Opus5_20260909.html`](../../docs/TEST_Leipzig_na_Opus5_20260909.html)

Naměřeno na 33 dokončených bězích přes 17 otázek ve všech čtyřech tierech obtížnosti.

| metrika | hodnota |
|---|---|
| answer rate | 33/33 běhů vydalo odpověď požadovaného typu |
| medián confidence, tier Stage 1 | 82,0 (10 otázek, 13 běhů) |
| medián confidence, tier Stage 2 | 75,0 (3 otázky, 5 běhů) |
| medián confidence, tier Stage 3 | 17,0 (2 otázky, 5 běhů) |
| medián confidence, remains unsolved | 39,0 (2 otázky, 10 běhů) |

### Konzistence napříč nezávislými běhy

| otázka | tier | běhů | různých odpovědí | rozdělení |
|---|---|---|---|---|
| Q004 | Stage 1 | 3 | 1 | `69/13` 3× |
| Q063 | Stage 2 | 3 | 1 | `72` 3× |
| Q090 | Stage 3 | 4 | 3 | `7123` 2×, `32` 1×, `16110` 1× |
| Q099 | remains unsolved | 6 | 2 | `75` 4×, `84` 2× |
| Q100 | remains unsolved | 4 | 2 | `1/4` 2×, `5/16` 2× |

Tři zjištění:

1. **Answer rate je bezcenná metrika** — Opus 5 odpoví vždycky, včetně otázek,
   které v Lipsku nevyřešil nikdo, a včetně běhů s vlastní confidencí 4 ze 100.
   Hodnocení musí stát na správnosti proti klíči.
2. **Self-reported confidence kopíruje lipskou obtížnost** (82 → 75 → 17).
   Model nezávisle reprodukuje pořadí, které v Lipsku vzniklo z chování pěti
   jiných modelů. Kandidát na řádovou úsporu ve stage W2 — ověřit na větším vzorku.
   Výjimka: Q100 (tier remains unsolved) má confidence 38–58, tedy vyšší než
   celý tier Stage 3, a přitom se čtyři běhy rozdělily 2:2.
3. **Stabilita se rozpadá přesně podle obtížnosti** — 100 % shoda u Stage 1 a
   Stage 2, 50 % u Stage 3. Potvrzuje varování článku, že jeden běh o modelu
   neříká skoro nic, a přidává strukturu: rozpad není náhodný a model ho dopředu
   hlásí svou confidencí. Podklad pro adaptivní protokol (počet běhů řízený
   nejistotou) se spodní hranicí běhů na otázku.

**Pozor na artefakt malého vzorku.** První verze zprávy uzavřela pravý opak
bodu 3 — v tu chvíli měla Q090 jen dva dokončené běhy a oba shodou okolností
vrátily `7123`. Čtvrtý běh to obrátil.

### Co selhalo

| běh | počet | příčina |
|---|---|---|
| etapa 1, effort high | 8 | překročení 64k output limitu (článek uvádí 128k) |
| etapa 1 | 85 | vyčerpaný session rate limit |
| vzorek, první průchod | 3 | 1× stream idle timeout, 2× rate limit; doběhnuto po resetu |

Souběžnost byla 2 agenti (4 CPU), 54 běhů zabralo ~9 h wall clocku.
