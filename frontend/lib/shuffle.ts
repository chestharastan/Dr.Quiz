import type { QuizQuestion } from "@/lib/api";

export const LETTERS = ["A", "B", "C", "D"] as const;
export type Letter = (typeof LETTERS)[number];

/** A question plus the order its choices are shown in: original letters, the first one shown as "A". */
export type ShuffledQuestion = QuizQuestion & { order: Letter[] };

/** Give every question its own random choice order (Fisher–Yates). Answers keep their original letters. */
export function shuffleChoices(questions: QuizQuestion[]): ShuffledQuestion[] {
  return questions.map((q) => {
    const order: Letter[] = [...LETTERS];
    for (let i = order.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [order[i], order[j]] = [order[j], order[i]];
    }
    return { ...q, order };
  });
}

export function choiceText(q: QuizQuestion, letter: string) {
  return q[`choice_${letter.toLowerCase()}` as "choice_a" | "choice_b" | "choice_c" | "choice_d"];
}

/** The letter a choice was shown under: an original "C" shown first reads as "A". */
export function shownLetter(q: ShuffledQuestion, letter: string) {
  return LETTERS[q.order.indexOf(letter as Letter)] ?? letter;
}
