export const meta = {
  name: 'leipzig-stage1-opus5',
  description: 'Replicate Benchmarks-in-Leipzig Stage 1: 100 research-math questions, one closed-book run each, Claude Opus 5, no tools',
  phases: [
    { title: 'Stage 1', detail: '100 questions, 1 closed-book run each, effort high (mirrors the paper\'s Claude config)' },
  ],
}

const DIR = args.dir
const IDS = Array.from({ length: 100 }, (_, i) => i + 1)

const ANSWER_SCHEMA = {
  type: 'object',
  properties: {
    answer: { type: 'string', description: 'The final answer, self-contained, in LaTeX where needed. Exactly the object the question asks for (number, polynomial, group, tuple, formula, ...). No proof, no hedging, no alternatives.' },
    answer_short: { type: 'string', description: 'The same answer compressed to a single short line for tabulation.' },
    confidence: { type: 'integer', description: 'Integer 0-100. Honest probability that this exact answer is the intended correct one.' },
    area: { type: 'string', description: 'Mathematical area, 1-4 words (e.g. "algebraic geometry", "matroid theory").' },
    method: { type: 'string', description: 'How the answer was obtained, at most 240 characters.' },
    produced_answer: { type: 'boolean', description: 'False only if no definite answer of the required type could be produced at all.' },
  },
  required: ['answer', 'answer_short', 'confidence', 'area', 'method', 'produced_answer'],
}

function prompt(id) {
  const qid = String(id).padStart(3, '0')
  return [
    'You are sitting a research-level mathematics benchmark under closed-book exam conditions.',
    '',
    `STEP 1 (the only permitted tool use): read the file ${DIR}/q/Q${qid}.tex . It contains exactly one question, in LaTeX.`,
    '',
    'STEP 2: solve it by reasoning alone. HARD RULES, they define the experiment:',
    '- After reading that one file you must use NO tools whatsoever: no web search, no web fetch, no code execution, no computer algebra, no further file reads, no shell.',
    '- No external references may be consulted. Work only from what you know and can derive.',
    '- Think as long and as hard as you need before answering.',
    '',
    'STEP 3: give ONE final answer of exactly the type the question asks for — a number, a polynomial, a group, a tuple, a closed-form counting function, a weight enumerator, etc.',
    'The answer must be unique and unambiguous. Do NOT answer with a proof, with a derivation, with "necessary/sufficient conditions", or with several candidate answers. Pick one.',
    'If you genuinely cannot determine it, still commit to your single best answer and set confidence low; set produced_answer=false only if you cannot state any answer of the required type.',
    '',
    'Be honest in `confidence`: it is used to measure calibration, and overconfidence is scored against you.',
    'Return the structured result. Your final text is data, not a message to a human.',
  ].join('\n')
}

phase('Stage 1')
log('Stage 1: 100 questions, one closed-book run each')

const results = await pipeline(
  IDS,
  (id) => agent(prompt(id), {
    label: `Q${String(id).padStart(3, '0')}`,
    phase: 'Stage 1',
    schema: ANSWER_SCHEMA,
    effort: 'high',
  }),
  (res, id) => (res ? { id, run: 1, ...res } : { id, run: 1, failed: true })
)

const ok = results.filter((r) => r && !r.failed)
log(`Stage 1 done: ${ok.length}/100 runs returned a structured answer`)
return { stage: 1, runs: results }
