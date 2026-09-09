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

Naměřeno na 25 dokončených bězích přes 17 otázek ve všech čtyřech tierech obtížnosti:

| metrika | hodnota |
|---|---|
| answer rate | 25/25 běhů vydalo odpověď požadovaného typu |
| medián confidence, tier Stage 1 | 82,0 (n=13 běhů, 10 otázek) |
| medián confidence, tier Stage 2 | 75,0 (n=5 běhů, 3 otázky) |
| medián confidence, tier Stage 3 | 17,0 (n=3 běhy, 2 otázky) |
| medián confidence, remains unsolved | 35,5 (n=4 běhy, 2 otázky) |
| konzistence 3 běhů | shoda u Q004, Q063, Q090; rozchod u Q099 |

Tři zjištění, která z toho plynou:

1. **Answer rate je bezcenná metrika** — Opus 5 odpoví vždycky, včetně otázek,
   které v Lipsku nevyřešil nikdo. Hodnocení musí stát na správnosti proti klíči.
2. **Self-reported confidence kopíruje lipskou obtížnost** (82 → 75 → 17).
   Model nezávisle reprodukuje pořadí, které v Lipsku vzniklo z chování pěti
   jiných modelů. Kandidát na řádovou úsporu ve stage W2 — ověřit na větším vzorku.
3. **Rozchod mezi běhy nastal jen u otázky, kterou v Lipsku nevyřešil nikdo.**
   Naznačuje, že plošných 20 běhů na otázku je plýtvání a rozpočet patří tam,
   kde model hlásí nejistotu. Vzorek 4 otázek — hypotéza, ne závěr.

### Co selhalo

| běh | počet | příčina |
|---|---|---|
| etapa 1, effort high | 8 | překročení 64k output limitu (článek uvádí 128k) |
| etapa 1 | 85 | vyčerpaný session rate limit |
| Q090#2 | 1 | stream idle timeout |
| Q100#2, #3 | 2 | vyčerpaný session rate limit |

Souběžnost byla 2 agenti (4 CPU), 46 běhů zabralo 7,6 h wall clocku.
