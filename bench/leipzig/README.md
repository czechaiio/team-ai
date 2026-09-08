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
